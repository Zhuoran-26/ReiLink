from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.modules.game_session.state import GameSessionState, GameSessionStore
from app.modules.memory.pending import PendingMemoryQueue
from app.modules.memory.store import ConversationStore
from app.modules.proactive.trigger import ProactiveCompanion


def _enable(sensitivity: str = "low", now: datetime | None = None) -> None:
    ProactiveCompanion().update_settings(enabled=True, sensitivity=sensitivity, now=now)


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
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_initial_grace_seconds", 5)
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable(now=now - timedelta(seconds=40))
    _append_user("idle", "你好", now - timedelta(seconds=31))

    result = ProactiveCompanion().check(session_id="idle", now=now)

    assert result["should_send"] is True
    assert result["trigger_type"] == "idle_silence"
    assert 0 < len(result["message"]) <= 12


def test_repeated_death_triggers_from_game_state():
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable(now=now)
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
    _enable(now=now)
    _append_user("late", "再打一把", now - timedelta(minutes=2))
    GameSessionStore().save(GameSessionState(current_game="Elden Ring", last_attempted_boss="恶兆妖鬼 Margit"))

    result = ProactiveCompanion().check(session_id="late", now=now)

    assert result["should_send"] is True
    assert result["trigger_type"] == "late_night"


def test_frustration_loop_triggers():
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable(now=now)
    _append_user("frustrated", "好烦，还是不行", now - timedelta(minutes=3))
    _append_user("frustrated", "真的烦死了", now - timedelta(minutes=2))

    result = ProactiveCompanion().check(session_id="frustrated", now=now)

    assert result["should_send"] is True
    assert result["trigger_type"] == "frustration_loop"


def test_cooldown_blocks_repeat(monkeypatch):
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_global_cooldown_seconds", 300)
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_type_cooldown_seconds", 600)
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable(now=now - timedelta(minutes=20))
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
    _enable(now=now - timedelta(minutes=20))
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


def test_enable_resets_idle_start_before_idle_can_trigger(monkeypatch):
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_idle_seconds", 30)
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_initial_grace_seconds", 5)
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _append_user("enable-reset", "很久没说话", now - timedelta(hours=2))

    _enable(now=now)
    result = ProactiveCompanion().check(session_id="enable-reset", now=now)

    assert result["should_send"] is False
    assert result["trigger_type"] == "none"
    assert result["idle_for_seconds"] == 0
    assert result["enabled_at"] == now.isoformat()


def test_idle_silence_waits_for_initial_grace(monkeypatch):
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_idle_seconds", 3)
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_initial_grace_seconds", 10)
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable(now=now - timedelta(seconds=5))
    _append_user("grace", "你好", now - timedelta(seconds=20))

    result = ProactiveCompanion().check(session_id="grace", now=now)

    assert result["should_send"] is False
    assert result["trigger_type"] == "none"
    assert result["initial_grace_remaining_seconds"] > 0


def test_idle_silence_triggers_after_initial_grace_and_threshold(monkeypatch):
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_idle_seconds", 3)
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_initial_grace_seconds", 5)
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable(now=now - timedelta(seconds=6))
    _append_user("grace-done", "你好", now - timedelta(seconds=40))

    result = ProactiveCompanion().check(session_id="grace-done", now=now)

    assert result["should_send"] is True
    assert result["trigger_type"] == "idle_silence"
    assert result["idle_for_seconds"] >= 3


def test_proactive_status_returns_idle_timing_fields(monkeypatch):
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_idle_seconds", 30)
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_initial_grace_seconds", 5)
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    enabled_at = now - timedelta(seconds=20)
    _enable(now=enabled_at)
    _append_user("status-fields", "你好", now - timedelta(seconds=7))

    status = ProactiveCompanion().status(session_id="status-fields", now=now)

    assert status["enabled_at"] == enabled_at.isoformat()
    assert status["last_user_activity_at"] == (now - timedelta(seconds=7)).isoformat()
    assert status["idle_for_seconds"] == 7
    assert status["idle_threshold_seconds"] == 30


def test_cooldown_and_idle_threshold_are_separate_debug_fields(monkeypatch):
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_idle_seconds", 30)
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_global_cooldown_seconds", 300)
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable(now=now - timedelta(minutes=20))
    _append_user("debug-separate", "你好", now - timedelta(minutes=20))
    state = ProactiveCompanion().load()
    state.last_triggered_at = (now - timedelta(seconds=60)).isoformat()
    ProactiveCompanion().save(state)

    status = ProactiveCompanion().status(session_id="debug-separate", now=now)

    assert status["cooldown_remaining_seconds"] == 240
    assert status["idle_threshold_seconds"] == 30


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
        "enabled_at",
        "last_user_activity_at",
        "idle_for_seconds",
        "idle_threshold_seconds",
        "initial_grace_remaining_seconds",
    } <= status.json().keys()


def test_settings_route_enable_records_enabled_at_and_blocks_old_idle(monkeypatch):
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_idle_seconds", 30)
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_initial_grace_seconds", 5)
    client = TestClient(app)
    now = datetime.now(timezone.utc)
    _append_user("settings-enable", "很久没说话", now - timedelta(hours=2))

    updated = client.post("/api/settings", json={"proactive_companion": "on", "proactive_sensitivity": "low"})
    assert updated.status_code == 200

    status = client.get("/api/proactive/status?session_id=settings-enable").json()
    assert status["enabled"] is True
    assert status["enabled_at"]
    assert status["idle_for_seconds"] < status["idle_threshold_seconds"]

    result = client.post("/api/proactive/check", json={"session_id": "settings-enable"}).json()
    assert result["should_send"] is False
    assert result["trigger_type"] == "none"


def test_last_proactive_message_blocks_consecutive_trigger(monkeypatch):
    monkeypatch.setattr("app.modules.proactive.trigger.settings.proactive_idle_seconds", 30)
    now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    _enable(now=now - timedelta(minutes=20))
    _append_user("consecutive", "你好", now - timedelta(seconds=40))
    first = ProactiveCompanion().check(session_id="consecutive", now=now)

    second = ProactiveCompanion().check(session_id="consecutive", now=now + timedelta(minutes=20))

    assert first["should_send"] is True
    assert second["should_send"] is False
    assert second["reason"] == "last_message_proactive"
