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


def test_memory_reset_route():
    client.post("/api/chat", json={"message": "Margit 我又死了", "session_id": "api-memory-reset"})
    response = client.post("/api/memory/reset")

    assert response.status_code == 200
    assert response.json() == {"status": "reset"}
    assert client.get("/api/memory/profile").json()["current_boss"] is None
    assert client.get("/api/memory/episodes").json() == []
