from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.modules.app_settings.store import AppSettingsStore
from app.modules.game_session.state import GameSessionState, GameSessionStore
from app.modules.memory.pending import PendingMemoryQueue
from app.modules.memory.store import ConversationStore
from app.modules.proactive.trigger import ProactiveCompanion, ProactiveState
from app.schemas.api import AppSettingsUpdate


def _enable(sensitivity: str = "low") -> None:
    AppSettingsStore().save(AppSettingsUpdate(proactive_companion="on", proactive_sensitivity=sensitivity))


def _append_user(session_id: str, message: str, timestamp: datetime) -> None:
    ConversationStore().append(
        session_id=session_id,
        game_id="elden_ring",
        persona_id="rei_like",
        user_message=message,
        assistant_reply="嗯。",
        timestamp=timestamp,
    )


def test_proactive_disabled_never_triggers(monkeypatch):
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_idle_seconds", 30)
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _append_user("disabled", "你好", now - timedelta(minutes=20))

    result = ProactiveCompanion().check(session_id="disabled", now=now)

    assert result["should_send"] is False
    assert result["reason"] == "disabled"


def test_idle_silence_after_threshold_triggers(monkeypatch):
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_idle_seconds", 30)
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable()
    _append_user("idle", "你好", now - timedelta(seconds=31))

    result = ProactiveCompanion().check(session_id="idle", now=now)

    assert result["should_send"] is True
    assert result["trigger_type"] == "idle_silence"
    assert 0 < len(result["message"]) <= 12


def test_repeated_death_triggers_from_game_state():
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable()
    _append_user("death", "我又死了", now - timedelta(minutes=2))
    GameSessionStore().save(
        GameSessionState(
            current_game="Elden Ring",
            death_count=2,
            last_updated_at=(now - timedelta(minutes=1)).isoformat(),
        )
    )

    result = ProactiveCompanion().check(session_id="death", now=now)

    assert result["should_send"] is True
    assert result["trigger_type"] == "repeated_death"
    assert result["message"]


def test_late_night_triggers_with_active_boss():
    now = datetime(2026, 5, 31, 23, 45, tzinfo=timezone.utc)
    _enable()
    _append_user("late", "再打一把", now - timedelta(minutes=2))
    GameSessionStore().save(GameSessionState(current_game="Elden Ring", last_attempted_boss="恶兆妖鬼 Margit"))

    result = ProactiveCompanion().check(session_id="late", now=now)

    assert result["should_send"] is True
    assert result["trigger_type"] == "late_night"


def test_frustration_loop_triggers():
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable()
    _append_user("frustrated", "好烦，还是不行", now - timedelta(minutes=3))
    _append_user("frustrated", "真的烦死了", now - timedelta(minutes=2))

    result = ProactiveCompanion().check(session_id="frustrated", now=now)

    assert result["should_send"] is True
    assert result["trigger_type"] == "frustration_loop"


def test_cooldown_blocks_repeat(monkeypatch):
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_global_cooldown_seconds", 300)
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_type_cooldown_seconds", 600)
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable()
    _append_user("cooldown", "你好", now - timedelta(minutes=20))
    state = ProactiveCompanion().load()
    state.last_triggered_at = (now - timedelta(seconds=60)).isoformat()
    state.trigger_cooldowns["idle_silence"] = (now - timedelta(seconds=60)).isoformat()
    ProactiveCompanion().save(state)

    result = ProactiveCompanion().check(session_id="cooldown", now=now)

    assert result["should_send"] is False
    assert result["reason"] == "cooldown"
    assert result["cooldown_remaining_seconds"] > 0


def test_proactive_message_does_not_enter_pending_memory_or_change_game_state():
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable()
    _append_user("safe", "你好", now - timedelta(minutes=20))
    before = GameSessionStore().debug_state(now=now)

    result = ProactiveCompanion().check(session_id="safe", now=now)
    after = GameSessionStore().debug_state(now=now)

    assert result["should_send"] is True
    assert PendingMemoryQueue().list() == []
    assert after == before
    entries = ConversationStore().read_session("safe")
    assert entries[-1].assistant_message_type == "proactive"
    assert entries[-1].trigger_type == "idle_silence"


def test_proactive_status_and_settings_routes():
    client = TestClient(app)

    updated = client.post("/api/proactive/settings", json={"enabled": True, "sensitivity": "high"})
    assert updated.status_code == 200
    assert updated.json()["enabled"] is True
    assert updated.json()["sensitivity"] == "high"

    status = client.get("/api/proactive/status")
    assert status.status_code == 200
    assert {
        "enabled",
        "sensitivity",
        "last_triggered_at",
        "last_triggered_type",
        "next_possible_trigger_at",
        "active_candidate_triggers",
        "last_trigger_reason",
    } <= status.json().keys()


def test_last_proactive_message_blocks_consecutive_trigger(monkeypatch):
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_idle_seconds", 30)
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable()
    _append_user("consecutive", "你好", now - timedelta(seconds=40))
    first = ProactiveCompanion().check(session_id="consecutive", now=now)

    second = ProactiveCompanion().check(session_id="consecutive", now=now + timedelta(minutes=20))

    assert first["should_send"] is True
    assert second["should_send"] is False
    assert second["reason"] == "last_message_proactive"
