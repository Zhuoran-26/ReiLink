from app.modules.dialogue_agent.emotion import build_companion_policy, detect_user_emotion
from pathlib import Path

from app.modules.dialogue_agent.repetition import (
    build_followup_progression_policy,
    build_repetition_guard,
    has_exact_duplicate,
    has_high_frequency_repetition,
    is_repetitive_reply,
)
from app.modules.dialogue_agent.session_focus import resolve_session_focus
from app.modules.dialogue_agent.validator import validate_or_repair
from app.modules.persona_engine.engine import PersonaEngine

POETIC_PHRASES = (
    "屏幕的光藏不住",
    "夜色",
    "孤独的旅途",
    "像……一样",
    "旅途还在",
    "风景还在",
)

COUNSELOR_PHRASES = (
    "喜欢的定义",
    "因人而异",
    "作为一个陪伴者",
    "我会尽力理解你",
    "你的感受是合理的",
    "我希望我的陪伴",
)


def test_prompt_contains_anti_poetic_and_anti_counselor_boundaries():
    prompt = PersonaEngine().build_prompt("rei_like", {})

    for phrase in POETIC_PHRASES + COUNSELOR_PHRASES:
        assert phrase in prompt
    assert "不要写诗意旁白" in prompt
    assert "不要反复复用" in prompt
    assert "不要猜具体 boss" in prompt


def test_validator_rejects_poetic_ai_copy():
    reply = "凌晨的游戏容易让人忘记时间，不过屏幕的光藏不住你的倦意。该停了。"

    repaired = validate_or_repair(reply, "casual_chat")

    assert "屏幕的光藏不住" not in repaired
    assert repaired != reply


def test_validator_rejects_ai_counselor_copy():
    reply = "喜欢的定义因人而异。你的感受是合理的。作为一个陪伴者，我会尽力理解你。"

    repaired = validate_or_repair(reply, "casual_chat")

    assert not any(phrase in repaired for phrase in COUNSELOR_PHRASES)
    assert repaired != reply


def test_validator_preserves_natural_newline_segments():
    reply = "你问得太急了。\n先慢一点。"

    cleaned = validate_or_repair(reply, "casual_chat")

    assert cleaned == reply


def test_repetition_guard_warns_on_recent_core_phrase_reuse():
    replies = [
        "我在这里。想说的时候就说。",
        "我听见了。",
        "别想太多。",
        "习惯你在。",
        "看着你。",
    ]

    guard = build_repetition_guard(replies)

    assert "不要继续复用" in guard
    assert "我在这里" in guard
    assert "我听见了" in guard
    assert has_high_frequency_repetition(["我在这里。", "我在这里。"]) is True


def test_repetition_guard_detects_exact_duplicate_and_semantic_similarity():
    replies = [
        "你问得这么认真，我有点不知道该怎么接。但我没有走开过。",
        "你问得这么认真，我有点不知道该怎么接。但我没有走开过。",
    ]
    guard = build_repetition_guard(replies)

    assert has_exact_duplicate(replies) is True
    assert "不要重复刚才的回答" in guard
    assert "用户是在追问，需要推进关系，而不是复述" in guard
    assert is_repetitive_reply("你问得这么认真，我不知道怎么接。但我没有走开。", replies) is True


def test_followup_progression_policy_is_not_a_fixed_reply_template():
    policy = build_followup_progression_policy("那你对我是什么情感？", ["你喜欢我吗", "那你不喜欢我吗？"])

    assert "连续追问关系或情感" in policy
    assert "不要复述刚才回答" in policy
    assert "这些只是方向，不是固定台词" in policy
    assert "但我没有走" not in policy
    assert "这样已经够近了" not in policy


def test_repetition_guard_is_injected_into_prompt():
    guard = build_repetition_guard(["我在这里。", "别想太多。"])

    prompt = PersonaEngine().build_prompt("rei_like", {}, repetition_guard=guard)

    assert guard in prompt


def test_memory_correction_policy_says_do_not_guess():
    policy = build_companion_policy("不是大树守卫，也不是恶兆妖鬼", "casual_chat")

    assert "不要继续猜" in policy
    assert "不知道就简短承认不知道" in policy


def test_relationship_and_late_night_inputs_are_emotional_for_segmentation():
    assert detect_user_emotion("你是不是在关心我").detected is True
    assert detect_user_emotion("已经凌晨了").detected is True
    assert detect_user_emotion("你会不会觉得我烦").detected is True


def test_session_focus_resolves_elliptical_boss_reference():
    focus = resolve_session_focus("一直打不过啊", ["女武神", "现在我重新尝试一下"])

    assert focus.boss == "女武神"
    assert "不要再问“哪个 boss”" in focus.as_prompt_line()


def test_no_hardcoded_followup_dialogue_added():
    root = Path(__file__).resolve().parents[3]
    checked = [
        root / "services/backend/app/modules/dialogue_agent/agent.py",
        root / "services/backend/app/modules/dialogue_agent/repetition.py",
        root / "services/backend/app/modules/dialogue_agent/session_focus.py",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in checked)

    for fixed_reply in ("但我没有走。", "这样已经够近了。", "你真的想听答案"):
        assert fixed_reply not in combined
