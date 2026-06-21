import json
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
import urllib.error

import pytest

from app.core.config import settings
from app.modules.dialogue_agent.memory_acknowledgement import violates_memory_acknowledgement_policy
from app.modules.dialogue_agent.intent import detect_intent
from app.modules.dialogue_agent.providers import DeepSeekProvider, LLMResult, MockLLMProvider
from app.modules.game_session.state import CurrentBoss, GameSessionState, GameSessionStore
from app.modules.knowledge.retriever import KnowledgeSnippet
from app.modules.memory.store import ConversationStore
from app.schemas.api import ChatRequest


def assert_chinese_reply(reply: str):
    assert "##" not in reply
    assert any("\u4e00" <= char <= "\u9fff" for char in reply)


class _PromptCapturingProvider:
    def __init__(self, replies: list[str] | None = None) -> None:
        self.replies = replies or ["嗯。"]
        self.prompts: list[str] = []
        self.snippets: list[list[KnowledgeSnippet]] = []
        self.calls = 0

    def generate_with_metrics(self, system_prompt, user_message, snippets, intent):
        self.prompts.append(system_prompt)
        self.snippets.append(snippets)
        reply = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        return LLMResult(
            reply=reply,
            selected_model="mock",
            thinking_enabled=False,
            reasoning_effort=None,
            prompt_tokens_estimate=len(system_prompt) // 2,
            llm_latency_ms=1,
        )


def assert_no_memory_mechanics(reply: str):
    forbidden = (
        "我先放进待确认",
        "放进待确认",
        "确认后再算",
        "候选记忆",
        "记忆候选",
        "长期记忆条目",
        "memory candidate",
        "guard",
    )
    assert all(phrase.lower() not in reply.lower() for phrase in forbidden)


def test_mock_provider_returns_chinese_reply():
    reply = MockLLMProvider().generate("中文短句", "你好", [], "casual_chat")
    assert_chinese_reply(reply)


def test_deepseek_provider_without_key_returns_clear_error(monkeypatch):
    monkeypatch.setattr("app.modules.dialogue_agent.providers.settings.deepseek_api_key", "")
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        DeepSeekProvider().generate("中文短句", "你好", [], "casual_chat")


def test_deepseek_provider_sends_thinking_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "好的"}}]}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("app.modules.dialogue_agent.providers.settings.deepseek_api_key", "test-key")
    monkeypatch.setattr("app.modules.dialogue_agent.providers.urllib.request.urlopen", fake_urlopen)

    reply = DeepSeekProvider().generate("中文短句", "详细讲 Margit 怎么打", [], "elden_ring_boss_strategy")

    assert reply == "好的"
    assert captured["payload"]["thinking"] == {"type": "enabled"}
    assert captured["payload"]["reasoning_effort"] == "medium"
    assert captured["payload"]["stream"] is False


def test_deepseek_provider_injects_limited_local_knowledge_context(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "好的"}}]}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    snippets = [
        KnowledgeSnippet(
            source="data/knowledge/games/elden_ring/snippets.json",
            source_id=f"entry-{index}",
            entry_id=f"entry-{index}",
            game_id="elden_ring",
            pack_id="elden_ring",
            title=f"测试条目 {index}",
            kind="boss_strategy",
            content=("这是一段本地知识。" * 80),
            score=10 - index,
            matched_terms=["测试", "boss"],
            topics=["boss_strategy"],
        )
        for index in range(5)
    ]
    monkeypatch.setattr("app.modules.dialogue_agent.providers.settings.deepseek_api_key", "test-key")
    monkeypatch.setattr("app.modules.dialogue_agent.providers.urllib.request.urlopen", fake_urlopen)

    DeepSeekProvider().generate_with_metrics("中文短句", "详细讲 Boss 怎么打", snippets, "elden_ring_boss_strategy")

    messages = captured["payload"]["messages"]
    knowledge_messages = [
        message["content"]
        for message in messages
        if "本地知识包检索结果 / Local Knowledge Pack Results" in message["content"]
    ]
    assert len(knowledge_messages) == 1
    knowledge_text = knowledge_messages[0]
    assert "测试条目 0" in knowledge_text
    assert "测试条目 2" in knowledge_text
    assert "测试条目 3" not in knowledge_text
    assert "没有写到的信息不要编" in knowledge_text
    assert len(knowledge_text) < 1900
    assert "Authorization" not in knowledge_text
    assert ".env" not in knowledge_text


