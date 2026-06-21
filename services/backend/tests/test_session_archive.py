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


def _safe_event(
    event_type: str,
    summary: str,
    *,
    game: str,
    entity: str | None = None,
    source: str = "game_session",
) -> dict:
    return {
        "id": f"event-{event_type}-{game}",
        "timestamp": _now(),
        "event_type": event_type,
        "safe_summary": summary,
        "source": source,
        "related_game": game,
        "related_entity": entity,
    }


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


def test_session_archive_search_filters_keywords_and_safe_metadata():
    store = SessionArchiveStore()
    elden = store.archive_current(
        session_id="search-elden",
        events=_events(),
        game="艾尔登法环",
        boss="恶兆妖鬼 Margit",
    )["archive"]
    hollow = store.archive_current(
        session_id="search-hollow",
        events=[
            _safe_event("game_selected", "游戏：空洞骑士", game="空洞骑士", source="game_context"),
            _safe_event("boss_detected", "Boss：Hornet", game="空洞骑士", entity="Hornet"),
            _safe_event("boss_cleared", "已击败 Boss：Hornet", game="空洞骑士", entity="Hornet"),
        ],
        game="空洞骑士",
        boss="Hornet",
    )["archive"]

    by_keyword = store.search_archives(q="死亡")
    assert by_keyword["total"] == 1
    assert by_keyword["results"][0]["archive_id"] == elden["id"]
    assert by_keyword["results"][0]["event_id"] == "event-deaths"
    assert by_keyword["results"][0]["reason"] == "关键词命中安全事件摘要"
    assert "死亡次数更新：3" in by_keyword["safe_result_summaries"]

    by_game = store.search_archives(game="空洞")
    assert by_game["total"] == 1
    assert by_game["results"][0]["archive_id"] == hollow["id"]
    assert by_game["results"][0]["matched_tags"] == ["game"]

    by_boss = store.search_archives(boss="margit")
    assert by_boss["total"] == 1
    assert by_boss["results"][0]["archive_id"] == elden["id"]

    by_type = store.search_archives(event_type="boss_cleared")
    assert by_type["total"] == 1
    assert by_type["results"][0]["archive_id"] == hollow["id"]
    assert by_type["results"][0]["event_type"] == "boss_cleared"

    combined = store.search_archives(q="Boss", game="空洞骑士", boss="Hornet", event_type="boss_detected")
    assert combined["total"] == 1
    assert combined["results"][0]["archive_id"] == hollow["id"]

    limited = store.search_archives(limit=1)
    assert limited["total"] == 2
    assert limited["omitted_count"] == 1
    assert len(limited["results"]) == 1


def test_session_archive_search_covers_stored_safe_event_summaries():
    store = SessionArchiveStore()
    now = _now()
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(
        json.dumps(
            {
                "archives": [
                    {
                        "id": "archive-safe-summaries-only",
                        "session_id": "legacy-safe-summary",
                        "title": "旧归档",
                        "created_at": now,
                        "updated_at": now,
                        "started_at": now,
                        "ended_at": now,
                        "source": "manual",
                        "game": "空洞骑士",
                        "boss": "Hornet",
                        "summary": "本局保存了安全摘要。",
                        "event_count": 1,
                        "safe_event_summaries": ["安全事件：发现隐藏道路"],
                        "events": [],
                        "is_deleted": False,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = store.search_archives(q="隐藏道路")

    assert result["total"] == 1
    assert result["results"][0]["archive_id"] == "archive-safe-summaries-only"
    assert result["results"][0]["safe_summary"] == "安全事件：发现隐藏道路"
    assert result["results"][0]["reason"] == "关键词命中安全事件摘要"


def test_session_archive_search_excludes_deleted_and_handles_empty_results():
    store = SessionArchiveStore()
    archive = store.archive_current(session_id="deleted-search", events=_events())["archive"]

    store.delete_archive(archive["id"])

    deleted_search = store.search_archives(q="艾尔登法环")
    assert deleted_search == {"results": [], "total": 0, "omitted_count": 0, "safe_result_summaries": []}
    assert store.search_archives(q="不存在的 Boss")["results"] == []


def test_session_archive_search_api_returns_safe_result_shape():
    created = client.post(
        "/api/session-archives/archive-current",
        json={"session_id": "api-search", "events": _events(), "game": "艾尔登法环", "boss": "恶兆妖鬼 Margit"},
    )
    archive_id = created.json()["archive"]["id"]

    response = client.get(
        "/api/session-archives/search",
        params={"q": "玛尔基特", "game": "艾尔登", "boss": "Margit", "event_type": "knowledge_used", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["omitted_count"] == 0
    assert payload["results"][0]["archive_id"] == archive_id
    assert payload["results"][0]["event_type"] == "knowledge_used"
    assert payload["results"][0]["safe_summary"] == "使用知识摘要：玛尔基特二阶段"
    assert payload["safe_result_summaries"] == ["使用知识摘要：玛尔基特二阶段"]


def test_session_archive_search_redacts_raw_secret_and_does_not_mutate_memory_or_prompt():
    store = SessionArchiveStore()
    result = store.archive_current(
        session_id="search-secret-boundary",
        events=[
            {
                "id": "unsafe-event",
                "timestamp": _now(),
                "event_type": "session_note",
                "safe_summary": (
                    "raw prompt raw JSON Authorization bearer token secret=TEST_SECRET_PLACEHOLDER "
                    "/Users/example/project/services/backend/.env stdout stderr"
                ),
                "source": "manual",
            },
            _safe_event("boss_detected", "Boss：恶兆妖鬼 Margit", game="艾尔登法环", entity="恶兆妖鬼 Margit"),
        ],
        game="艾尔登法环",
        boss="恶兆妖鬼 Margit",
    )

    assert result["status"] == "created"
    search = store.search_archives(q="TEST_SECRET_PLACEHOLDER")
    serialized = json.dumps(search, ensure_ascii=False).lower()
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
        "TEST_SECRET_PLACEHOLDER",
    ):
        assert forbidden not in serialized

    profile = PlayerMemory().load_profile()
    prompt_text = PlayerMemory().build_prompt_context()
    retrieved = PlayerMemory().retrieve_prompt_memory(user_message="找一下归档", current_game="艾尔登法环")
    assert profile.long_term_memories == []
    assert "恶兆妖鬼" not in prompt_text
    assert retrieved.memories == []


def test_session_archive_redacts_raw_prompt_secrets_paths_and_voice_transcript():
    store = SessionArchiveStore()
    result = store.archive_current(
        session_id="secret-session",
        events=[
            {
                "timestamp": _now(),
                "event_type": "voice_mode_used",
                "safe_summary": (
                    "full voice transcript raw prompt raw JSON: 我的 api_key=TEST_SECRET_PLACEHOLDER，"
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
        "TEST_SECRET_PLACEHOLDER",
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
