import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "services" / "backend"

os.environ["LLM_PROVIDER"] = "mock"

sys.path.insert(0, str(BACKEND))
sys.path.append(str(ROOT))


@pytest.fixture(autouse=True)
def isolate_player_memory(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.memory.profile.settings.user_profile_path", tmp_path / "user_profile.json")
    monkeypatch.setattr("app.modules.memory.profile.settings.episodes_path", tmp_path / "episodes.jsonl")
    monkeypatch.setattr("app.modules.memory.pending.settings.pending_memories_path", tmp_path / "pending_memories.jsonl")
    monkeypatch.setattr("app.modules.memory.store.settings.conversations_dir", tmp_path / "conversations")
    monkeypatch.setattr("app.modules.game_session.state.settings.game_session_state_path", tmp_path / "game_session_state.json")
    monkeypatch.setattr("app.modules.game_context.context.settings.game_context_state_path", tmp_path / "game_context_state.json")
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_state_path", tmp_path / "proactive_state.json")
    monkeypatch.setattr("app.modules.session_archive.store.settings.session_archives_path", tmp_path / "session_archives.json")
    monkeypatch.setattr("app.core.config.settings.settings_path", tmp_path / "settings.json")
    monkeypatch.setattr("app.core.config.settings.game_registry_path", tmp_path / "game_registry.json")


@pytest.fixture(autouse=True)
def isolate_local_asr_settings_file(tmp_path, monkeypatch, request):
    test_file = Path(str(request.fspath)).name
    if not test_file.startswith("test_local_asr_"):
        return
    data_dir = tmp_path / "local_asr_data"
    data_dir.mkdir()
    monkeypatch.setattr("app.core.config.settings.data_dir", data_dir)