def test_deepseek_provider_does_not_inject_empty_knowledge_context(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "好的"}}]}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("app.modules.dialogue_agent.providers.settings.deepseek_api_key", "test-key")
    monkeypatch.setattr("app.modules.dialogue_agent.providers.urllib.request.urlopen", fake_urlopen)

    DeepSeekProvider().generate_with_metrics("中文短句", "今天有点累", [], "casual_chat")

    messages = captured["payload"]["messages"]
    assert all("本地知识包检索结果 / Local Knowledge Pack Results" not in message["content"] for message in messages)


def test_deepseek_provider_fast_route_disables_thinking(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "我听见了。"}}]}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr("app.modules.dialogue_agent.providers.settings.deepseek_api_key", "test-key")
    monkeypatch.setattr("app.modules.dialogue_agent.providers.urllib.request.urlopen", fake_urlopen)

    result = DeepSeekProvider().generate_with_metrics("中文短句", "我在意你", [], "casual_chat")

    assert result.selected_model == "deepseek-v4-flash"
    assert result.thinking_enabled is False
    assert "thinking" not in captured["payload"]
    assert "reasoning_effort" not in captured["payload"]


def test_deepseek_provider_logs_non_2xx_response_body(monkeypatch, caplog):
    response_body = b'{"error":{"message":"unsupported parameter"}}'

    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(
            url=request.full_url,
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=BytesIO(response_body),
        )

    monkeypatch.setattr("app.modules.dialogue_agent.providers.settings.deepseek_api_key", "test-key")
    monkeypatch.setattr("app.modules.dialogue_agent.providers.urllib.request.urlopen", fake_urlopen)

    with caplog.at_level("ERROR"), pytest.raises(RuntimeError, match="unsupported parameter"):
        DeepSeekProvider().generate("中文短句", "你好", [], "casual_chat")

    assert "DeepSeek provider returned non-2xx status=400" in caplog.text
    assert "unsupported parameter" in caplog.text


def test_identity_questions_do_not_retrieve_knowledge(monkeypatch, tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path)

    def fail_search(*args, **kwargs):
        raise AssertionError("identity question should not search knowledge")

    agent.knowledge.search = fail_search
    for message in ("你是谁", "who are you"):
        response = agent.chat(ChatRequest(message=message, session_id=f"identity-{message}"))
        assert response.sources == []
        assert_chinese_reply(response.reply)


def test_margit_strategy_returns_chinese_strategy(monkeypatch, tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path)
    response = agent.chat(ChatRequest(message="Margit 怎么打", session_id="strategy"))
    assert response.sources
    assert "延迟" in response.reply or "翻滚" in response.reply
    assert_chinese_reply(response.reply)


