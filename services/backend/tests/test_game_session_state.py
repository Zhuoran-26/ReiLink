from datetime import datetime, timedelta, timezone

import pytest

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


@pytest.mark.parametrize(
    "message",
    [
        "没打过",
        "还没过",
        "还是没打过",
        "打不过",
        "一直打不过",
        "又死了",
    ],
)
def test_negated_clear_words_keep_current_boss_failed(tmp_path, message):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now(timezone.utc)
    store.update_from_user_message("我现在卡在恶兆妖鬼", "casual_chat", _idle_status(), now)

    state = store.update_from_user_message(message, "casual_chat", _idle_status(), now + timedelta(minutes=1))

    assert state.current_boss is not None
    assert state.current_boss.name == "恶兆妖鬼 Margit"
    assert state.current_activity == "boss_failed"
    assert state.last_attempted_boss == "恶兆妖鬼 Margit"
    assert state.last_cleared_boss is None
    assert state.last_game_intent == "boss_failed"
    assert any(entry.name == "恶兆妖鬼 Margit" and entry.status == "failed" for entry in state.boss_history)


def test_failure_after_cleared_reopens_recent_boss(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now(timezone.utc)
    store.update_from_user_message("我现在卡在恶兆妖鬼", "casual_chat", _idle_status(), now)
    store.update_from_user_message("打过了", "casual_chat", _idle_status(), now + timedelta(minutes=1))

    state = store.update_from_user_message("不是打过了，是没打过", "casual_chat", _idle_status(), now + timedelta(minutes=2))

    assert state.current_boss is not None
    assert state.current_boss.name == "恶兆妖鬼 Margit"
    assert state.current_activity == "boss_failed"
    assert state.last_cleared_boss is None
    assert any(entry.name == "恶兆妖鬼 Margit" and entry.status == "failed" for entry in state.boss_history)


def test_negated_failure_phrase_can_clear_current_boss(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now(timezone.utc)
    store.update_from_user_message("我现在卡在恶兆妖鬼", "casual_chat", _idle_status(), now)

    state = store.update_from_user_message("不是没打过", "casual_chat", _idle_status(), now + timedelta(minutes=1))

    assert state.current_boss is None
    assert state.current_activity == "boss_cleared"
    assert state.last_cleared_boss == "恶兆妖鬼 Margit"
    assert state.last_game_intent == "boss_cleared"


def test_explicit_new_boss_overwrites_previous_boss(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now(timezone.utc)
    store.update_from_user_message("我现在卡在女武神", "casual_chat", _idle_status(), now)

    state = store.update_from_user_message("我现在卡在拉塔恩", "casual_chat", _idle_status(), now + timedelta(minutes=10))

    assert state.current_boss is not None
    assert state.current_boss.name == "拉塔恩"
    assert state.current_boss.mention_count == 1


def test_switch_to_old_general_oneil_and_keep_elliptical_focus(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now(timezone.utc)
    store.update_from_user_message("我现在卡在女武神", "casual_chat", _idle_status(), now)
    switching = store.update_from_user_message("算了，我先去打别的 boss", "casual_chat", _idle_status(), now + timedelta(minutes=1))

    assert switching.current_boss is None
    assert switching.last_attempted_boss == "女武神"
    assert any(entry.name == "女武神" and entry.status == "abandoned" for entry in switching.boss_history)

    old_general = store.update_from_user_message("那我就去打老将欧尼尔", "casual_chat", _idle_status(), now + timedelta(minutes=2))

    assert old_general.current_boss is not None
    assert old_general.current_boss.name == "老将欧尼尔"
    assert old_general.last_attempted_boss == "老将欧尼尔"
    assert old_general.last_game_intent == "boss_attempt"

    state = store.update_from_user_message("也打不过又死了", "casual_chat", _idle_status(), now + timedelta(minutes=3))

    assert state.current_boss is not None
    assert state.current_boss.name == "老将欧尼尔"
    assert state.current_boss.source == "current_context"
    assert state.current_activity == "boss_failed"
    assert state.death_count == 1
    assert state.last_game_intent == "boss_failed"


def test_clear_old_general_records_recent_history(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now(timezone.utc)
    store.update_from_user_message("我现在卡在女武神", "casual_chat", _idle_status(), now)
    store.update_from_user_message("那我就去打老将欧尼尔", "casual_chat", _idle_status(), now + timedelta(minutes=1))

    state = store.update_from_user_message("打过老将了", "casual_chat", _idle_status(), now + timedelta(minutes=2))

    assert state.current_boss is None
    assert state.current_activity == "boss_cleared"
    assert state.last_boss == "老将欧尼尔"
    assert state.last_attempted_boss == "老将欧尼尔"
    assert state.last_cleared_boss == "老将欧尼尔"
    assert state.last_game_intent == "boss_cleared"
    assert "老将欧尼尔" in state.recent_game_topics
    assert "老将欧尼尔已结束" in state.recent_game_topics
    assert any(entry.name == "老将欧尼尔" and entry.status == "cleared" for entry in state.boss_history)


def test_history_summary_after_boss_cleared_does_not_claim_current(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now(timezone.utc)
    store.update_from_user_message("我现在卡在女武神", "casual_chat", _idle_status(), now)
    store.update_from_user_message("那我就去打老将欧尼尔", "casual_chat", _idle_status(), now + timedelta(minutes=1))
    store.update_from_user_message("老将打完了", "casual_chat", _idle_status(), now + timedelta(minutes=2))

    summary = store.build_prompt_summary(now + timedelta(minutes=3))

    assert "刚刚结束的 boss 是 老将欧尼尔" in summary
    assert "当前没有正在打的 boss" in summary
    assert "女武神已结束" not in summary


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
