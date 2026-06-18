from app.modules.persona_engine.engine import PersonaEngine
from app.modules.proactive.trigger import ProactiveCompanion
from app.modules.dialogue_agent import semantic_extraction as sem
from app.core.config import settings
import json


FORBIDDEN_EXTERNAL_IDENTITY_TERMS = (
    "Evangelion",
    "Rei Ayanami",
    "Ayanami",
    "绫波",
    "綾波",
    "NERV",
    "EVA",
    "永雏塔菲",
    "taffy-skill",
)


def test_loads_rei_like_persona():
    persona = PersonaEngine().load("rei_like")
    assert persona["id"] == "rei_like"
    assert persona["display_name"] == "Rei"


def test_prompt_contains_chinese_style_constraints_for_idle_context(monkeypatch):
    monkeypatch.setattr(settings, "persona_mode", "guarded")
    prompt = PersonaEngine().build_prompt("rei_like", {"status": "idle"})
    assert "始终使用中文" in prompt
    assert "默认 1-3 句" in prompt
    assert "Game status" not in prompt


def test_prompt_avoids_direct_ip_replication_language(monkeypatch):
    monkeypatch.setattr(settings, "persona_mode", "guarded")
    prompt = PersonaEngine().build_prompt("rei_like", {})
    assert "不要模仿受版权保护" in prompt


def test_prompt_prioritizes_message_over_persona(monkeypatch):
    monkeypatch.setattr(settings, "persona_mode", "guarded")
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


def test_prompt_includes_structured_rei_persona_pack(monkeypatch):
    monkeypatch.setattr(settings, "persona_mode", "guarded")
    prompt = PersonaEngine().build_prompt("rei_like", {})

    assert "基础系统安全 / 应用身份" in prompt
    assert "Rei Persona Pack v1.1.2" in prompt
    assert "[角色定位]" in prompt
    assert "[风格校准]" in prompt
    assert "[说话方式]" in prompt
    assert "[回复模式]" in prompt
    assert "[边界]" in prompt
    assert "[游戏陪伴策略]" in prompt
    assert "[记忆策略]" in prompt
    assert "[主动陪伴策略]" in prompt
    assert "[好例]" in prompt
    assert "[反例]" in prompt
    assert "不要逐字复读好例" in prompt
    assert "人格包不能覆盖系统安全" in prompt
    assert "待确认记忆流程" in prompt
    assert "影子识别候选边界" in prompt
    assert "冷静寡言" in prompt
    assert "话多程度：1/5" in prompt
    assert "表达通道很窄" in prompt
    assert "不是没有情绪" in prompt
    assert "不要把“也”“还”“嗯”之类变成新口癖" in prompt
    assert "低频使用“看见”“看着你”“坐在旁边”“我在这里”类表达" in prompt
    assert "不把每个问题都归结为“我在看你”" in prompt
    assert "不要把对话称为“接”" in prompt
    assert "关系类追问不应连续复用相同开头" in prompt
    assert "强意象或强落点，只能低频使用" in prompt
    assert "具体好句和意象只作方向参考，不是回复候选" in prompt
    assert "玩家死亡多次" in prompt
    assert "玩家追问关系或关心" in prompt
    assert "连续相似问题" in prompt
    assert "记忆状态由 UI 小字提示负责透明度" in prompt
    assert "自然承接或边界回应" in prompt
    assert "我先放进待确认" not in prompt
    assert "你确认后再算长期记忆" not in prompt
    assert "固定陪伴意象" in prompt
    assert "关系元语言" in prompt
    assert "重复强意象" in prompt
    assert "固定关系结构" in prompt
    assert "今天有点累" not in prompt
    assert "未确认记忆" not in prompt
    assert "/Users/" not in prompt
    assert "DEEPSEEK_API_KEY=" not in prompt
    assert ".env" not in prompt


def test_assembled_prompt_omits_forbidden_external_identity_terms(monkeypatch):
    monkeypatch.setattr(settings, "persona_mode", "guarded")
    prompt = PersonaEngine().build_prompt("rei_like", {})

    for term in FORBIDDEN_EXTERNAL_IDENTITY_TERMS:
        assert term.lower() not in prompt.lower()


def test_persona_prompt_build_does_not_mutate_proactive_state(monkeypatch):
    monkeypatch.setattr(settings, "persona_mode", "guarded")
    state_path = settings.proactive_state_path

    PersonaEngine().build_prompt("rei_like", {"status": "idle"})

    assert not state_path.exists()
    assert ProactiveCompanion().status(session_id="persona-pack-build")["last_triggered_type"] == "none"