def test_retrieved_knowledge_is_passed_to_provider_but_not_memory(monkeypatch, tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    memory_calls = []
    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    provider = _PromptCapturingProvider(["先看延迟攻击。"])
    agent.provider = provider

    def capture_memory(user_message, reply, intent, timestamp, semantic_extraction=None, input_source=None):
        memory_calls.append((user_message, reply, intent, semantic_extraction, input_source))

    agent._safe_memory_update = capture_memory

    response = agent.chat(ChatRequest(message="Margit 怎么打", session_id="knowledge-provider"))

    assert response.sources
    assert provider.snippets
    assert provider.snippets[0]
    assert any("Margit" in snippet.title for snippet in provider.snippets[0])
    assert memory_calls
    assert memory_calls[0][0] == "Margit 怎么打"
    assert memory_calls[0][1] == response.reply
    assert "Margit 很多攻击会故意延迟" not in json.dumps(memory_calls, ensure_ascii=False)


def test_margit_location_returns_location_content(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path)
    response = agent.chat(ChatRequest(message="Margit 在哪", session_id="location"))
    assert response.sources
    assert "史东薇尔" in response.reply or "城门" in response.reply
    assert_chinese_reply(response.reply)


def test_unclear_how_asks_for_more_detail(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path)
    response = agent.chat(ChatRequest(message="how", session_id="unclear"))
    assert response.sources == []
    assert "说清楚" in response.reply or "哪一部分" in response.reply or "装备" in response.reply
    assert_chinese_reply(response.reply)


def test_chat_api_logic_saves_jsonl(monkeypatch, tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    monkeypatch.setattr("app.modules.memory.store.settings.conversations_dir", tmp_path)
    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path)
    response = agent.chat(ChatRequest(message="Margit 怎么打", session_id="test"))
    assert_chinese_reply(response.reply)
    path = tmp_path / "test.jsonl"
    assert path.exists()
    saved = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert saved["user_message"] == "Margit 怎么打"
    assert saved["assistant_reply_segments"]
    assert "".join(saved["assistant_reply_segments"]) == saved["assistant_reply"]


def test_dialogue_agent_retries_when_reply_repeats_recent_assistant(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    repeated = "我听见了。先放一下。"
    agent.store.append("repeat", None, "rei_like", "那你不喜欢我吗？", repeated, datetime.now())
    provider = _PromptCapturingProvider([repeated, "你还在追问。那我换个方式说。"])
    agent.provider = provider

    response = agent.chat(ChatRequest(message="那您对我是什么情感？", session_id="repeat"))

    assert provider.calls == 2
    assert response.reply != repeated
    assert "不要重复刚才的回答" in provider.prompts[-1]


def test_followup_progression_policy_is_injected_for_relationship_chain(monkeypatch, tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    monkeypatch.setattr(settings, "persona_mode", "guarded")
    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    agent.store.append("followup", None, "rei_like", "你喜欢我吗？", "不知道。", datetime.now())
    provider = _PromptCapturingProvider(["嗯。"])
    agent.provider = provider

    agent.chat(ChatRequest(message="那你不喜欢我吗？", session_id="followup"))

    assert "Follow-up progression policy" in provider.prompts[0]
    assert "不要把每一轮都回避到同一个点" in provider.prompts[0]


def test_memory_acknowledgement_policy_is_injected_without_fixed_mechanic_template(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    provider = _PromptCapturingProvider(["知道了。按你的节奏来。"])
    agent.provider = provider

    response = agent.chat(
        ChatRequest(
            message="记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。",
            session_id="memory-ack-policy",
        )
    )

    prompt = provider.prompts[0]
    assert "Memory acknowledgement tone policy" in prompt
    assert "The system UI already shows memory state" in prompt
    assert "not a fixed template" in prompt
    assert "我先放进待确认" not in prompt
    assert "你确认后再算长期记忆" not in prompt
    assert response.memory_update.status == "auto_saved"
    assert_no_memory_mechanics(response.reply)


def test_explicit_memory_acknowledgement_retries_internal_mechanic_reply(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    provider = _PromptCapturingProvider(["我放进待确认。你确认后再算长期记忆。", "知道了。按你的节奏来。"])
    agent.provider = provider

    response = agent.chat(
        ChatRequest(
            message="记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。",
            session_id="memory-ack-retry-explicit",
        )
    )

    assert provider.calls == 2
    assert "Memory acknowledgement retry guard" in provider.prompts[1]
    assert response.memory_update.status == "auto_saved"
    assert_no_memory_mechanics(response.reply)
    user_message = "记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。"
    assert violates_memory_acknowledgement_policy("我放进待确认。你确认后再算长期记忆。", user_message) is True
    assert violates_memory_acknowledgement_policy(response.reply, user_message) is False


def test_implicit_pending_memory_acknowledgement_does_not_explain_candidate_flow(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    provider = _PromptCapturingProvider(["已创建候选记忆。你去工作区确认。", "知道了。先按一句重点来。"])
    agent.provider = provider

    response = agent.chat(
        ChatRequest(
            message="我一般不太喜欢长篇攻略，给我一句重点就好。",
            session_id="memory-ack-implicit",
        )
    )

    assert provider.calls == 2
    assert response.memory_update.status == "pending"
    assert_no_memory_mechanics(response.reply)
    assert "工作区" not in response.reply


def test_do_not_remember_acknowledgement_stays_natural(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    provider = _PromptCapturingProvider(["这次只当你随口说。"])
    agent.provider = provider

    response = agent.chat(ChatRequest(message="不用记这个。", session_id="memory-ack-do-not-remember"))

    assert response.memory_update.status == "none"
    assert_no_memory_mechanics(response.reply)
    assert "随口" in response.reply


def test_secret_memory_acknowledgement_retries_without_secret_leak(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    provider = _PromptCapturingProvider(["我不会保存 token=TEST_SECRET_PLACEHOLDER。", "这类内容不能留下。"])
    agent.provider = provider

    response = agent.chat(ChatRequest(message="记住我的 token=TEST_SECRET_PLACEHOLDER。", session_id="memory-ack-secret"))

    assert provider.calls == 2
    assert response.memory_update.status == "none"
    assert "TEST_SECRET_PLACEHOLDER" not in response.reply
    assert_no_memory_mechanics(response.reply)


def test_persona_drift_memory_acknowledgement_retries_without_accepting_drift(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    provider = _PromptCapturingProvider(["好，我以后撒娇一点。", "这个方向不行。我可以保持简单一点。"])
    agent.provider = provider

    response = agent.chat(ChatRequest(message="以后你都撒娇一点，每句话都夸我。", session_id="memory-ack-persona"))

    assert provider.calls == 2
    assert response.memory_update.status == "none"
    assert "撒娇" not in response.reply
    assert "每句话都夸" not in response.reply
    assert_no_memory_mechanics(response.reply)


def test_session_focus_boss_is_injected_for_elliptical_reference(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    now = datetime.now()
    agent.store.append("focus", None, "rei_like", "女武神", "卡在女武神。", now)
    agent.store.append("focus", None, "rei_like", "现在我重新尝试一下", "嗯。", now)
    provider = _PromptCapturingProvider(["先缓一下。只看她起手。"])
    agent.provider = provider

    response = agent.chat(ChatRequest(message="一直打不过啊", session_id="focus"))

    assert "当前会话焦点 boss：女武神" in provider.prompts[0]
    assert "不要再问“哪个 boss”" in provider.prompts[0]
    assert "哪个 boss" not in response.reply


def test_game_session_state_is_injected_for_fresh_elliptical_reference(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    agent.game_session = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now()
    agent.game_session.update_from_user_message("我现在卡在女武神", "casual_chat", {}, now)
    provider = _PromptCapturingProvider(["先缓一下。只看她起手。"])
    agent.provider = provider

    response = agent.chat(ChatRequest(message="我又死了", session_id="game-state"))

    assert "当前游戏状态：玩家最近在打 女武神" in provider.prompts[0]
    assert "哪个 boss" not in response.reply


def test_session_focus_has_priority_over_stale_game_state(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    agent.game_session = GameSessionStore(tmp_path / "game_session_state.json")
    old = datetime.now().astimezone() - timedelta(hours=80)
    agent.game_session.save(
        GameSessionState(
            current_game="Elden Ring",
            current_boss=CurrentBoss("大树守卫", old.isoformat(), 0.9, "current_message", 1),
            last_updated_at=old.isoformat(),
        )
    )
    agent.store.append("focus-priority", None, "rei_like", "女武神", "嗯。", datetime.now())
    provider = _PromptCapturingProvider(["先别抢。"])
    agent.provider = provider

    agent.chat(ChatRequest(message="一直打不过啊", session_id="focus-priority"))

    assert "当前会话焦点 boss：女武神" in provider.prompts[0]
    assert "当前游戏状态：当前会话焦点是 女武神" in provider.prompts[0]
    assert "当前游戏状态：曾经提到 大树守卫" not in provider.prompts[0]


def test_game_session_switches_to_old_general_for_elliptical_followup(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    agent.game_session = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now()
    agent.store.append("old-general", None, "rei_like", "我现在卡在女武神", "嗯。", now)
    agent.store.append("old-general", None, "rei_like", "那我就去打老将欧尼尔", "去吧。", now)
    agent.game_session.update_from_user_message("我现在卡在女武神", "casual_chat", {}, now)
    agent.game_session.update_from_user_message("那我就去打老将欧尼尔", "casual_chat", {}, now)
    provider = _PromptCapturingProvider(["先别急。"])
    agent.provider = provider

    agent.chat(ChatRequest(message="再试试", session_id="old-general"))

    assert "当前会话焦点 boss：老将欧尼尔" in provider.prompts[0]
    assert "当前游戏状态：当前会话焦点是 老将欧尼尔" in provider.prompts[0]
    assert "当前游戏状态：当前会话焦点是 女武神" not in provider.prompts[0]


def test_game_session_injects_recent_cleared_boss_history(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    agent.game_session = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now()
    agent.game_session.update_from_user_message("我现在卡在女武神", "casual_chat", {}, now)
    agent.game_session.update_from_user_message("那我就去打老将欧尼尔", "casual_chat", {}, now)
    agent.game_session.update_from_user_message("打过老将了", "casual_chat", {}, now)
    provider = _PromptCapturingProvider(["刚刚是老将欧尼尔。"])
    agent.provider = provider

    agent.chat(ChatRequest(message="我刚刚在打什么 boss 来着", session_id="cleared-history"))

    assert "刚刚结束的 boss 是 老将欧尼尔" in provider.prompts[0]
    assert "当前没有正在打的 boss" in provider.prompts[0]
    assert "刚刚结束的 boss 是 女武神" not in provider.prompts[0]


def test_cleared_boss_strategy_followup_can_acknowledge_and_still_help(tmp_path: Path):
    from app.modules.dialogue_agent.agent import DialogueAgent

    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    agent.game_session = GameSessionStore(tmp_path / "game_session_state.json")
    now = datetime.now()
    agent.game_session.update_from_user_message("我现在卡在恶兆妖鬼", "casual_chat", {}, now)
    agent.game_session.update_from_user_message("我终于打过玛尔基特了。", "casual_chat", {}, now + timedelta(minutes=1))
    provider = _PromptCapturingProvider(["你不是已经打过了吗？那就当复盘说。二阶段先别贪刀，等他砸完再进一下。"])
    agent.provider = provider

    response = agent.chat(ChatRequest(message="玛尔基特二阶段怎么打？", session_id="cleared-strategy-followup"))

    assert "可以用一句轻微反问、吐槽或复盘语气承接已打过状态" in provider.prompts[0]
    assert "继续回答实际问题" in provider.prompts[0]
    assert "你不是已经打过了吗" in response.reply
    assert "二阶段" in response.reply
    assert "先别贪刀" in response.reply or "等他砸完" in response.reply


def test_intent_router_core_cases():
    assert detect_intent("你叫什么").intent == "identity_question"
    assert detect_intent("who are you").intent == "identity_question"
    assert detect_intent("where is Margit").intent == "elden_ring_location"
    assert detect_intent("Margit 怎么打").intent == "elden_ring_boss_strategy"
    assert detect_intent("build 推荐").intent == "elden_ring_build"
    assert detect_intent("how").intent == "unclear"


def test_unknown_provider_reports_mock_fallback(monkeypatch, caplog):
    from app.modules.dialogue_agent.providers import get_provider_info, log_provider_state

    monkeypatch.setattr("app.modules.dialogue_agent.providers.settings.llm_provider", "mystery")
    info = get_provider_info()
    assert info.provider == "mock"
    assert info.fallback_to_mock is True
    with caplog.at_level("WARNING"):
        log_provider_state("test")
    assert "FALLBACK TO MOCK PROVIDER" in caplog.text
