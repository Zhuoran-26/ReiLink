from datetime import datetime, timedelta, timezone

from app.modules.game_session.state import CurrentBoss, GameSessionState, GameSessionStore


def _idle_status():
    return {"game_id": None, "game_name": None, "process_name": None, "status": "idle", "confidence": 0, "tags": []}


def test_explicit_current_boss_updates_game_session_state(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now(timezone.utc)

    state = store.update_from_user_message("我现在卡在女武神", "casual_chat", _idle_status(), now)

    assert state.current_game == "Elden Ring"
    assert state.current_boss is not None
    assert state.current_boss.name == "女武神"
    assert state.current_boss.source == "current_message"
    assert state.current_boss.confidence >= 0.9


def test_elliptical_death_loop_uses_fresh_current_boss(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now(timezone.utc)
    store.update_from_user_message("我现在卡在女武神", "casual_chat", _idle_status(), now)

    state = store.update_from_user_message("我又死了，一直打不过啊", "casual_chat", _idle_status(), now + timedelta(minutes=2))

    assert state.current_boss is not None
    assert state.current_boss.name == "女武神"
    assert state.current_boss.mention_count == 2
    assert state.death_count == 1
    assert state.frustration_count == 2


def test_boss_clear_message_removes_current_boss(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now(timezone.utc)
    store.update_from_user_message("我现在卡在女武神", "casual_chat", _idle_status(), now)

    state = store.update_from_user_message("女武神过了", "casual_chat", _idle_status(), now + timedelta(minutes=5))

    assert state.current_boss is None
    assert state.current_activity == "boss_cleared"


def test_explicit_new_boss_overwrites_previous_boss(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now(timezone.utc)
    store.update_from_user_message("我现在卡在女武神", "casual_chat", _idle_status(), now)

    state = store.update_from_user_message("我现在卡在拉塔恩", "casual_chat", _idle_status(), now + timedelta(minutes=10))

    assert state.current_boss is not None
    assert state.current_boss.name == "拉塔恩"
    assert state.current_boss.mention_count == 1


def test_stale_current_boss_is_not_injected_as_current(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    old = datetime.now(timezone.utc) - timedelta(hours=73)
    store.save(
        GameSessionState(
            current_game="Elden Ring",
            current_boss=CurrentBoss("女武神", old.isoformat(), 0.95, "current_message", 1),
            last_updated_at=old.isoformat(),
        )
    )

    summary = store.build_prompt_summary(datetime.now(timezone.utc))

    assert "已超过 72 小时" in summary
    assert "玩家最近在打 女武神" not in summary


def test_game_session_does_not_guess_boss_without_evidence(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")

    state = store.update_from_user_message("我又死了", "casual_chat", _idle_status(), datetime.now(timezone.utc))

    assert state.current_boss is None
    assert "暂无明确当前 boss" not in store.build_prompt_summary()
