import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "services" / "backend"

os.environ["LLM_PROVIDER"] = "mock"

sys.path.insert(0, str(BACKEND))


@pytest.fixture(autouse=True)
def isolate_player_memory(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.memory.profile.settings.user_profile_path", tmp_path / "user_profile.json")
    monkeypatch.setattr("app.modules.memory.profile.settings.episodes_path", tmp_path / "episodes.jsonl")
    monkeypatch.setattr("app.modules.memory.store.settings.conversations_dir", tmp_path / "conversations")
    monkeypatch.setattr("app.modules.game_session.state.settings.game_session_state_path", tmp_path / "game_session_state.json")
