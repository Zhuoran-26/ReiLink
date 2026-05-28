import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def assert_chinese_reply(reply: str):
    assert "##" not in reply
    assert any("\u4e00" <= char <= "\u9fff" for char in reply)


def test_health_ok():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_game_status_schema():
    data = client.get("/api/game/status").json()
    assert {"game_id", "game_name", "process_name", "status", "confidence", "tags"} <= data.keys()


def test_chat_returns_chinese_reply():
    response = client.post("/api/chat", json={"message": "Margit 怎么打", "session_id": "api-test"})
    assert response.status_code == 200
    assert_chinese_reply(response.json()["reply"])


def test_identity_chat_has_no_sources():
    response = client.post("/api/chat", json={"message": "你是谁", "session_id": "api-identity"})
    assert response.status_code == 200
    data = response.json()
    assert data["sources"] == []
    assert_chinese_reply(data["reply"])


def test_invalid_chat_input_returns_422():
    response = client.post("/api/chat", json={"message": "", "session_id": "api-test"})
    assert response.status_code == 422


def test_debug_provider_returns_current_provider():
    response = client.get("/api/debug/provider")
    assert response.status_code == 200
    data = response.json()
    assert {
        "provider",
        "model",
        "base_url",
        "api_key_loaded",
        "configured_provider",
        "fallback_to_mock",
        "env_file_loaded",
        "env_file_path",
        "persona_mode",
    } <= data.keys()
    assert isinstance(data["api_key_loaded"], bool)
    assert isinstance(data["fallback_to_mock"], bool)
    assert isinstance(data["env_file_loaded"], bool)
    assert data["persona_mode"] in {"guarded", "minimal"}


def test_debug_chat_returns_last_latency_fields():
    client.post("/api/chat", json={"message": "你好", "session_id": "api-debug-chat"})

    response = client.get("/api/debug/chat")

    assert response.status_code == 200
    data = response.json()
    assert {
        "intent",
        "selected_model",
        "thinking_enabled",
        "reasoning_effort",
        "prompt_tokens_estimate",
        "llm_latency_ms",
        "memory_latency_ms",
        "total_latency_ms",
    } <= data.keys()


def test_memory_profile_and_episodes_routes():
    client.post("/api/chat", json={"message": "Margit 我又死了", "session_id": "api-memory"})

    profile = client.get("/api/memory/profile")
    assert profile.status_code == 200
    assert profile.json()["current_boss"] == "恶兆妖鬼 Margit"

    episodes = client.get("/api/memory/episodes")
    assert episodes.status_code == 200
    assert episodes.json()[0]["boss"] == "恶兆妖鬼 Margit"


def test_debug_memory_returns_provenance_items():
    client.post("/api/chat", json={"message": "Margit 我又死了", "session_id": "api-memory-debug"})

    response = client.get("/api/debug/memory?session_id=api-memory-debug")

    assert response.status_code == 200
    data = response.json()
    assert data["prompt_order"] == ["current_user_message", "current_session", "memory", "persona"]
    assert data["memory_written"] is True
    assert data["current_boss"] == "恶兆妖鬼 Margit"
    assert data["recent_episode_count"] >= 1
    sources = {item["source"] for item in data["items"]}
    assert {"current_session", "profile", "episode"} <= sources
    assert all(item["text"] for item in data["items"])


def test_debug_game_session_routes():
    client.post("/api/debug/game-session/reset")
    client.post("/api/chat", json={"message": "我现在卡在女武神", "session_id": "api-game-session"})

    response = client.get("/api/debug/game-session")

    assert response.status_code == 200
    data = response.json()
    assert data["current_game"] == "Elden Ring"
    assert data["current_boss"]["name"] == "女武神"
    assert data["current_boss"]["confidence"] >= 0.9
    assert data["current_boss"]["is_fresh"] is True
    assert {
        "last_boss",
        "last_attempted_boss",
        "last_cleared_boss",
        "boss_history",
        "death_count",
        "frustration_count",
        "last_game_intent",
    } <= data.keys()
    assert data["last_attempted_boss"] == "女武神"
    assert data["boss_history"][0]["name"] == "女武神"

    reset = client.post("/api/debug/game-session/reset")
    assert reset.status_code == 200
    assert reset.json() == {"status": "reset"}
    assert client.get("/api/debug/game-session").json()["current_boss"] is None


def test_prompt_preview_endpoint_returns_structured_context_without_secrets():
    session_id = "api-prompt-preview"
    client.post("/api/debug/game-session/reset")
    client.post("/api/chat", json={"message": "我现在卡在女武神", "session_id": session_id})

    response = client.get(f"/api/debug/prompt-preview?session_id={session_id}")

    assert response.status_code == 200
    data = response.json()
    assert {
        "persona_mode",
        "current_user_message",
        "prompt_order",
        "session_focus_summary",
        "game_state_summary",
        "memory_summary",
        "final_context_summary",
        "warnings",
    } <= data.keys()
    assert data["persona_mode"] in {"guarded", "minimal"}
    assert data["current_user_message"] == "我现在卡在女武神"
    assert data["game_state_summary"]["current_game"] == "Elden Ring"
    assert data["game_state_summary"]["current_boss"]["name"] == "女武神"
    assert data["game_state_summary"]["freshness"] == "fresh"
    assert isinstance(data["memory_summary"]["injected"], list)
    assert isinstance(data["memory_summary"]["skipped"], list)
    assert data["final_context_summary"]["raw_prompt_omitted"] is True
    serialized = json.dumps(data, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "deepseek_api_key" not in serialized
    assert "authorization" not in serialized


def test_prompt_preview_warns_on_negated_clear_phrase():
    session_id = "api-prompt-preview-negated-clear"
    client.post("/api/debug/game-session/reset")
    client.post("/api/chat", json={"message": "我现在卡在恶兆妖鬼", "session_id": session_id})
    client.post("/api/chat", json={"message": "还是没打过", "session_id": session_id})

    response = client.get(f"/api/debug/prompt-preview?session_id={session_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["current_user_message"] == "还是没打过"
    assert data["game_state_summary"]["current_activity"] == "boss_failed"
    assert data["game_state_summary"]["current_boss"]["name"] == "恶兆妖鬼 Margit"
    assert data["game_state_summary"]["last_cleared_boss"] != "恶兆妖鬼 Margit"
    assert "current user message contains negated clear phrase" in data["warnings"]


def test_memory_reset_route():
    client.post("/api/chat", json={"message": "Margit 我又死了", "session_id": "api-memory-reset"})
    response = client.post("/api/memory/reset")

    assert response.status_code == 200
    assert response.json() == {"status": "reset"}
    assert client.get("/api/memory/profile").json()["current_boss"] is None
    assert client.get("/api/memory/episodes").json() == []
