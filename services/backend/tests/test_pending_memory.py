import json
from datetime import datetime, timezone
from pathlib import Path

from app.modules.dialogue_agent.prompt_preview import build_prompt_preview
from app.modules.memory.pending import PendingMemoryQueue
from app.modules.memory.profile import PlayerMemory


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _game_state(
    *,
    current_boss: str | None = None,
    current_activity: str | None = None,
    last_cleared_boss: str | None = None,
) -> dict:
    return {
        "current_game": "Elden Ring",
        "current_boss": {"name": current_boss} if current_boss else None,
        "current_activity": current_activity,
        "last_attempted_boss": current_boss,
        "last_cleared_boss": last_cleared_boss,
    }


def test_explicit_long_guide_preference_creates_pending_memory():
    created = PendingMemoryQueue().generate_and_enqueue(
        "我不喜欢长篇攻略",
        "",
        "casual_chat",
        _now(),
        {},
    )

    assert len(created) == 1
    assert created[0]["type"] == "user_preference"
    assert created[0]["text"] == "玩家不喜欢长篇攻略"
    assert created[0]["source"] == "explicit_user_statement"
    assert created[0]["status"] == "pending"


def test_explicit_short_guide_preference_creates_pending_memory():
    created = PendingMemoryQueue().generate_and_enqueue(
        "我喜欢简短的游戏攻略",
        "",
        "casual_chat",
        _now(),
        {},
    )

    assert len(created) == 1
    assert created[0]["type"] == "user_preference"
    assert created[0]["text"] == "玩家喜欢简短的游戏攻略"
    assert created[0]["source"] == "explicit_user_statement"


def test_explicit_spirit_ashes_preference_creates_playstyle_pending_memory():
    created = PendingMemoryQueue().generate_and_enqueue(
        "我不想召骨灰",
        "",
        "casual_chat",
        _now(),
        {},
    )

    assert len(created) == 1
    assert created[0]["type"] == "playstyle"
    assert "骨灰" in created[0]["text"]


def test_plain_personal_preference_without_remember_is_not_pending_memory():
    created = PendingMemoryQueue().generate_and_enqueue(
        "我喜欢吃菠萝",
        "",
        "casual_chat",
        _now(),
        {},
    )

    assert created == []
    assert PendingMemoryQueue().list() == []


def test_explicit_personal_preference_with_remember_creates_pending_memory():
    created = PendingMemoryQueue().generate_and_enqueue(
        "记住我喜欢吃菠萝",
        "",
        "casual_chat",
        _now(),
        {},
    )

    assert len(created) == 1
    assert created[0]["type"] == "user_preference"
    assert created[0]["text"] == "玩家喜欢吃菠萝"
    assert created[0]["source"] == "explicit_user_statement"


def test_semantic_memory_candidate_creates_pending_memory():
    semantic = {
        "final_decision": {
            "memory_candidate": {
                "should_create_pending": True,
                "type": "guide_preference",
                "text": "玩家喜欢简短提醒",
                "confidence": 0.86,
                "reason": "用户表达偏好",
            }
        }
    }

    created = PendingMemoryQueue().generate_and_enqueue(
        "短一点",
        "",
        "casual_chat",
        _now(),
        {},
        semantic_extraction=semantic,
    )

    assert len(created) == 1
    assert created[0]["type"] == "user_preference"
    assert created[0]["text"] == "玩家喜欢简短提醒"
    assert created[0]["source"] == "semantic_extraction"


def test_death_loop_does_not_create_long_term_pending_memory():
    created = PendingMemoryQueue().generate_and_enqueue(
        "我又死了",
        "",
        "casual_chat",
        _now(),
        _game_state(current_boss="女武神", current_activity="boss_failed"),
    )

    assert created == []
    assert PendingMemoryQueue().list() == []


def test_boss_cleared_game_state_creates_game_progress_pending_memory():
    created = PendingMemoryQueue().generate_and_enqueue(
        "打过大树守卫了",
        "",
        "casual_chat",
        _now(),
        _game_state(current_activity="boss_cleared", last_cleared_boss="大树守卫"),
    )

    assert len(created) == 1
    assert created[0]["type"] == "game_progress"
    assert created[0]["text"] == "玩家已经打过大树守卫"
    assert created[0]["source"] == "game_session"


def test_accept_pending_memory_writes_profile_and_episode():
    queue = PendingMemoryQueue()
    created = queue.generate_and_enqueue(
        "我不喜欢长篇攻略",
        "",
        "casual_chat",
        _now(),
        {},
    )

    accepted = queue.accept(created[0]["id"])
    profile = PlayerMemory().load_profile()
    episodes = PlayerMemory().recent_episodes(limit=5)

    assert accepted["status"] == "accepted"
    assert profile.preferred_tone == "不喜欢长篇攻略"
    assert any(episode["summary"] == "玩家不喜欢长篇攻略" for episode in episodes)


def test_ignore_pending_memory_does_not_write_long_term_memory():
    queue = PendingMemoryQueue()
    created = queue.generate_and_enqueue(
        "我不喜欢长篇攻略",
        "",
        "casual_chat",
        _now(),
        {},
    )

    ignored = queue.ignore(created[0]["id"])
    profile = PlayerMemory().load_profile()

    assert ignored["status"] == "ignored"
    assert profile.preferred_tone is None
    assert PlayerMemory().recent_episodes(limit=5) == []


def test_pending_memory_is_not_in_prompt_preview_until_accepted():
    queue = PendingMemoryQueue()
    created = queue.generate_and_enqueue(
        "我不喜欢长篇攻略",
        "",
        "casual_chat",
        _now(),
        {},
    )

    preview = build_prompt_preview()
    pending_preview_text = json.dumps(preview["memory_summary"], ensure_ascii=False)

    assert "不喜欢长篇攻略" not in pending_preview_text

    queue.accept(created[0]["id"])
    accepted_preview = build_prompt_preview()
    accepted_preview_text = json.dumps(accepted_preview["memory_summary"], ensure_ascii=False)

    assert "不喜欢长篇攻略" in accepted_preview_text


def test_duplicate_pending_memory_is_not_generated_twice():
    queue = PendingMemoryQueue()
    first = queue.generate_and_enqueue("我不喜欢长篇攻略", "", "casual_chat", _now(), {})
    second = queue.generate_and_enqueue("不要给我长篇攻略", "", "casual_chat", _now(), {})

    assert len(first) == 1
    assert second == []
    assert len(queue.list()) == 1


def test_pending_memory_file_is_gitignored():
    gitignore = Path(__file__).resolve().parents[3] / ".gitignore"

    assert "data/memory/pending_memories.jsonl" in gitignore.read_text(encoding="utf-8")
