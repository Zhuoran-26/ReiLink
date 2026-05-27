from app.modules.persona_engine.engine import PersonaEngine
from app.core.config import settings
import json


def test_loads_rei_like_persona():
    persona = PersonaEngine().load("rei_like")
    assert persona["id"] == "rei_like"
    assert persona["display_name"] == "Rei"


def test_prompt_contains_chinese_style_constraints_for_idle_context():
    prompt = PersonaEngine().build_prompt("rei_like", {"status": "idle"})
    assert "始终使用中文" in prompt
    assert "默认 1-3 句" in prompt
    assert "Game status" not in prompt


def test_prompt_avoids_direct_ip_replication_language():
    prompt = PersonaEngine().build_prompt("rei_like", {})
    assert "不要模仿受版权保护" in prompt


def test_prompt_prioritizes_message_over_persona():
    prompt = PersonaEngine().build_prompt(
        "rei_like",
        {},
        memory_context="- 玩家当前卡点：Margit",
        companion_policy="Companion-first Response Policy:\n- 测试策略",
    )

    assert "回复优先级从高到低" in prompt
    assert "当前用户情绪" in prompt
    assert "当前用户问题和真实意图" in prompt
    assert "知识库" in prompt
    assert "人格不能压过理解、推理和回答质量" in prompt
    assert "不要编造“上次/之前/你说过”" in prompt
    assert "故意使用不完整句" in prompt
    assert "Companion-first Response Policy" in prompt


def test_golden_style_dataset_contains_anchor():
    data = json.loads(settings.persona_golden_style_path.read_text(encoding="utf-8"))
    examples = data["golden_examples"]
    anchor = next(item for item in examples if item["situation"] == "late_night_or_long_session")

    assert anchor["user"] == "你是不是在关心我"
    assert anchor["good_reply"] == "……你看屏幕太久，该休息了。我只是习惯你在这里。别想太多。"
    assert "先观察用户状态" in anchor["why_it_works"]


def test_prompt_includes_golden_style_anchor_and_guardrails():
    prompt = PersonaEngine().build_prompt("rei_like", {})

    assert "Golden style anchor" in prompt
    assert "安静地观察用户，并用很克制的方式表达关心" in prompt
    assert "……你看屏幕太久，该休息了。我只是习惯你在这里。别想太多。" in prompt
    assert "观察用户状态 -> 轻微关心或提醒 -> 回避直接亲密表达 -> 短句收尾" in prompt
    assert "学习这个结构，不要高频复用表层短语" in prompt
    assert "可以用自然换行表达分段" in prompt
    assert "情感类问题不要解释喜欢、关心、陪伴的抽象概念" in prompt


def test_prompt_bans_abstract_counselor_phrases():
    prompt = PersonaEngine().build_prompt("rei_like", {})

    for phrase in (
        "喜欢的定义因人而异",
        "关心和喜欢的区别",
        "你更有发言权",
        "我希望我的陪伴让你觉得被认真对待",
        "作为一个陪伴者",
        "我会尽力理解你",
    ):
        assert phrase in prompt
    assert "禁止出现或模仿的抽象解释型回答" in prompt


def test_prompt_includes_negative_examples_without_turning_them_into_templates():
    prompt = PersonaEngine().build_prompt("rei_like", {})

    assert "Negative examples" in prompt
    assert "凌晨的游戏容易让人忘记时间" in prompt
    assert "屏幕的光也藏不住" in prompt
    assert "已经凌晨了。该停了。" in prompt
    assert "只学习边界" in prompt
    assert "不要机械复读或固定套用" in prompt