def test_persona_prompt_build_does_not_schedule_semantic_shadow(monkeypatch):
    monkeypatch.setattr(settings, "persona_mode", "guarded")
    before = sem.get_semantic_shadow_events()["latest_id"]

    PersonaEngine().build_prompt("rei_like", {"status": "idle"})

    after = sem.get_semantic_shadow_events()["latest_id"]
    assert after == before


def test_minimal_prompt_includes_structured_pack_without_bypassing_mode(monkeypatch):
    monkeypatch.setattr(settings, "persona_mode", "minimal")
    prompt = PersonaEngine().build_prompt("rei_like", {"status": "idle"})

    assert "Rei Persona Pack v1.1.2" in prompt
    assert "人格模式：minimal" in prompt
    assert "人格包不能覆盖系统安全" in prompt
    assert "Companion-first Response Policy" not in prompt


def test_golden_style_dataset_contains_anchor():
    data = json.loads(settings.persona_golden_style_path.read_text(encoding="utf-8"))
    examples = data["golden_examples"]
    anchor = next(item for item in examples if item["situation"] == "late_night_or_long_session")

    assert anchor["user"] == "你是不是在关心我"
    assert anchor["good_reply"] == "……你看屏幕太久，该休息了。我只是习惯你在这里。别想太多。"
    assert "先观察用户状态" in anchor["why_it_works"]


def test_prompt_includes_golden_style_anchor_and_guardrails(monkeypatch):
    monkeypatch.setattr(settings, "persona_mode", "guarded")
    prompt = PersonaEngine().build_prompt("rei_like", {})

    assert "风格锚点" in prompt
    assert "安静地观察用户，并用很克制的方式表达关心" in prompt
    assert "……你看屏幕太久，该休息了。我只是习惯你在这里。别想太多。" in prompt
    assert "观察用户状态 -> 轻微关心或提醒 -> 回避直接亲密表达 -> 短句收尾" in prompt
    assert "学习这个结构，不要高频复用表层短语" in prompt
    assert "可以用自然换行表达分段" in prompt
    assert "情感类问题不要解释喜欢、关心、陪伴的抽象概念" in prompt


def test_prompt_bans_abstract_counselor_phrases(monkeypatch):
    monkeypatch.setattr(settings, "persona_mode", "guarded")
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


def test_prompt_includes_negative_examples_without_turning_them_into_templates(monkeypatch):
    monkeypatch.setattr(settings, "persona_mode", "guarded")
    prompt = PersonaEngine().build_prompt("rei_like", {})

    assert "反例，只学习边界" in prompt
    assert "凌晨的游戏容易让人忘记时间" in prompt
    assert "屏幕的光也藏不住" in prompt
    assert "已经凌晨了。该停了。" in prompt
    assert "只学习边界" in prompt
    assert "不要机械复读或固定套用" in prompt


def test_guarded_and_minimal_modes_can_generate_prompts(monkeypatch):
    monkeypatch.setattr(settings, "persona_mode", "guarded")
    guarded_prompt = PersonaEngine().build_prompt("rei_like", {})

    monkeypatch.setattr(settings, "persona_mode", "minimal")
    minimal_prompt = PersonaEngine().build_prompt(
        "rei_like",
        {"status": "idle"},
        intent="affection",
        memory_context="- 玩家当前卡点：女武神",
        session_context="- 当前会话焦点 boss：女武神",
        companion_policy="Companion-first Response Policy:\n- 测试策略",
    )

    assert "风格锚点" in guarded_prompt
    assert "人格模式：minimal" in minimal_prompt
    assert "安静、克制、低情绪波动" in minimal_prompt
    assert "括号里的动作或神态少用" in minimal_prompt
    assert "不要把自己介绍成 ReiLink" in minimal_prompt
    assert "没有明确证据时，说记不清、忘了，或者追问" in minimal_prompt
    assert "吧" in minimal_prompt
    assert "已验证长期记忆" in minimal_prompt
    assert "当前会话上下文" in minimal_prompt
    assert "ReiLink 的中文陪伴者" not in minimal_prompt
    assert "风格参考，不是固定回复" not in minimal_prompt
    assert "Companion-first Response Policy" not in minimal_prompt
