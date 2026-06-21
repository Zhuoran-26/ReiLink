from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.modules.memory.pending import PendingMemoryQueue
from app.modules.memory.profile import PlayerMemory
from app.modules.session_archive.memory_bridge import ArchiveMemoryCandidateBridge
from app.modules.session_archive.store import SessionArchiveStore

client = TestClient(app)


def _now(offset_seconds: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def _event(
    summary: str,
    *,
    event_id: str = "event-preference",
    event_type: str = "session_note",
    source: str = "manual",
    game: str = "艾尔登法环",
    entity: str | None = "恶兆妖鬼 Margit",
    timestamp: str | None = None,
) -> dict:
    return {
        "id": event_id,
        "timestamp": timestamp or _now(),
        "event_type": event_type,
        "safe_summary": summary,
        "source": source,
        "related_game": game,
        "related_entity": entity,
    }


def _archive(
    summary: str,
    *,
    session_id: str = "archive-memory-bridge",
    event_id: str = "event-preference",
    event_type: str = "session_note",
    source: str = "manual",
    timestamp: str | None = None,
) -> dict:
    result = SessionArchiveStore().archive_current(
        session_id=session_id,
        events=[_event(summary, event_id=event_id, event_type=event_type, source=source, timestamp=timestamp)],
        game="艾尔登法环",
        boss="恶兆妖鬼 Margit",
    )
    assert result["status"] == "created"
    assert result["archive"] is not None
    return result["archive"]


def _scan(archive: dict) -> dict:
    return ArchiveMemoryCandidateBridge().scan_archive(archive["id"])


def test_archive_safe_preference_creates_pending_candidate_without_long_term_memory():
    archive = _archive("用户偏好打 Boss 前先探索地图，不喜欢直接硬打。")

    result = _scan(archive)
    pending = PendingMemoryQueue().list()
    profile = PlayerMemory().load_profile()

    assert result["scan_summary"]["created_count"] == 1
    assert pending[0]["source"] == "session_archive"
    assert pending[0]["type"] == "gameplay_preference"
    assert pending[0]["requires_confirmation"] is True
    assert pending[0]["status"] == "pending"
    assert pending[0]["guard_reason"] == "requires_confirmation"
    assert pending[0]["payload"]["source_archive_id"] == archive["id"]
    assert "raw prompt" not in json.dumps(pending[0], ensure_ascii=False).lower()
    assert profile.long_term_memories == []
    assert "探索地图" not in PlayerMemory().build_prompt_context()


def test_archive_single_death_and_single_emotion_do_not_create_candidates():
    death_archive = _archive(
        "死亡次数更新：3",
        session_id="death-only",
        event_id="death-event",
        event_type="death_count_changed",
    )
    emotion_archive = _archive(
        "用户这局打 Boss 很烦躁。",
        session_id="emotion-only",
        event_id="emotion-event",
        event_type="frustration_changed",
    )

    death_result = _scan(death_archive)
    emotion_result = _scan(emotion_archive)

    assert death_result["created_candidates"] == []
    assert death_result["skipped_candidates"][0]["guard_reason"] == "single_session_event_only"
    assert emotion_result["created_candidates"] == []
    assert emotion_result["skipped_candidates"][0]["guard_reason"] == "single_emotional_state_only"
    assert PendingMemoryQueue().list() == []


def test_archive_bridge_blocks_assistant_proactive_secret_and_persona_drift_sources():
    archives = [
        _archive("用户偏好回复短一点。", session_id="assistant-source", source="assistant"),
        _archive("用户偏好回复短一点。", session_id="proactive-source", source="proactive"),
        _archive("用户偏好回复短一点，api_key=sk-test-secret-value-123456。", session_id="secret-source"),
        _archive("用户希望 Rei 以后像客服一样每句都夸我。", session_id="persona-drift"),
    ]

    reasons = []
    for archive in archives:
        result = _scan(archive)
        assert result["created_candidates"] == []
        reasons.append(result["rejected_candidates"][0]["guard_reason"])

    assert reasons == [
        "assistant_source_blocked",
        "proactive_source_blocked",
        "sensitive_secret_blocked",
        "persona_drift_blocked",
    ]
    assert PendingMemoryQueue().list() == []


def test_archive_bridge_dedupes_pending_and_already_accepted_memory():
    archive = _archive("用户偏好打 Boss 前先探索地图，不喜欢直接硬打。", session_id="dedupe-first")
    first = _scan(archive)
    candidate_id = first["created_candidates"][0]["id"]

    duplicate_pending = _scan(archive)
    accepted = PendingMemoryQueue().accept(candidate_id)
    second_archive = _archive("用户偏好打 Boss 前先探索地图，不喜欢直接硬打。", session_id="dedupe-second")
    duplicate_accepted = _scan(second_archive)

    assert duplicate_pending["created_candidates"] == []
    assert duplicate_pending["skipped_candidates"][0]["guard_reason"] == "duplicate_candidate"
    assert accepted["status"] == "accepted"
    assert accepted["long_term_memory_id"]
    assert duplicate_accepted["created_candidates"] == []
    assert duplicate_accepted["skipped_candidates"][0]["guard_reason"] == "duplicate_candidate"


def test_archive_candidate_accept_and_ignore_keep_confirmation_boundary():
    accepted_archive = _archive("用户偏好回复短一点，只给一句重点。", session_id="accept-archive")
    accepted_candidate = _scan(accepted_archive)["created_candidates"][0]
    accepted = PendingMemoryQueue().accept(accepted_candidate["id"])

    ignored_archive = _archive("用户偏好避免剧透，除非主动问攻略。", session_id="ignore-archive")
    ignored_candidate = _scan(ignored_archive)["created_candidates"][0]
    ignored = PendingMemoryQueue().ignore(ignored_candidate["id"])
    profile = PlayerMemory().load_profile()

    assert accepted["long_term_memory_id"]
    assert ignored["long_term_memory_id"] is None
    assert ignored["status"] == "ignored"
    assert len(profile.long_term_memories) == 1
    assert "回复更短" in profile.long_term_memories[0]["summary"]
    assert "避免剧透" not in PlayerMemory().build_prompt_context()


def test_archive_bridge_handles_empty_scan_and_recent_limit():
    empty_recent = ArchiveMemoryCandidateBridge().scan_recent()
    assert empty_recent["scan_summary"]["archives_scanned"] == 0
    assert empty_recent["skipped_candidates"][0]["guard_reason"] == "no_recent_archives"

    first = _archive("用户偏好回复短一点，只给一句重点。", session_id="recent-first", timestamp=_now(-30))
    _archive("用户偏好避免剧透，除非主动问攻略。", session_id="recent-second", timestamp=_now(-20))
    _archive("用户偏好打 Boss 前先探索地图，不喜欢直接硬打。", session_id="recent-third", timestamp=_now(-10))

    recent = ArchiveMemoryCandidateBridge().scan_recent(limit=2)

    assert first["id"]
    assert recent["scan_summary"]["archives_scanned"] == 2
    assert recent["scan_summary"]["events_scanned"] == 2


def test_archive_search_does_not_auto_create_memory_candidates():
    _archive("用户偏好回复短一点，只给一句重点。", session_id="search-no-auto")

    result = SessionArchiveStore().search_archives(q="短一点")

    assert result["total"] == 1
    assert PendingMemoryQueue().list() == []
    assert PlayerMemory().load_profile().long_term_memories == []


def test_archive_memory_candidate_api_routes_return_public_pending_items():
    created = client.post(
        "/api/session-archives/archive-current",
        json={
            "session_id": "api-archive-memory-bridge",
            "game": "艾尔登法环",
            "boss": "恶兆妖鬼 Margit",
            "events": [_event("用户偏好回复短一点，只给一句重点。")],
        },
    )
    archive_id = created.json()["archive"]["id"]

    scan = client.post(f"/api/session-archives/{archive_id}/memory-candidates")
    pending = client.get("/api/memory/pending")
    recent = client.post("/api/session-archives/memory-candidates/scan-recent", json={"limit": 1})

    assert scan.status_code == 200
    assert scan.json()["scan_summary"]["created_count"] == 1
    assert scan.json()["created_candidates"][0]["source"] == "session_archive"
    assert "payload" not in scan.json()["created_candidates"][0]
    assert pending.status_code == 200
    assert pending.json()[0]["source"] == "session_archive"
    assert "payload" not in pending.json()[0]
    assert recent.status_code == 200
    assert recent.json()["scan_summary"]["archives_scanned"] == 1
