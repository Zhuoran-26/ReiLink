import json

from fastapi.testclient import TestClient

from app.core import config
from app.main import app

client = TestClient(app)


def _patch_local_data_paths(monkeypatch, data_dir, knowledge_dir):
    monkeypatch.setattr("app.modules.local_data.status.settings.data_dir", data_dir)
    monkeypatch.setattr("app.modules.local_data.status.settings.memory_dir", data_dir / "memory")
    monkeypatch.setattr("app.modules.local_data.status.settings.session_dir", data_dir / "session")
    monkeypatch.setattr("app.modules.local_data.status.settings.settings_path", data_dir / "settings.json")
    monkeypatch.setattr("app.modules.local_data.status.settings.pending_memories_path", data_dir / "memory" / "pending_memories.jsonl")
    monkeypatch.setattr("app.modules.local_data.status.settings.knowledge_games_dir", knowledge_dir)


def test_local_data_status_returns_directory_state_and_counts(tmp_path, monkeypatch):
    data_dir = tmp_path / "user-data"
    memory_dir = data_dir / "memory"
    session_dir = data_dir / "session"
    knowledge_dir = tmp_path / "ReiLink.app" / "Contents" / "Resources" / "knowledge" / "games"
    memory_dir.mkdir(parents=True)
    session_dir.mkdir(parents=True)
    knowledge_dir.mkdir(parents=True)
    (knowledge_dir / "catalog.json").write_text('{"games":[]}\n', encoding="utf-8")
    (memory_dir / "user_profile.json").write_text("{}\n", encoding="utf-8")
    (memory_dir / "pending_memories.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"status": "pending", "text": "safe"}),
                json.dumps({"status": "accepted", "text": "safe"}),
                "{bad-json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (session_dir / "game_session_state.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("REILINK_KNOWLEDGE_DIR", str(knowledge_dir))
    _patch_local_data_paths(monkeypatch, data_dir, knowledge_dir)

    response = client.get("/api/local-data/status")

    assert response.status_code == 200
    data = response.json()
    assert data["data_dir"] == str(data_dir)
    assert data["memory_dir"] == str(memory_dir)
    assert data["session_dir"] == str(session_dir)
    assert data["settings_dir"] == str(data_dir / "settings")
    assert data["logs_dir"] == str(data_dir / "logs")
    assert data["knowledge_dir"] == str(knowledge_dir)
    assert data["knowledge_source"] == "bundled"
    assert data["data_dir_exists"] is True
    assert data["memory_files_count"] == 2
    assert data["session_files_count"] == 1
    assert data["pending_memory_count"] == 1
    assert data["using_bundled_knowledge"] is True
    assert data["writable"] is True


def test_local_data_status_handles_missing_directories(tmp_path, monkeypatch):
    data_dir = tmp_path / "missing-data"
    knowledge_dir = tmp_path / "missing-knowledge" / "games"
    _patch_local_data_paths(monkeypatch, data_dir, knowledge_dir)

    response = client.get("/api/local-data/status")

    assert response.status_code == 200
    data = response.json()
    assert data["data_dir_exists"] is False
    assert data["knowledge_source"] == "missing"
    assert data["memory_files_count"] == 0
    assert data["session_files_count"] == 0
    assert data["pending_memory_count"] == 0


def test_local_data_status_does_not_return_secrets(tmp_path, monkeypatch):
    data_dir = tmp_path / "user-data"
    knowledge_dir = tmp_path / "knowledge" / "games"
    data_dir.mkdir()
    knowledge_dir.mkdir(parents=True)
    (knowledge_dir / "catalog.json").write_text('{"games":[]}\n', encoding="utf-8")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret-key")
    monkeypatch.setattr("app.modules.local_data.status.settings.deepseek_api_key", "test-secret-key")
    _patch_local_data_paths(monkeypatch, data_dir, knowledge_dir)

    response = client.get("/api/local-data/status")

    serialized = json.dumps(response.json(), ensure_ascii=False).lower()
    assert response.status_code == 200
    assert "test-secret-key" not in serialized
    assert "api_key" not in serialized
    assert "authorization" not in serialized
    assert "bearer" not in serialized


def test_reilink_data_dir_resolver_supports_runtime_data_root(tmp_path, monkeypatch):
    data_dir = tmp_path / "runtime-data"
    monkeypatch.setenv("REILINK_DATA_DIR", str(data_dir))

    assert config._resolve_data_dir(tmp_path / "repo") == data_dir
