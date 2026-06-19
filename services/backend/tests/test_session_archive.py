import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.modules.memory.pending import PendingMemoryQueue
from app.modules.memory.profile import PlayerMemory
from app.modules.session_archive.store import SessionArchiveStore

client = TestClient(app)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _events() -> list[dict]:
    return [
        {
            "id": "event-game",
            "timestamp": _now(),
            "event_type": "game_selected",
            "safe_summary": "游戏：艾尔登法环",
            "source": "game_context",
            "related_game": "艾尔登法环",
        },
        {
            "id": "event-boss",
            "timestamp": _now(),
            "event_type": "boss_detected",
            "safe_summary": "Boss：恶兆妖鬼 Margit",
            "source": "game_session",
            "related_game": "艾尔登法环",
            "related_entity": "恶兆妖鬼 Margit",
        },
        {
            "id": "event-deaths",
            "timestamp": _now(),
            "event_type": "death_count_changed",
            "safe_summary": "死亡次数更新：3",
            "source": "game_session",
            "related_game": "艾尔登法环",
            "related_entity": "恶兆妖鬼 Margit",
        },
        {
            "id": "event-knowledge",
            "timestamp": _now(),
            "event_type": "knowledge_used",
            "safe_summary": "使用知识摘要：玛尔基特二阶段",
            "source": "knowledge",
            "related_game": "艾尔登法环",
        },
    ]


def test_session_archive_store_create_list_read_delete_clear():
    store = SessionArchiveStore()

    result = store.archive_current(session_id="session-a", events=_events(), game="艾尔登法环", boss="恶兆妖鬼 Margit")

    assert result["status"] == "created"
    archive = result["archive"]
    assert archive["event_count"] == 4
    assert archive["game"] == "艾尔登法环"
    assert archive["boss"] == "恶兆妖鬼 Margit"
    assert "死亡次数更新" in archive["summary"]
    assert len(store.list_archives()) == 1
    assert store.get_archive(archive["id"])["id"] == archive["id"]

    store.delete_archive(archive["id"])
    assert store.list_archives() == []

    second = store.archive_current(session_id="session-b", events=_events())["archive"]
    assert second is not None
    assert store.clear_archives() == 1
    assert store.list_archives() == []


def test_session_archive_api_create_list_read_delete_clear():
    created = client.post(
        "/api/session-archives/archive-current",
        json={"session_id": "api-session", "events": _events(), "game": "艾尔登法环", "boss": "恶兆妖鬼 Margit"},
    )

    assert created.status_code == 200
    created_data = created.json()
    assert created_data["status"] == "created"
    archive_id = created_data["archive"]["id"]

    listed = client.get("/api/session-archives")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == archive_id

    detail = client.get(f"/api/session-archives/{archive_id}")
    assert detail.status_code == 200
    assert len(detail.json()["events"]) == 4

    deleted = client.delete(f"/api/session-archives/{archive_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"status": "deleted", "archive_id": archive_id}
    assert client.get(f"/api/session-archives/{archive_id}").status_code == 404

    client.post("/api/session-archives/archive-current", json={"session_id": "api-session-2", "events": _events()})
    cleared = client.post("/api/session-archives/clear")
    assert cleared.status_code == 200
    assert cleared.json()["deleted_count"] == 1
    assert client.get("/api/session-archives").json() == []


def test_session_archive_redacts_raw_prompt_secrets_paths_and_voice_transcript():
    store = SessionArchiveStore()
    result = store.archive_current(
        session_id="secret-session",
        events=[
            {
                "timestamp": _now(),
                "event_type": "voice_mode_used",
                "safe_summary": (
                    "full voice transcript raw prompt raw JSON: 我的 API key 是 sk-test-secret-1234567890，"
                    "路径 /Users/example/project/services/backend/.env，stdout stderr"
                ),
                "source": "voice_direct",
                "input_source": "voice_direct",
            },
            {
                "timestamp": _now(),
                "event_type": "knowledge_used",
                "safe_summary": "使用知识摘要：玛尔基特二阶段",
                "source": "knowledge",
            },
        ],
    )

    assert result["status"] == "created"
    serialized = json.dumps(result["archive"], ensure_ascii=False).lower()
    for forbidden in (
        ".env",
        "authorization",
        "api_key",
        "api key",
        "raw prompt",
        "raw json",
        "raw model response",
        "raw chat transcript",
        "full voice transcript",
        "full transcript",
        "stdout",
        "stderr",
        "secret",
        "/users/example",
        "sk-test-secret",
    ):
        assert forbidden not in serialized
    assert "voice_direct" in serialized
    assert result["archive"]["privacy_level"] == "sensitive"


def test_session_archive_does_not_enter_prompt_or_long_term_memory():
    store = SessionArchiveStore()
    result = store.archive_current(
        session_id="prompt-boundary",
        events=[
            {
                "timestamp": _now(),
                "event_type": "memory_accepted",
                "safe_summary": "确认记忆事件：玩家打 Boss 前喜欢先探索地图",
                "source": "memory",
            }
        ],
    )

    assert result["status"] == "created"
    profile = PlayerMemory().load_profile()
    prompt_text = PlayerMemory().build_prompt_context()
    retrieved = PlayerMemory().retrieve_prompt_memory(user_message="玛尔基特怎么打？", current_game="艾尔登法环")

    assert profile.long_term_memories == []
    assert "探索地图" not in prompt_text
    assert retrieved.memories == []
    assert retrieved.skip_reason == "no_active_memory"


def test_session_archive_does_not_change_pending_or_accepted_memory():
    queue = PendingMemoryQueue()
    pending = queue.generate_and_enqueue("我不喜欢长篇攻略", "", "casual_chat", datetime.now(timezone.utc), {})
    assert len(pending) == 1

    result = SessionArchiveStore().archive_current(session_id="pending-boundary", events=_events())

    assert result["status"] == "created"
    assert [item["id"] for item in queue.list()] == [pending[0]["id"]]
    assert PlayerMemory().load_profile().long_term_memories == []

    accepted = queue.accept(pending[0]["id"])
    long_term_id = accepted["long_term_memory_id"]
    assert long_term_id
    SessionArchiveStore().clear_archives()
    profile = PlayerMemory().load_profile()
    assert profile.long_term_memories[0]["id"] == long_term_id
    assert profile.long_term_memories[0]["is_active"] is True


def test_session_archive_repeated_archive_is_idempotent():
    store = SessionArchiveStore()
    events = _events()
    first = store.archive_current(session_id="same-session", events=events)
    second = store.archive_current(session_id="same-session", events=events)

    assert first["status"] == "created"
    assert second["status"] == "existing"
    assert first["archive"]["id"] == second["archive"]["id"]
    assert len(store.list_archives()) == 1


def test_session_archive_empty_timeline_skips_gracefully():
    result = client.post("/api/session-archives/archive-current", json={"session_id": "empty-session", "events": []})

    assert result.status_code == 200
    assert result.json()["status"] == "skipped"
    assert result.json()["archive"] is None
    assert client.get("/api/session-archives").json() == []
