import json
from datetime import datetime, timedelta, timezone

from app.modules.memory.profile import PlayerMemory


def test_memory_updates_profile_from_boss_struggle(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")

    memory.extract_and_update(
        "Margit 我又死了，打不过",
        "还是 Margit……你又急了",
        "elden_ring_boss_strategy",
        datetime.now(timezone.utc),
    )

    profile = memory.load_profile()
    assert profile.current_boss == "恶兆妖鬼 Margit"
    assert profile.favorite_game == "Elden Ring"
    assert "恶兆妖鬼 Margit死亡循环" in profile.repeated_struggles
    assert profile.emotional_notes[-1] == "death_loop"
    assert memory.recent_episodes()[0]["boss"] == "恶兆妖鬼 Margit"


def test_memory_updates_current_boss_from_margit_struggle(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")

    memory.extract_and_update(
        "我打不过 Margit",
        "先停一下，少打一刀。",
        "elden_ring_boss_strategy",
        datetime.now(timezone.utc),
    )

    assert memory.load_profile().current_boss == "恶兆妖鬼 Margit"
    assert memory.recent_episodes()[0]["boss"] == "恶兆妖鬼 Margit"


def test_memory_records_frustration(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")

    memory.extract_and_update(
        "我有点烦了",
        "先停一下吧。",
        "casual_chat",
        datetime.now(timezone.utc),
    )

    assert memory.load_profile().emotional_notes[-1] == "frustrated"


def test_memory_tracks_tone_preference(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")

    memory.extract_and_update(
        "以后可以吐槽我一点",
        "那你别又贪刀",
        "casual_chat",
        datetime.now(timezone.utc),
    )

    profile = memory.load_profile()
    assert profile.preferred_tone == "轻微吐槽"
    assert profile.likes_teasing is True


def test_memory_tracks_teasing_preference_inside_affection(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")

    memory.extract_and_update(
        "我喜欢你稍微吐槽我一点",
        "知道了。",
        "casual_chat",
        datetime.now(timezone.utc),
    )

    profile = memory.load_profile()
    assert profile.preferred_tone == "轻微吐槽"
    assert profile.likes_teasing is True
    assert "affection" in profile.emotional_notes


def test_memory_retriever_builds_prompt_context(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")
    now = datetime.now(timezone.utc)
    memory.extract_and_update("Margit 又死了", "还是 Margit……你又急了", "casual_chat", now)
    memory.extract_and_update("可以毒舌一点", "可以。但别后悔", "casual_chat", now)

    context = memory.build_prompt_context_with_provenance()
    text = context.as_prompt_text()

    assert len(context.lines) <= 3
    assert "玩家当前卡点：恶兆妖鬼 Margit" in text
    assert "玩家喜欢 Rei 用轻微吐槽的方式回应" in text
    assert "最近情绪：death_loop" in text
    assert {line.source for line in context.lines} <= {"profile", "episode"}


def test_memory_retriever_does_not_invent_history(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")

    context = memory.build_prompt_context_with_provenance()

    assert context.lines == []
    assert "上次" not in context.as_prompt_text()
    assert "之前" not in context.as_prompt_text()


def test_newer_boss_memory_overrides_old_boss(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")
    old = datetime.now(timezone.utc) - timedelta(days=3)
    now = datetime.now(timezone.utc)

    memory.extract_and_update("我打不过大树守卫", "先活下来。", "elden_ring_boss_strategy", old)
    memory.extract_and_update("今天卡在拉塔恩了", "别急。", "elden_ring_boss_strategy", now)

    context = memory.build_prompt_context_with_provenance(now=now)
    text = context.as_prompt_text()

    assert memory.load_profile().current_boss == "拉塔恩"
    assert "玩家当前卡点：拉塔恩" in text
    assert "Tree Sentinel" not in text


def test_stale_boss_memory_is_not_injected_without_fresh_evidence(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")
    old = datetime.now(timezone.utc) - timedelta(days=3)
    now = datetime.now(timezone.utc)

    memory.extract_and_update("我打不过大树守卫", "先活下来。", "elden_ring_boss_strategy", old)

    context = memory.build_prompt_context_with_provenance(now=now)

    assert "Tree Sentinel" not in context.as_prompt_text()
    assert all(line.field != "current_boss" for line in context.lines)


def test_stale_emotion_memory_is_not_injected(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")
    old = datetime.now(timezone.utc) - timedelta(days=2)
    now = datetime.now(timezone.utc)

    memory.extract_and_update("我有点烦了", "先停一下吧。", "casual_chat", old)

    context = memory.build_prompt_context_with_provenance(now=now)
    state = memory.active_memory_state(now=now)

    assert "frustrated" not in context.as_prompt_text()
    assert state["emotional_note"] is None


def test_memory_with_only_emotion_does_not_guess_boss(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")

    memory.extract_and_update("我有点烦了", "先停一下。", "casual_chat", datetime.now(timezone.utc))

    context = memory.build_prompt_context_with_provenance()
    text = context.as_prompt_text()
    assert "玩家当前卡点" not in text
    assert "大树守卫" not in text
    assert "恶兆妖鬼" not in text
    assert "拉塔恩" not in text
    assert "根据记忆" not in text


def test_negated_boss_message_does_not_update_current_boss(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")

    memory.extract_and_update("我打不过大树守卫", "先活下来。", "elden_ring_boss_strategy", datetime.now(timezone.utc))
    memory.extract_and_update("不是大树守卫", "那我不猜。", "casual_chat", datetime.now(timezone.utc))

    profile = memory.load_profile()
    context = memory.build_prompt_context_with_provenance()
    assert profile.current_boss is None
    assert "玩家当前卡点：大树守卫" not in context.as_prompt_text()


def test_later_negation_hides_older_boss_episode(tmp_path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")
    now = datetime.now(timezone.utc)

    memory.extract_and_update("我打不过 Margit", "先活下来。", "elden_ring_boss_strategy", now)
    memory.extract_and_update("我说的不是 Margit", "知道了。", "casual_chat", now + timedelta(minutes=1))

    context = memory.build_prompt_context_with_provenance(now=now + timedelta(minutes=2))
    assert "玩家当前卡点：恶兆妖鬼 Margit" not in context.as_prompt_text()


def test_negated_old_episode_does_not_pollute_active_current_boss(tmp_path):
    profile_path = tmp_path / "profile.json"
    episodes_path = tmp_path / "episodes.jsonl"
    timestamp = datetime.now(timezone.utc).isoformat()
    profile_path.write_text(
        json.dumps(
            {
                "current_boss": "Tree Sentinel",
                "repeated_struggles": [],
                "emotional_notes": [],
                "memory_updated_at": {"current_boss": timestamp},
            }
        ),
        encoding="utf-8",
    )
    episodes_path.write_text(
        json.dumps(
            {
                "timestamp": timestamp,
                "intent": "casual_chat",
                "boss": "Tree Sentinel",
                "user_message_sample": "不是大树守卫哦",
                "assistant_reply_sample": "知道了。",
                "summary": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    memory = PlayerMemory(profile_path, episodes_path)
    assert memory.active_memory_state()["current_boss"] is None
    assert "玩家当前卡点" not in memory.build_prompt_context_with_provenance().as_prompt_text()


def test_loaded_legacy_english_boss_memory_is_normalized(tmp_path):
    profile_path = tmp_path / "profile.json"
    episodes_path = tmp_path / "episodes.jsonl"
    profile_path.write_text(
        '{"current_boss":"Tree Sentinel","repeated_struggles":["Tree Sentinel死亡循环"],"emotional_notes":[]}',
        encoding="utf-8",
    )
    episodes_path.write_text("", encoding="utf-8")

    profile = PlayerMemory(profile_path, episodes_path).load_profile()

    assert profile.current_boss == "大树守卫"
    assert profile.repeated_struggles == ["大树守卫死亡循环"]


def test_memory_persists_after_new_instance(tmp_path):
    profile_path = tmp_path / "profile.json"
    episodes_path = tmp_path / "episodes.jsonl"
    memory = PlayerMemory(profile_path, episodes_path)
    memory.extract_and_update(
        "我打不过 Margit",
        "别急，少打一刀。",
        "elden_ring_boss_strategy",
        datetime.now(timezone.utc),
    )

    restored = PlayerMemory(profile_path, episodes_path)

    assert restored.load_profile().current_boss == "恶兆妖鬼 Margit"
    assert restored.recent_episodes()[0]["boss"] == "恶兆妖鬼 Margit"
