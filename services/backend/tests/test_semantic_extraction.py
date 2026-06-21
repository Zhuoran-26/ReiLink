import json
import inspect
import socket
import urllib.error

import pytest

from app.modules.dialogue_agent import semantic_extraction as sem


def _shadow_payload(
    *,
    game="unknown",
    boss="unknown",
    boss_label=None,
    death_operation="none",
    death_value=None,
    frustration="none",
    cleared="none",
    confidence="medium",
    memory=False,
    proactive="none",
    reasoning="候选摘要",
) -> dict:
    return {
        "is_game_related": True,
        "confidence": confidence,
        "game": {"operation": "set" if game != "unknown" else "unknown", "value": game, "confidence": confidence},
        "boss": {
            "operation": "set" if boss != "unknown" else "unknown",
            "value": boss,
            "surface_label": boss_label,
            "confidence": confidence,
        },
        "death_count": {"operation": death_operation, "value": death_value, "confidence": confidence},
        "frustration": {"operation": frustration, "confidence": confidence},
        "boss_cleared": {"operation": cleared, "confidence": confidence},
        "memory_candidate": {
            "should_create": memory,
            "kind": "progress" if memory else "none",
            "safe_summary": "玩家游戏进度候选" if memory else None,
            "confidence": confidence,
        },
        "proactive_signal": {"type": proactive, "confidence": confidence, "reason": "安全短原因" if proactive != "none" else ""},
        "reasoning_summary": reasoning,
    }


class _FakeResponse:
    def __init__(self, content: str | None = None):
        self.content = content or json.dumps(
            _shadow_payload(boss="margit", death_operation="increment", death_value=1, frustration="raise"),
            ensure_ascii=False,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(
            {
                "choices": [
                    {
                        "message": {"content": self.content}
                    }
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8")


def _game_state(current_boss: str | None = None) -> dict:
    return {
        "current_game": "Elden Ring",
        "current_boss": {"name": current_boss} if current_boss else None,
        "last_failed_boss": current_boss,
        "last_attempted_boss": current_boss,
        "last_cleared_boss": None,
        "boss_history": [],
    }


def _shadow_events_since(since_id: int) -> list[dict]:
    return sem.get_semantic_shadow_events(since_id=since_id)["events"]


def _primary_payload(
    *,
    game="elden_ring",
    boss="unknown",
    boss_switched=False,
    mentioned=None,
    negated=None,
    previous=None,
    new_current=None,
    guide_only=None,
    current_target=None,
    candidate_boss=None,
    candidate_event="none",
    candidate_confidence=None,
    candidate_reason="",
    needs_confirmation=False,
    guide_entity=None,
    confirmation_intent="unknown",
    death_operation="none",
    death_value=None,
    frustration="none",
    cleared="none",
    confidence="high",
    guide=False,
    strategy=False,
    memory=False,
    proactive="none",
    reasoning="安全候选摘要",
) -> dict:
    payload = _shadow_payload(
        game=game,
        boss=boss,
        death_operation=death_operation,
        death_value=death_value,
        frustration=frustration,
        cleared=cleared,
        confidence=confidence,
        memory=memory,
        proactive=proactive,
        reasoning=reasoning,
    )
    payload["guide_request"] = {"value": guide, "confidence": confidence if guide else "low"}
    payload["strategy_request"] = {"value": strategy, "confidence": confidence if strategy else "low"}
    payload["boss_switched"] = {"value": boss_switched, "confidence": confidence if boss_switched else "low"}
    payload["mentioned_entity"] = _primary_entity(mentioned, confidence)
    payload["negated_entity"] = _primary_entity(negated, confidence)
    payload["previous_target"] = _primary_entity(previous, confidence)
    payload["new_current_target"] = _primary_entity(new_current, confidence)
    payload["guide_only_entity"] = _primary_entity(guide_only, confidence)
    payload["current_target_candidate"] = _primary_entity(current_target, confidence)
    payload["candidate_boss"] = _primary_entity(candidate_boss, candidate_confidence or confidence)
    payload["candidate_event"] = candidate_event
    payload["candidate_confidence"] = candidate_confidence or confidence
    payload["candidate_reason"] = candidate_reason
    payload["needs_confirmation"] = needs_confirmation
    payload["guide_entity"] = _primary_entity(guide_entity, candidate_confidence or confidence)
    payload["confirmation_intent"] = confirmation_intent
    return payload


def _primary_entity(value: str | None, confidence: str) -> dict:
    return {"value": value, "surface_label": None, "confidence": confidence if value else "low"}


def _mock_primary(monkeypatch, payload_or_exc):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")

    def fake_primary(*args, **kwargs):
        if isinstance(payload_or_exc, BaseException):
            raise payload_or_exc
        if isinstance(payload_or_exc, str):
            return payload_or_exc
        return json.dumps(payload_or_exc, ensure_ascii=False)

    monkeypatch.setattr(sem, "_call_llm_primary", fake_primary)


def _mock_primary_sequence(monkeypatch, payloads_or_excs):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    calls = []
    responses = list(payloads_or_excs)

    def fake_primary(*args, **kwargs):
        del args
        calls.append(kwargs)
        payload_or_exc = responses.pop(0) if responses else payloads_or_excs[-1]
        if isinstance(payload_or_exc, BaseException):
            raise payload_or_exc
        if isinstance(payload_or_exc, str):
            return payload_or_exc
        return json.dumps(payload_or_exc, ensure_ascii=False)

    monkeypatch.setattr(sem, "_call_llm_primary", fake_primary)
    return calls


def _primary_updates_payload(
    *,
    updates=None,
    confidence=0.92,
    intent="boss_switch",
    requires_clarification=False,
    previous_target=None,
    negated_entity=None,
    new_current_target=None,
    guide_only_entity=None,
    guide_request=False,
    strategy_request=False,
    candidate_boss=None,
    candidate_event="none",
    candidate_confidence="low",
    candidate_reason="",
    needs_confirmation=False,
    guide_entity=None,
    confirmation_intent="unknown",
    summary="安全候选摘要",
):
    return {
        "is_game_related": True,
        "intent": intent,
        "confidence": confidence,
        "requires_clarification": requires_clarification,
        "updates": updates or [],
        "previous_target": previous_target,
        "negated_entity": negated_entity,
        "new_current_target": new_current_target,
        "guide_only_entity": guide_only_entity,
        "guide_request": guide_request,
        "strategy_request": strategy_request,
        "candidate_boss": candidate_boss,
        "candidate_event": candidate_event,
        "candidate_confidence": candidate_confidence,
        "candidate_reason": candidate_reason,
        "needs_confirmation": needs_confirmation,
        "guide_entity": guide_entity,
        "confirmation_intent": confirmation_intent,
        "safe_trace_summary": summary,
    }


def test_explicit_current_boss_uses_rule_without_llm(monkeypatch):
    monkeypatch.setattr(sem, "_call_deepseek_flash", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM called")))

    result = sem.extract_semantics("我现在卡在女武神", "casual_chat", _game_state())

    assert result["llm_called"] is False
    assert result["final_decision"]["game_event"]["type"] == "boss_attempt"
    assert result["final_decision"]["game_event"]["boss_name"] == "女武神"


def test_negated_clear_phrase_is_failed_attempt_not_cleared():
    result = sem.extract_semantics("没打过", "casual_chat", _game_state("恶兆妖鬼 Margit"))

    assert result["llm_called"] is False
    assert result["final_decision"]["game_event"]["type"] == "failed_attempt"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_clear_phrase_is_boss_cleared():
    result = sem.extract_semantics("终于打过了", "casual_chat", _game_state("恶兆妖鬼 Margit"))

    assert result["llm_called"] is False
    assert result["final_decision"]["game_event"]["type"] == "boss_cleared"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_near_clear_phrase_is_ambiguous_and_not_cleared(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "mock")

    result = sem.extract_semantics("差点就过了", "casual_chat", _game_state("恶兆妖鬼 Margit"))

    assert result["ambiguity_detected"] is True
    assert result["llm_called"] is False
    assert result["fallback_reason"] == "near_clear_phrase"
    assert result["final_decision"]["game_event"]["type"] in {"near_clear", "failed_attempt"}
    assert result["final_decision"]["game_event"]["type"] != "boss_cleared"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_remaining_health_failure_is_not_cleared(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "mock")

    result = sem.extract_semantics("只剩一点血但没过", "casual_chat", _game_state("恶兆妖鬼 Margit"))

    assert result["ambiguity_detected"] is True
    assert result["final_decision"]["game_event"]["type"] in {"near_clear", "failed_attempt"}
    assert result["final_decision"]["game_event"]["type"] != "boss_cleared"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_boss_start_uses_rule_without_llm(monkeypatch):
    monkeypatch.setattr(sem, "_call_deepseek_flash", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM called")))

    result = sem.extract_semantics("我去打大树守卫", "casual_chat", _game_state())

    assert result["llm_called"] is False
    assert result["final_decision"]["game_event"]["type"] == "boss_attempt"
    assert result["final_decision"]["game_event"]["boss_name"] == "大树守卫"


def test_strategy_question_does_not_reopen_cleared_boss_as_attempt(monkeypatch):
    monkeypatch.setattr(sem, "_call_deepseek_flash", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM called")))

    result = sem.extract_semantics("玛尔基特二阶段怎么打？", "elden_ring_boss_strategy", _game_state("恶兆妖鬼 Margit"))

    assert result["llm_called"] is False
    assert result["final_decision"]["game_event"]["type"] == "none"
    assert result["applied_updates"] == []


def test_passive_death_statement_has_safe_trace_without_clearing(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "mock")

    result = sem.extract_semantics("我被大树守卫杀了4次，有点烦。", "casual_chat", _game_state())

    assert result["llm_called"] is False
    assert result["ambiguity_detected"] is True
    assert result["fallback_reason"] == "passive_death_statement"
    assert result["source"] == "rule"
    assert result["confidence"] == "high"
    assert result["latest_user_message"].startswith("被动死亡表达 /")
    assert "我被大树守卫杀了4次" not in result["latest_user_message"]
    assert "boss_failed" in result["applied_updates"]
    assert "boss_detected" in result["applied_updates"]
    assert "emotion_frustrated" in result["applied_updates"]
    assert result["final_decision"]["game_event"]["type"] == "failed_attempt"
    assert result["final_decision"]["game_event"]["boss_name"] == "大树守卫"


def test_passive_death_statement_calls_llm_shadow_when_provider_available(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(
        sem,
        "_call_deepseek_flash",
        lambda *args, **kwargs: json.dumps(
            _shadow_payload(boss="tree_sentinel", death_operation="set", death_value=4, frustration="raise"),
            ensure_ascii=False,
        ),
    )

    result = sem.extract_semantics("我被大树守卫杀了4次，有点烦。", "casual_chat", _game_state())

    assert result["llm_called"] is True
    assert result["fallback_reason"] == "passive_death_statement"
    assert result["source"] == "rule"
    assert result["confidence"] == "high"
    assert result["parse_error"] is None
    assert result["llm_shadow_status"] == "succeeded"
    assert "大树守卫" in result["llm_shadow_summary"]
    assert "失败次数" in result["llm_shadow_summary"]
    assert result["final_decision"]["game_event"]["type"] == "failed_attempt"
    assert result["final_decision"]["game_event"]["boss_name"] == "大树守卫"


def test_passive_death_llm_failure_falls_back_to_rule_trace(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(sem, "_call_deepseek_flash", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("provider failed")))

    result = sem.extract_semantics("被玛尔基特杀了3次。", "casual_chat", _game_state())

    assert result["llm_called"] is True
    assert result["parse_error"] == "semantic_extraction_provider_error"
    assert "provider failed" not in result["parse_error"]
    assert result["fallback_reason"] == "passive_death_statement"
    assert result["source"] == "rule"
    assert result["final_decision"]["game_event"]["type"] == "failed_attempt"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_slang_failure_expression_has_safe_trace_without_hardcoded_update(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "mock")

    result = sem.extract_semantics("这树守卫给我薄纱了四回，真的烦。", "casual_chat", _game_state())

    assert result["llm_called"] is False
    assert result["latest_user_message"].startswith("低置信游戏语义 /")
    assert "这树守卫给我薄纱了四回" not in result["latest_user_message"]
    assert result["fallback_reason"] == "slang_failure_expression"
    assert result["skip_reason"] == "provider_unavailable"
    assert result["source"] == "rule"
    assert result["confidence"] == "medium"
    assert "emotion_frustrated" in result["applied_updates"]
    assert result["final_decision"]["game_event"]["type"] == "none"


def test_unknown_boss_alias_failure_is_observable_noop(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "mock")

    result = sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state())

    assert result["llm_called"] is False
    assert result["latest_user_message"].startswith("低置信游戏语义 /")
    assert "骑马金甲大哥" not in result["latest_user_message"]
    assert result["fallback_reason"] == "unknown_boss_alias"
    assert result["skip_reason"] == "provider_unavailable"
    assert result["source"] == "none"
    assert result["confidence"] == "low"
    assert result["applied_updates"] == []
    assert result["final_decision"]["game_event"]["type"] == "none"


def test_hollow_knight_unknown_alias_failure_is_observable_noop(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "mock")

    result = sem.extract_semantics("空洞骑士里那个一开始拿锤子的家伙把我打爆了。", "casual_chat", _game_state())

    assert result["llm_called"] is False
    assert result["latest_user_message"].startswith("低置信游戏语义 /")
    assert "拿锤子的家伙" not in result["latest_user_message"]
    assert result["fallback_reason"] == "unknown_boss_alias"
    assert result["skip_reason"] == "provider_unavailable"
    assert result["source"] == "none"
    assert result["confidence"] == "low"
    assert result["applied_updates"] == []


def test_game_semantic_hint_no_rule_update_emits_low_confidence_trace(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "mock")

    result = sem.extract_semantics("空洞骑士里这个 boss 二阶段打起来怎么处理。", "casual_chat", _game_state())

    assert result["llm_called"] is False
    assert result["fallback_reason"] == "game_semantic_keywords_no_rule_update"
    assert result["skip_reason"] == "provider_unavailable"
    assert result["source"] == "none"
    assert result["confidence"] == "low"
    assert result["applied_updates"] == []


def test_casual_chat_does_not_trigger_llm_shadow(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(sem, "_call_deepseek_flash", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shadow called")))

    result = sem.extract_semantics("今天吃饭了吗？", "casual_chat", _game_state())

    assert result["llm_called"] is False
    assert result["skip_reason"] == "no_semantic_signal"
    assert result["llm_shadow_status"] == "skipped"


def test_explicit_game_semantics_triggers_llm_shadow_without_overriding_rule(monkeypatch):
    calls = []
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        return json.dumps(_shadow_payload(boss="tree_sentinel", death_operation="none", confidence="medium"), ensure_ascii=False)

    monkeypatch.setattr(sem, "_call_deepseek_flash", fake_call)

    result = sem.extract_semantics("我去打大树守卫", "casual_chat", _game_state())

    assert calls
    assert result["llm_called"] is True
    assert result["llm_shadow_status"] == "succeeded"
    assert result["source"] == "rule"
    assert result["final_decision"]["game_event"]["type"] == "boss_attempt"
    assert result["final_decision"]["game_event"]["boss_name"] == "大树守卫"


def test_low_confidence_game_semantic_calls_llm_shadow_when_provider_available(monkeypatch):
    calls = []
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")

    def fake_call(*args, **kwargs):
        calls.append((args, kwargs))
        return json.dumps(
            _shadow_payload(
                game="elden_ring",
                boss="tree_sentinel",
                death_operation="increment",
                death_value=2,
                frustration="raise",
                proactive="repeated_death",
                confidence="medium",
            ),
            ensure_ascii=False,
        )

    monkeypatch.setattr(sem, "_call_deepseek_flash", fake_call)

    result = sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state())

    assert calls
    assert result["llm_called"] is True
    assert result["fallback_reason"] == "unknown_boss_alias"
    assert result["skip_reason"] is None
    assert result["source"] == "none"
    assert result["applied_updates"] == []
    assert result["llm_shadow_status"] == "succeeded"
    assert result["llm_shadow"]["boss"]["value"] == "tree_sentinel"
    assert result["llm_shadow"]["proactive_signal"]["type"] == "repeated_death"
    assert "规则未识别，LLM 认为可能是 大树守卫" == result["llm_shadow_diff"]
    assert "大树守卫" in result["llm_shadow_summary"]
    assert result["final_decision"]["game_event"]["type"] == "none"


def test_low_confidence_game_semantic_llm_unavailable_degrades_safely(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "")

    result = sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state())

    assert result["llm_called"] is False
    assert result["fallback_reason"] == "unknown_boss_alias"
    assert result["skip_reason"] == "provider_unavailable"
    assert result["source"] == "none"
    assert result["llm_shadow_status"] == "skipped"
    assert result["llm_shadow"]["skip_reason"] == "provider_unavailable"
    assert "provider_unavailable" in result["llm_shadow_summary"]
    serialized = json.dumps(result, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert ".env" not in serialized
    assert "authorization" not in serialized
    assert "我在那个骑马金甲大哥那里又寄了几次" not in result["latest_user_message"]


def test_shadow_provider_uses_current_deepseek_config_and_fast_timeout(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["authorization"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "runtime-key")
    monkeypatch.setattr(sem.settings, "deepseek_base_url", "https://provider.example/v1")
    monkeypatch.setattr(sem.settings, "deepseek_model_fast", "deepseek-fast-runtime")
    monkeypatch.setattr(sem.settings, "llm_timeout_seconds", 20)
    monkeypatch.setattr(sem.urllib.request, "urlopen", fake_urlopen)

    result = sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state())

    assert result["llm_called"] is True
    assert result["llm_shadow_status"] == "succeeded"
    assert result["semantic_extraction_model"] == "deepseek-fast-runtime"
    assert captured["url"] == "https://provider.example/v1/chat/completions"
    assert captured["authorization"] == "Bearer runtime-key"
    assert captured["payload"]["model"] == "deepseek-fast-runtime"
    assert captured["payload"]["max_tokens"] == 512
    assert captured["payload"]["temperature"] == 0
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert "Return ONLY one JSON object" in captured["payload"]["messages"][0]["content"]
    user_prompt = json.loads(captured["payload"]["messages"][1]["content"])
    assert user_prompt["task"] == "semantic_shadow_json"
    assert "format" in user_prompt
    assert "chat_history" not in user_prompt
    assert "messages" not in user_prompt
    assert 8 <= captured["timeout"] <= 15


def test_llm_primary_timeout_allows_slow_foreground_provider(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_timeout_seconds", 20)
    assert sem._semantic_primary_timeout_seconds() == 20.0

    monkeypatch.setattr(sem.settings, "llm_timeout_seconds", 2)
    assert sem._semantic_primary_timeout_seconds() == 8.0


def test_shadow_can_use_openai_compatible_provider_config(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        del timeout
        captured["url"] = request.full_url
        captured["authorization"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setattr(sem.settings, "llm_provider", "openai-compatible")
    monkeypatch.setattr(sem.settings, "openai_api_key", "compatible-key")
    monkeypatch.setattr(sem.settings, "openai_base_url", "https://compatible.example")
    monkeypatch.setattr(sem.settings, "openai_model", "compatible-fast")
    monkeypatch.setattr(sem.urllib.request, "urlopen", fake_urlopen)

    result = sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state())

    assert result["llm_called"] is True
    assert result["semantic_extraction_model"] == "compatible-fast"
    assert captured["url"] == "https://compatible.example/chat/completions"
    assert captured["authorization"] == "Bearer compatible-key"
    assert captured["payload"]["model"] == "compatible-fast"


def test_shadow_parser_accepts_strict_valid_compact_json():
    raw = json.dumps(
        {
            "related": True,
            "conf": "medium",
            "boss": {"op": "set", "value": "tree_sentinel", "label": "大树守卫", "conf": "medium"},
            "death": {"op": "increment", "value": 2, "conf": "medium"},
            "frustration": {"op": "raise", "conf": "medium"},
            "cleared": {"op": "none", "conf": "high"},
            "memory": {"create": False, "kind": "none", "summary": None, "conf": "low"},
            "proactive": {"type": "none", "conf": "low"},
            "summary": "possible failure",
        },
        ensure_ascii=False,
    )

    shadow = sem._parse_llm_shadow_json(raw, "我在那个骑马金甲大哥那里又寄了几次。")

    assert shadow["status"] == "succeeded"
    assert shadow["json_recovered"] is False
    assert shadow["json_recovery_stage"] == "strict"
    assert shadow["boss"]["value"] == "tree_sentinel"
    assert shadow["death_count"]["operation"] == "increment"
    assert shadow["death_count"]["value"] == 2
    assert shadow["frustration"]["operation"] == "raise"


def test_shadow_parser_recovers_json_from_markdown_fence():
    raw = "```json\n" + json.dumps(_shadow_payload(boss="tree_sentinel"), ensure_ascii=False) + "\n```"

    shadow = sem._parse_llm_shadow_json(raw, "我在那个骑马金甲大哥那里又寄了几次。")

    assert shadow["status"] == "succeeded"
    assert shadow["json_recovered"] is True
    assert shadow["json_recovery_stage"] == "fenced"
    assert shadow["boss"]["value"] == "tree_sentinel"


def test_shadow_json_recovery_is_reported_without_raw_response(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    raw = "```json\n" + json.dumps(_shadow_payload(boss="tree_sentinel"), ensure_ascii=False) + "\n```"
    monkeypatch.setattr(sem, "_call_deepseek_flash", lambda *args, **kwargs: raw)

    result = sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state())

    assert result["llm_shadow_status"] == "succeeded"
    assert result["llm_shadow"]["json_recovered"] is True
    assert "JSON 已安全恢复" in result["llm_shadow_summary"]
    serialized = json.dumps(result, ensure_ascii=False)
    assert "```json" not in serialized
    assert "骑马金甲大哥" not in serialized


def test_shadow_parser_recovers_json_with_prose_prefix_suffix():
    raw = "好的，结果如下：" + json.dumps(_shadow_payload(boss="false_knight"), ensure_ascii=False) + "\n仅供参考。"

    shadow = sem._parse_llm_shadow_json(raw, "空洞骑士里那个一开始拿锤子的家伙把我打爆了。")

    assert shadow["status"] == "succeeded"
    assert shadow["json_recovered"] is True
    assert shadow["json_recovery_stage"] == "object_extract"
    assert shadow["boss"]["value"] == "false_knight"


def test_llm_primary_recovers_jsonish_smart_quotes_and_fullwidth_colon():
    raw = "“result”： “ignored”"
    payload = "{“is_game_related”： true， “confidence”： 0.92， “updates”： [{“field”： “boss”， “value”： “玛尔基特”， “canonical”： “margit”， “confidence”： 0.92}]}"

    shadow = sem._parse_llm_primary_candidate(payload or raw, "我现在在打玛尔基特")

    assert shadow["status"] == "succeeded"
    assert shadow["json_recovered"] is True
    assert shadow["json_recovery_stage"] == "jsonish_repair"
    assert shadow["boss"]["value"] == "margit"


def test_llm_primary_unwraps_result_wrapper():
    payload = {
        "result": {
            "is_game_related": True,
            "confidence": 0.92,
            "updates": [{"field": "boss", "value": "玛尔基特", "canonical": "margit", "confidence": 0.92}],
        }
    }

    shadow = sem._parse_llm_primary_candidate(json.dumps(payload, ensure_ascii=False), "我现在在打玛尔基特")

    assert shadow["status"] == "succeeded"
    assert shadow["json_recovery_stage"] == "strict"
    assert shadow["boss"]["value"] == "margit"


def test_shadow_parser_accepts_first_object_from_array():
    raw = json.dumps([
        _shadow_payload(boss="tree_sentinel"),
        _shadow_payload(boss="margit"),
    ], ensure_ascii=False)

    shadow = sem._parse_llm_shadow_json(raw, "我在那个骑马金甲大哥那里又寄了几次。")

    assert shadow["status"] == "succeeded"
    assert shadow["json_recovered"] is True
    assert shadow["json_recovery_stage"] == "array_first"
    assert shadow["boss"]["value"] == "tree_sentinel"


def test_shadow_parser_accepts_ultra_compact_json():
    raw = json.dumps(
        {
            "related": True,
            "conf": "medium",
            "game": "hollow_knight",
            "boss": "false_knight",
            "failure": True,
            "death_count": 1,
            "frustration": "raise",
            "signals": ["unknown_boss_alias"],
            "summary": "possible false knight failure",
        },
        ensure_ascii=False,
    )

    shadow = sem._parse_llm_shadow_json(
        raw,
        "空洞骑士里那个一开始拿锤子的家伙把我打爆了。",
        provider_diagnostics={"ultra_compact_used": True, "attempts": ["normal_json", "compat_retry", "ultra_compact"]},
    )

    assert shadow["status"] == "succeeded"
    assert shadow["ultra_compact_used"] is True
    assert shadow["attempts"] == ["normal_json", "compat_retry", "ultra_compact"]
    assert shadow["json_recovery_stage"] == "strict"
    assert shadow["game"]["value"] == "hollow_knight"
    assert shadow["boss"]["value"] == "false_knight"
    assert shadow["death_count"]["operation"] == "increment"
    assert shadow["death_count"]["value"] == 1
    assert shadow["frustration"]["operation"] == "raise"


def test_shadow_parser_treats_ultra_compact_string_false_as_false():
    raw = json.dumps(
        {
            "related": True,
            "conf": "low",
            "game": "elden_ring",
            "boss": "unknown",
            "failure": "false",
            "death_count": None,
            "frustration": "none",
            "signals": [],
            "summary": "game mention only",
        },
        ensure_ascii=False,
    )

    shadow = sem._parse_llm_shadow_json(raw, "随便聊一下艾尔登法环。")

    assert shadow["status"] == "succeeded"
    assert shadow["death_count"]["operation"] == "none"
    assert shadow["death_count"]["value"] is None


def test_shadow_parser_rejects_no_json_and_malformed_json_safely():
    for raw in ("not json at all", "前缀 {not valid json} 后缀"):
        try:
            sem._parse_llm_shadow_json(raw, "我在那个骑马金甲大哥那里又寄了几次。")
        except ValueError as exc:
            assert "JSON" in str(exc)
        else:
            raise AssertionError("malformed shadow JSON parsed unexpectedly")


def test_shadow_parser_does_not_use_eval():
    source = inspect.getsource(sem._parse_llm_shadow_json) + inspect.getsource(sem._load_llm_shadow_json)

    assert "eval(" not in source
    assert "exec(" not in source


def test_shadow_can_be_deferred_without_calling_provider(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(sem, "_call_deepseek_flash", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("shadow called")))

    result = sem.extract_semantics(
        "我在那个骑马金甲大哥那里又寄了几次。",
        "casual_chat",
        _game_state(),
        run_llm_shadow=False,
    )

    assert result["llm_called"] is False
    assert result["llm_shadow_status"] == "skipped"
    assert result["llm_shadow"]["skip_reason"] == "shadow_deferred"
    assert result["llm_shadow_diff"] == "LLM 影子识别后台等待"
    assert result["applied_updates"] == []
    assert result["final_decision"]["memory_candidate"]["should_create_pending"] is False


def test_shadow_deferred_creates_pending_background_trace(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    since_id = sem.get_semantic_shadow_events()["latest_id"]

    deferred = sem.extract_semantics(
        "我在那个骑马金甲大哥那里又寄了几次。",
        "casual_chat",
        _game_state(),
        run_llm_shadow=False,
    )
    trace_id = sem.schedule_semantic_shadow_event(deferred)

    events = _shadow_events_since(since_id)
    assert trace_id.startswith("shadow#")
    assert events[-1]["trace_id"] == trace_id
    assert events[-1]["phase"] == "scheduled"
    assert events[-1]["status"] == "shadow_deferred"
    assert events[-1]["skip_reason"] == "shadow_deferred"
    assert "骑马金甲大哥" not in json.dumps(events, ensure_ascii=False)


def test_background_shadow_succeeded_produces_final_event_without_state_writes(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(
        sem,
        "_call_deepseek_flash",
        lambda *args, **kwargs: json.dumps(
            _shadow_payload(
                boss="tree_sentinel",
                death_operation="increment",
                death_value=2,
                memory=True,
                proactive="repeated_death",
            ),
            ensure_ascii=False,
        ),
    )
    since_id = sem.get_semantic_shadow_events()["latest_id"]
    deferred = sem.extract_semantics(
        "我在那个骑马金甲大哥那里又寄了几次。",
        "casual_chat",
        _game_state(),
        run_llm_shadow=False,
    )
    trace_id = sem.schedule_semantic_shadow_event(deferred)

    sem.run_semantic_shadow_background(
        "我在那个骑马金甲大哥那里又寄了几次。",
        "casual_chat",
        _game_state(),
        trace_id=trace_id,
    )

    events = _shadow_events_since(since_id)
    final_events = [event for event in events if event["phase"] == "final" and event["trace_id"] == trace_id]
    assert final_events
    final = final_events[-1]
    assert final["status"] == "shadow_succeeded"
    assert final["llm_shadow_status"] == "succeeded"
    assert final["response_format_used"] is True
    assert final["compat_retry_used"] is False
    assert final["json_recovery_stage"] == "strict"
    assert final["applied_updates"] == []
    assert "final_decision" not in final
    assert "memory_candidate" not in final
    assert "proactive_signal" not in final
    serialized = json.dumps(events, ensure_ascii=False)
    assert "骑马金甲大哥" not in serialized
    assert "raw prompt" not in serialized.lower()
    assert ".env" not in serialized.lower()


def test_background_shadow_timeout_produces_final_timeout_event(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    calls = []

    def fake_call(*args, **kwargs):
        calls.append(kwargs.get("use_response_format"))
        raise TimeoutError("raw prompt /Users/x/.env")

    monkeypatch.setattr(sem, "_call_deepseek_flash", fake_call)
    since_id = sem.get_semantic_shadow_events()["latest_id"]
    trace_id = sem.schedule_semantic_shadow_event(
        sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), run_llm_shadow=False)
    )

    sem.run_semantic_shadow_background("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), trace_id=trace_id)

    events = _shadow_events_since(since_id)
    final = [event for event in events if event["phase"] == "final" and event["trace_id"] == trace_id][-1]
    assert final["status"] == "shadow_timeout"
    assert final["parse_error"] == "semantic_extraction_timeout"
    assert calls == [True]
    serialized = json.dumps(final, ensure_ascii=False).lower()
    assert "骑马金甲大哥" not in serialized
    assert "raw prompt" not in serialized
    assert "/users/" not in serialized
    assert ".env" not in serialized


def test_background_shadow_invalid_json_produces_final_invalid_json_event(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    calls = []

    def fake_call(*args, **kwargs):
        calls.append((kwargs.get("use_response_format"), kwargs.get("ultra_compact")))
        return "not json"

    monkeypatch.setattr(sem, "_call_deepseek_flash", fake_call)
    since_id = sem.get_semantic_shadow_events()["latest_id"]
    trace_id = sem.schedule_semantic_shadow_event(
        sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), run_llm_shadow=False)
    )

    sem.run_semantic_shadow_background("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), trace_id=trace_id)

    final = [event for event in _shadow_events_since(since_id) if event["phase"] == "final" and event["trace_id"] == trace_id][-1]
    assert calls == [(True, False), (False, False), (False, True)]
    assert final["status"] == "shadow_invalid_json"
    assert final["parse_error"] == "semantic_extraction_parse_error"
    assert final["llm_shadow_summary"] == (
        "失败：ultra_compact invalid_json / attempts:normal_json>compat_retry>ultra_compact"
    )
    assert final["response_format_used"] is False
    assert final["compat_retry_used"] is True
    assert final["ultra_compact_used"] is True
    assert final["attempts"] == ["normal_json", "compat_retry", "ultra_compact"]
    assert final["last_failure"] == "invalid_json"
    assert final["json_recovery_stage"] == "failed"
    assert final["content_length_bucket"] == "short"
    assert final["first_char_type"] == "prose"


def test_background_shadow_retries_without_response_format_after_invalid_json(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    calls = []

    def fake_call(*args, **kwargs):
        use_response_format = kwargs.get("use_response_format")
        calls.append(use_response_format)
        if use_response_format:
            return "not json"
        return json.dumps(_shadow_payload(boss="tree_sentinel", death_operation="increment", death_value=1), ensure_ascii=False)

    monkeypatch.setattr(sem, "_call_deepseek_flash", fake_call)
    since_id = sem.get_semantic_shadow_events()["latest_id"]
    trace_id = sem.schedule_semantic_shadow_event(
        sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), run_llm_shadow=False)
    )

    sem.run_semantic_shadow_background("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), trace_id=trace_id)

    final = [event for event in _shadow_events_since(since_id) if event["phase"] == "final" and event["trace_id"] == trace_id][-1]
    assert calls == [True, False]
    assert final["status"] == "shadow_succeeded"
    assert final["response_format_used"] is False
    assert final["compat_retry_used"] is True
    assert final["json_recovery_stage"] == "strict"
    assert "兼容模式" in final["llm_shadow_summary"]
    assert final["applied_updates"] == []


def test_background_shadow_uses_ultra_compact_after_compat_invalid_json(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    calls = []

    def fake_call(*args, **kwargs):
        calls.append((kwargs.get("use_response_format"), kwargs.get("ultra_compact")))
        if kwargs.get("ultra_compact"):
            return json.dumps(
                {
                    "related": True,
                    "conf": "medium",
                    "game": "elden_ring",
                    "boss": "tree_sentinel",
                    "failure": True,
                    "death_count": None,
                    "frustration": "raise",
                    "signals": ["unknown_boss_alias"],
                    "summary": "possible tree sentinel failure",
                },
                ensure_ascii=False,
            )
        return "not json"

    monkeypatch.setattr(sem, "_call_deepseek_flash", fake_call)
    since_id = sem.get_semantic_shadow_events()["latest_id"]
    trace_id = sem.schedule_semantic_shadow_event(
        sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), run_llm_shadow=False)
    )

    sem.run_semantic_shadow_background("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), trace_id=trace_id)

    final = [event for event in _shadow_events_since(since_id) if event["phase"] == "final" and event["trace_id"] == trace_id][-1]
    assert calls == [(True, False), (False, False), (False, True)]
    assert final["status"] == "shadow_succeeded"
    assert final["response_format_used"] is False
    assert final["compat_retry_used"] is True
    assert final["ultra_compact_used"] is True
    assert final["attempts"] == ["normal_json", "compat_retry", "ultra_compact"]
    assert final["json_recovery_stage"] == "strict"
    assert "ultra_compact" in final["llm_shadow_summary"]
    assert final["applied_updates"] == []
    assert "final_decision" not in final
    assert "memory_candidate" not in final
    assert "proactive_signal" not in final


def test_shadow_empty_content_has_safe_diagnostics(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(
        sem,
        "_call_deepseek_flash",
        lambda *args, **kwargs: sem.SemanticShadowProviderResponse(
            content="",
            diagnostics={
                "response_format_used": kwargs.get("use_response_format"),
                "finish_reason": "stop",
                "content_length_bucket": "empty",
                "first_char_type": "empty",
            },
        ),
    )
    result = sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state())

    assert result["llm_shadow_status"] == "failed"
    assert result["llm_shadow"]["failure_reason"] == "invalid_json"
    assert result["llm_shadow"]["content_length_bucket"] == "empty"
    assert result["llm_shadow"]["first_char_type"] == "empty"
    assert result["llm_shadow"]["finish_reason"] == "stop"
    serialized = json.dumps(result, ensure_ascii=False)
    assert "骑马金甲大哥" not in serialized


def test_background_shadow_auth_error_produces_final_auth_failed_event(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    calls = []

    def fake_call(*args, **kwargs):
        calls.append(kwargs.get("use_response_format"))
        raise sem.SemanticShadowAuthError("auth failed with secret-token")

    monkeypatch.setattr(sem, "_call_deepseek_flash", fake_call)
    since_id = sem.get_semantic_shadow_events()["latest_id"]
    trace_id = sem.schedule_semantic_shadow_event(
        sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), run_llm_shadow=False)
    )

    sem.run_semantic_shadow_background("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), trace_id=trace_id)

    final = [event for event in _shadow_events_since(since_id) if event["phase"] == "final" and event["trace_id"] == trace_id][-1]
    assert final["status"] == "shadow_auth_failed"
    assert final["parse_error"] == "semantic_extraction_auth_failed"
    assert calls == [True]
    assert "secret-token" not in json.dumps(final, ensure_ascii=False)


def test_background_shadow_provider_error_produces_final_provider_error_event(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    calls = []

    def fake_call(*args, **kwargs):
        calls.append(kwargs.get("use_response_format"))
        raise RuntimeError("provider failed")

    monkeypatch.setattr(sem, "_call_deepseek_flash", fake_call)
    since_id = sem.get_semantic_shadow_events()["latest_id"]
    trace_id = sem.schedule_semantic_shadow_event(
        sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), run_llm_shadow=False)
    )

    sem.run_semantic_shadow_background("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), trace_id=trace_id)

    final = [event for event in _shadow_events_since(since_id) if event["phase"] == "final" and event["trace_id"] == trace_id][-1]
    assert final["status"] == "shadow_provider_error"
    assert final["parse_error"] == "semantic_extraction_provider_error"
    assert calls == [True]


def test_background_shadow_provider_unavailable_produces_final_event(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    since_id = sem.get_semantic_shadow_events()["latest_id"]
    trace_id = sem.schedule_semantic_shadow_event(
        sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), run_llm_shadow=False)
    )
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "")

    sem.run_semantic_shadow_background("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), trace_id=trace_id)

    final = [event for event in _shadow_events_since(since_id) if event["phase"] == "final" and event["trace_id"] == trace_id][-1]
    assert final["status"] == "shadow_provider_unavailable"
    assert final["llm_shadow_status"] == "skipped"
    assert final["skip_reason"] == "provider_unavailable"


def test_pending_shadow_trace_expires_with_safe_final_event(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    start = 1000.0
    monkeypatch.setattr(sem.time, "time", lambda: start)
    since_id = sem.get_semantic_shadow_events()["latest_id"]
    trace_id = sem.schedule_semantic_shadow_event(
        sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), run_llm_shadow=False)
    )
    monkeypatch.setattr(sem.time, "time", lambda: start + sem.SEMANTIC_SHADOW_EVENT_EXPIRE_SECONDS + 1)

    events = _shadow_events_since(since_id)

    final = [event for event in events if event["phase"] == "final" and event["trace_id"] == trace_id][-1]
    assert final["status"] == "shadow_expired"
    assert final["parse_error"] == "semantic_extraction_timeout"
    assert "超时或已过期" in final["llm_shadow_diff"]


def test_consecutive_background_shadow_inputs_append_safe_final_events(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(sem, "_call_deepseek_flash", lambda *args, **kwargs: json.dumps(_shadow_payload(boss="tree_sentinel"), ensure_ascii=False))
    since_id = sem.get_semantic_shadow_events()["latest_id"]
    first_trace = sem.schedule_semantic_shadow_event(
        sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), run_llm_shadow=False)
    )
    second_trace = sem.schedule_semantic_shadow_event(
        sem.extract_semantics("空洞骑士里那个一开始拿锤子的家伙把我打爆了。", "casual_chat", _game_state(), run_llm_shadow=False)
    )

    sem.run_semantic_shadow_background("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state(), trace_id=first_trace)
    sem.run_semantic_shadow_background("空洞骑士里那个一开始拿锤子的家伙把我打爆了。", "casual_chat", _game_state(), trace_id=second_trace)

    events = _shadow_events_since(since_id)
    final_trace_ids = [event["trace_id"] for event in events if event["phase"] == "final"]
    assert first_trace in final_trace_ids
    assert second_trace in final_trace_ids
    serialized = json.dumps(events, ensure_ascii=False)
    assert "骑马金甲大哥" not in serialized
    assert "拿锤子的家伙" not in serialized


def test_shadow_auth_error_is_classified_safely(monkeypatch):
    def fake_urlopen(request, timeout):
        del request, timeout
        raise urllib.error.HTTPError(
            url="https://provider.example/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(sem.urllib.request, "urlopen", fake_urlopen)

    result = sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state())

    assert result["llm_called"] is True
    assert result["llm_shadow_status"] == "failed"
    assert result["llm_shadow"]["failure_reason"] == "auth_failed"
    assert result["parse_error"] == "semantic_extraction_auth_failed"
    assert result["applied_updates"] == []


def test_shadow_timeout_is_classified_without_state_writes(monkeypatch):
    def fake_urlopen(request, timeout):
        del request, timeout
        raise socket.timeout("timed out with raw prompt /Users/aragoto/private/.env")

    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(sem.urllib.request, "urlopen", fake_urlopen)

    result = sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state())

    assert result["llm_called"] is True
    assert result["llm_shadow_status"] == "failed"
    assert result["llm_shadow"]["failure_reason"] == "timeout"
    assert result["parse_error"] == "semantic_extraction_timeout"
    assert result["applied_updates"] == []
    assert result["final_decision"]["game_event"]["type"] == "none"
    assert result["final_decision"]["memory_candidate"]["should_create_pending"] is False
    serialized = json.dumps(result, ensure_ascii=False).lower()
    assert "raw prompt" not in serialized
    assert "/users/aragoto" not in serialized
    assert ".env" not in serialized


def test_shadow_generic_provider_error_is_classified_safely(monkeypatch):
    def fake_urlopen(request, timeout):
        del request, timeout
        raise urllib.error.HTTPError(
            url="https://provider.example/v1/chat/completions",
            code=500,
            msg="Server Error",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(sem.urllib.request, "urlopen", fake_urlopen)

    result = sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state())

    assert result["llm_shadow_status"] == "failed"
    assert result["llm_shadow"]["failure_reason"] == "provider_error"
    assert result["parse_error"] == "semantic_extraction_provider_error"
    assert result["applied_updates"] == []


def test_hollow_knight_shadow_candidate_does_not_mutate_state(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(
        sem,
        "_call_deepseek_flash",
        lambda *args, **kwargs: json.dumps(
            _shadow_payload(
                game="hollow_knight",
                boss="false_knight",
                death_operation="increment",
                death_value=1,
                frustration="raise",
            ),
            ensure_ascii=False,
        ),
    )

    result = sem.extract_semantics("空洞骑士里那个一开始拿锤子的家伙把我打爆了。", "casual_chat", _game_state())

    assert result["llm_called"] is True
    assert result["llm_shadow_status"] == "succeeded"
    assert result["llm_shadow"]["game"]["value"] == "hollow_knight"
    assert result["llm_shadow"]["boss"]["value"] == "false_knight"
    assert "假骑士" in result["llm_shadow_summary"]
    assert result["applied_updates"] == []
    assert result["final_decision"]["game_event"]["type"] == "none"


def test_shadow_memory_and_proactive_candidates_are_not_applied(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(
        sem,
        "_call_deepseek_flash",
        lambda *args, **kwargs: json.dumps(
            _shadow_payload(
                boss="tree_sentinel",
                death_operation="increment",
                death_value=3,
                memory=True,
                proactive="repeated_death",
            ),
            ensure_ascii=False,
        ),
    )

    result = sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state())

    assert result["llm_shadow"]["memory_candidate"]["should_create"] is True
    assert result["llm_shadow"]["proactive_signal"]["type"] == "repeated_death"
    assert "memory_candidate_created" not in result["applied_updates"]
    assert "boss_failed" not in result["applied_updates"]
    assert result["final_decision"]["memory_candidate"]["should_create_pending"] is False
    assert result["final_decision"]["game_event"]["type"] == "none"


def test_shadow_invalid_json_fails_safely_without_raw_payload(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(sem, "_call_deepseek_flash", lambda *args, **kwargs: "raw prompt /Users/aragoto/private/.env sk-secret")

    result = sem.extract_semantics("我在那个骑马金甲大哥那里又寄了几次。", "casual_chat", _game_state())

    assert result["llm_called"] is True
    assert result["llm_shadow_status"] == "failed"
    assert result["llm_shadow"]["failure_reason"] == "invalid_json"
    assert result["parse_error"] == "semantic_extraction_parse_error"
    serialized = json.dumps(result, ensure_ascii=False).lower()
    assert "raw prompt" not in serialized
    assert "/users/aragoto" not in serialized
    assert ".env" not in serialized
    assert "sk-secret" not in serialized


def test_safe_label_preserves_non_path_slash_and_redacts_local_paths():
    assert sem._safe_label("仅攻略/策略请求，不写入当前 Boss") == "仅攻略/策略请求，不写入当前 Boss"
    sanitized = sem._safe_label("raw prompt /Users/aragoto/private/.env C:\\Users\\name\\secret.env")
    assert "[redacted]" in sanitized
    assert "[path]" in sanitized
    assert "/Users/aragoto" not in sanitized
    assert "C:\\Users" not in sanitized


def test_shadow_safe_summary_sanitizes_untrusted_model_text(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    user_message = "我在那个骑马金甲大哥那里又寄了几次。"
    payload = _shadow_payload(
        boss="tree_sentinel",
        boss_label=f"{user_message} /Users/aragoto/private/.env raw prompt sk-secret",
        memory=True,
        reasoning=f"{user_message} stdout stderr /Users/aragoto/private/.env",
    )
    payload["memory_candidate"]["safe_summary"] = f"{user_message} DEEPSEEK_API_KEY=/Users/aragoto/private/.env"
    monkeypatch.setattr(sem, "_call_deepseek_flash", lambda *args, **kwargs: json.dumps(payload, ensure_ascii=False))

    result = sem.extract_semantics(user_message, "casual_chat", _game_state())

    serialized = json.dumps(result["llm_shadow"], ensure_ascii=False).lower()
    assert user_message not in serialized
    assert "/users/aragoto" not in serialized
    assert ".env" not in serialized
    assert "raw prompt" not in serialized
    assert "stdout" not in serialized
    assert "stderr" not in serialized
    assert "deepseek_api_key" not in serialized
    assert "sk-secret" not in serialized


def test_short_guide_preference_creates_pending_candidate():
    result = sem.extract_semantics("我喜欢简短的游戏攻略", "casual_chat", _game_state())

    candidate = result["final_decision"]["memory_candidate"]
    assert result["llm_called"] is False
    assert candidate["should_create_pending"] is True
    assert candidate["type"] == "guide_preference"
    assert "简短" in candidate["text"]


def test_personal_preference_without_remember_does_not_create_pending_or_call_llm():
    result = sem.extract_semantics("我喜欢吃菠萝", "casual_chat", _game_state())

    assert result["llm_called"] is False
    assert result["skip_reason"] == "no_semantic_signal"
    assert result["final_decision"]["memory_candidate"]["should_create_pending"] is False


def test_personal_preference_with_remember_creates_pending_candidate():
    result = sem.extract_semantics("记住我喜欢吃菠萝", "casual_chat", _game_state())

    candidate = result["final_decision"]["memory_candidate"]
    assert result["llm_called"] is False
    assert candidate["should_create_pending"] is True
    assert candidate["type"] == "personal_preference"
    assert "喜欢吃菠萝" in candidate["text"]


def test_explicit_playstyle_memory_request_creates_pending_candidate():
    result = sem.extract_semantics("记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。", "casual_chat", _game_state())

    candidate = result["final_decision"]["memory_candidate"]
    assert result["llm_called"] is False
    assert candidate["should_create_pending"] is True
    assert candidate["type"] == "playstyle_preference"
    assert "先探索地图" in candidate["text"]
    assert "直接硬打" in candidate["text"]


def test_negative_memory_request_does_not_create_pending_candidate():
    result = sem.extract_semantics("以后不用记住这个，只是我这次随便说一下。", "casual_chat", _game_state())

    candidate = result["final_decision"]["memory_candidate"]
    assert candidate["should_create_pending"] is False


def test_persona_preference_creates_low_confidence_pending_candidate():
    result = sem.extract_semantics("我喜欢你经常笑的样子", "casual_chat", _game_state())

    candidate = result["final_decision"]["memory_candidate"]
    assert result["llm_called"] is False
    assert candidate["should_create_pending"] is True
    assert candidate["type"] == "persona_preference"
    assert 0.6 <= candidate["confidence"] < 0.75


def test_llm_shadow_does_not_resolve_ambiguous_game_event_directly(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(
        sem,
        "_call_deepseek_flash",
        lambda *args, **kwargs: json.dumps(
            _shadow_payload(boss="margit", death_operation="increment", death_value=1, frustration="raise"),
            ensure_ascii=False,
        ),
    )

    result = sem.extract_semantics("差点过", "casual_chat", _game_state("恶兆妖鬼 Margit"))

    assert result["llm_called"] is True
    assert result["parse_error"] is None
    assert result["llm_shadow_status"] == "succeeded"
    assert result["llm_shadow"]["boss"]["value"] == "margit"
    assert result["final_decision"]["game_event"]["type"] == "near_clear"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_semantic_extraction_llm_defaults_to_fast_model(monkeypatch):
    captured_models = []

    def fake_urlopen(request, timeout):
        del timeout
        captured_models.append(json.loads(request.data.decode("utf-8"))["model"])
        return _FakeResponse()

    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(sem.urllib.request, "urlopen", fake_urlopen)

    result = sem.extract_semantics("差点过", "casual_chat", _game_state("恶兆妖鬼 Margit"))

    assert captured_models == ["deepseek-v4-flash"]
    assert result["llm_called"] is True
    assert result["semantic_extraction_model"] == "deepseek-v4-flash"
    assert result["semantic_extraction_latency_ms"] >= 0


def test_llm_cleared_result_does_not_override_near_clear_rule(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(
        sem,
        "_call_deepseek_flash",
        lambda *args, **kwargs: json.dumps(
            _shadow_payload(boss="margit", cleared="set_true", confidence="high"),
            ensure_ascii=False,
        ),
    )

    result = sem.extract_semantics("差点就过了", "casual_chat", _game_state("恶兆妖鬼 Margit"))

    assert result["llm_called"] is True
    assert result["final_decision"]["game_event"]["type"] in {"near_clear", "failed_attempt"}
    assert result["final_decision"]["game_event"]["type"] != "boss_cleared"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_llm_json_parse_failure_does_not_raise(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(sem, "_call_deepseek_flash", lambda *args, **kwargs: "not json")

    result = sem.extract_semantics("差点过", "casual_chat", _game_state("恶兆妖鬼 Margit"))

    assert result["llm_called"] is True
    assert result["parse_error"]
    assert result["final_decision"]["game_event"]["type"] in {"near_clear", "failed_attempt"}


@pytest.mark.parametrize("input_source", ["text", "voice_confirmed", "voice_direct"])
def test_llm_primary_records_input_source_and_applies_grounded_boss(monkeypatch, input_source):
    _mock_primary(monkeypatch, _primary_payload(boss="margit"))

    result = sem.extract_semantics(
        "我现在在打玛尔基特",
        "casual_chat",
        _game_state(),
        input_source=input_source,
        run_llm_primary=True,
    )

    assert result["input_source"] == input_source
    assert result["source"] == "llm_primary"
    assert result["llm_guard_decision"] == "apply"
    assert result["final_decision"]["game_event"]["guard_source"] == "llm_primary"
    assert result["final_decision"]["game_event"]["input_source"] == input_source
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_llm_primary_guide_only_boss_question_does_not_switch_current_boss(monkeypatch):
    _mock_primary(monkeypatch, _primary_payload(boss="margit", guide=True, strategy=True))

    result = sem.extract_semantics(
        "玛尔基特那边怎么打来着",
        "elden_ring_boss_strategy",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert result["llm_guard_decision"] in {"candidate_only", "no_op"}
    assert result["final_decision"]["game_event"]["type"] == "none"
    assert result["applied_updates"] == []


def test_llm_primary_explicit_voice_direct_switch_applies(monkeypatch):
    _mock_primary(monkeypatch, _primary_payload(boss="margit"))

    result = sem.extract_semantics(
        "我换去打玛尔基特了",
        "casual_chat",
        _game_state("女武神"),
        input_source="voice_direct",
        run_llm_primary=True,
    )

    event = result["final_decision"]["game_event"]
    assert result["llm_guard_decision"] == "apply"
    assert event["type"] == "boss_switch"
    assert event["boss_name"] == "恶兆妖鬼 Margit"
    assert event["input_source"] == "voice_direct"


@pytest.mark.parametrize(
    "message",
    [
        "我现在不打女武神了，换去打玛尔基特。",
        "先不打女武神了，我换去玛尔基特。",
        "从女武神换到玛尔基特。",
    ],
)
def test_llm_primary_switch_negation_overrides_old_rule_grounding(monkeypatch, message):
    _mock_primary(
        monkeypatch,
        _primary_payload(
            boss="margit",
            boss_switched=True,
            mentioned="malenia",
            negated="malenia",
            previous="malenia",
            new_current="margit",
        ),
    )

    result = sem.extract_semantics(
        message,
        "casual_chat",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert result["rule_result"]["game_event"]["boss_name"] == "女武神"
    assert result["source"] == "llm_primary"
    assert result["llm_guard_decision"] == "apply"
    assert result["llm_guard_reason"] == "switch_negation_candidate_overrules_rule_grounding"
    event = result["final_decision"]["game_event"]
    assert event["type"] == "boss_switch"
    assert event["boss_name"] == "恶兆妖鬼 Margit"
    assert event["guard_source"] == "llm_primary"
    assert "boss_switched" in result["applied_updates"]


def test_llm_primary_simple_rule_friendly_statement_still_uses_primary(monkeypatch):
    _mock_primary(monkeypatch, _primary_payload(boss="margit", current_target="margit"))

    result = sem.extract_semantics(
        "我换去打玛尔基特了。",
        "casual_chat",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert result["llm_called"] is True
    assert result["source"] == "llm_primary"
    assert result["llm_guard_decision"] == "apply"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_llm_primary_minimal_updates_json_applies_without_optional_fields(monkeypatch):
    _mock_primary(
        monkeypatch,
        {
            "is_game_related": True,
            "intent": "boss_switch",
            "confidence": 0.92,
            "updates": [
                {
                    "field": "boss",
                    "value": "玛尔基特",
                    "canonical": "margit",
                    "confidence": 0.92,
                    "reason": "用户说换去打玛尔基特",
                }
            ],
            "safe_trace_summary": "切换到玛尔基特",
        },
    )

    result = sem.extract_semantics(
        "我换去打玛尔基特了。",
        "casual_chat",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert result["parse_error"] is None
    assert result["llm_schema_valid"] is True
    assert result["source"] == "llm_primary"
    assert result["llm_guard_decision"] == "apply"
    assert result["applied_by"] == "llm_primary"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_llm_primary_updates_json_switch_negation_applies_margit(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_updates_payload(
            previous_target="malenia",
            negated_entity="malenia",
            new_current_target="margit",
            updates=[
                {
                    "field": "boss",
                    "value": "玛尔基特",
                    "canonical": "margit",
                    "confidence": 0.94,
                    "reason": "用户说从女武神换去玛尔基特",
                }
            ],
        ),
    )

    result = sem.extract_semantics(
        "我现在不打女武神了，换去打玛尔基特。",
        "casual_chat",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert result["rule_result"]["game_event"]["boss_name"] == "女武神"
    assert result["llm_schema_valid"] is True
    assert result["llm_guard_decision"] == "apply"
    assert result["llm_guard_reason"] == "switch_negation_candidate_overrules_rule_grounding"
    assert result["source"] == "llm_primary"
    assert result["final_decision"]["game_event"]["type"] == "boss_switch"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_llm_primary_guide_only_entity_does_not_switch_current_boss(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_payload(boss="margit", guide=True, strategy=True, guide_only="margit"),
    )

    result = sem.extract_semantics(
        "玛尔基特那边怎么打来着？",
        "elden_ring_boss_strategy",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert result["llm_guard_decision"] in {"candidate_only", "no_op"}
    assert result["llm_shadow"]["guide_only_entity"]["value"] == "margit"
    assert result["final_decision"]["game_event"]["type"] == "none"
    assert result["applied_updates"] == []


def test_llm_primary_updates_json_guide_only_does_not_switch(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_updates_payload(
            intent="guide_request",
            guide_request=True,
            strategy_request=True,
            guide_only_entity="margit",
            updates=[
                {"field": "guide_request", "value": True, "confidence": 0.9, "reason": "用户问打法"}
            ],
        ),
    )

    result = sem.extract_semantics(
        "玛尔基特那边怎么打来着？",
        "elden_ring_boss_strategy",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert result["parse_error"] is None
    assert result["llm_schema_valid"] is True
    assert result["llm_shadow"]["guide_request"]["value"] is True
    assert result["llm_shadow"]["guide_only_entity"]["value"] == "margit"
    assert result["final_decision"]["game_event"]["type"] == "none"
    assert result["applied_updates"] == []


@pytest.mark.parametrize(
    ("message", "candidate_boss", "expected_label"),
    [
        ("我换去打马尔吉特了", "margit", "恶兆妖鬼 Margit"),
        ("我现在去打女巫神了", "malenia", "女武神"),
        ("我在去打女巫神了", "malenia", "女武神"),
    ],
)
def test_llm_primary_voice_typo_candidates_apply_when_high_confidence(monkeypatch, message, candidate_boss, expected_label):
    _mock_primary(monkeypatch, _primary_payload(boss=candidate_boss, current_target=candidate_boss))

    result = sem.extract_semantics(
        message,
        "casual_chat",
        _game_state(),
        input_source="voice_direct",
        run_llm_primary=True,
    )

    assert result["llm_called"] is True
    assert result["input_source"] == "voice_direct"
    assert result["source"] == "llm_primary"
    assert result["llm_guard_decision"] == "apply"
    assert result["final_decision"]["game_event"]["boss_name"] == expected_label
    assert result["llm_shadow"]["current_target_candidate"]["value"] == candidate_boss


def test_llm_primary_voice_uncertain_typo_asks_clarification(monkeypatch):
    _mock_primary(monkeypatch, _primary_payload(boss="margit", current_target="margit", confidence="medium"))

    result = sem.extract_semantics(
        "我去打猫耳机特了",
        "casual_chat",
        _game_state(),
        input_source="voice_direct",
        run_llm_primary=True,
    )

    assert result["llm_called"] is True
    assert result["llm_guard_decision"] == "ask_clarification"
    assert result["llm_guard_reason"] == "voice_candidate_below_apply_threshold"
    assert result["final_decision"]["game_event"]["type"] == "none"
    assert result["llm_shadow"]["current_target_candidate"]["value"] == "margit"


def test_llm_primary_death_increment_applies_with_current_context(monkeypatch):
    _mock_primary(monkeypatch, _primary_payload(boss="unknown", death_operation="increment", death_value=2))

    result = sem.extract_semantics(
        "又死了两次",
        "casual_chat",
        _game_state("恶兆妖鬼 Margit"),
        run_llm_primary=True,
    )

    event = result["final_decision"]["game_event"]
    assert result["llm_guard_decision"] == "apply"
    assert event["type"] == "failed_attempt"
    assert event["death_count_operation"] == "increment"
    assert event["death_count_value"] == 2


def test_llm_primary_updates_json_death_increment(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_updates_payload(
            intent="death_update",
            updates=[
                {
                    "field": "death_count_increment",
                    "value": 2,
                    "confidence": 0.9,
                    "reason": "用户说又死了两次",
                }
            ],
        ),
    )

    result = sem.extract_semantics(
        "又死了两次。",
        "casual_chat",
        _game_state("恶兆妖鬼 Margit"),
        run_llm_primary=True,
    )

    event = result["final_decision"]["game_event"]
    assert result["parse_error"] is None
    assert result["llm_guard_decision"] == "apply"
    assert event["death_count_operation"] == "increment"
    assert event["death_count_value"] == 2


def test_llm_primary_death_absolute_applies_with_current_context(monkeypatch):
    _mock_primary(monkeypatch, _primary_payload(boss="unknown", death_operation="set", death_value=7))

    result = sem.extract_semantics(
        "死亡次数到 7 了",
        "casual_chat",
        _game_state("恶兆妖鬼 Margit"),
        run_llm_primary=True,
    )

    event = result["final_decision"]["game_event"]
    assert event["type"] == "failed_attempt"
    assert event["death_count_operation"] == "absolute"
    assert event["death_count_value"] == 7


def test_llm_primary_updates_json_death_absolute(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_updates_payload(
            intent="death_update",
            updates=[
                {
                    "field": "death_count_absolute",
                    "value": 3,
                    "confidence": 0.91,
                    "reason": "用户说已经死了3次",
                }
            ],
        ),
    )

    result = sem.extract_semantics(
        "已经死了3次。",
        "casual_chat",
        _game_state("恶兆妖鬼 Margit"),
        run_llm_primary=True,
    )

    event = result["final_decision"]["game_event"]
    assert result["parse_error"] is None
    assert result["llm_guard_decision"] == "apply"
    assert event["death_count_operation"] == "absolute"
    assert event["death_count_value"] == 3


def test_llm_primary_boss_cleared_applies(monkeypatch):
    _mock_primary(monkeypatch, _primary_payload(boss="margit", cleared="set_true"))

    result = sem.extract_semantics(
        "终于把玛尔基特过了",
        "casual_chat",
        _game_state("恶兆妖鬼 Margit"),
        run_llm_primary=True,
    )

    assert result["llm_guard_decision"] == "apply"
    assert result["final_decision"]["game_event"]["type"] == "boss_cleared"


def test_llm_primary_frustration_applies_only_as_guarded_emotion(monkeypatch):
    _mock_primary(monkeypatch, _primary_payload(boss="margit", frustration="raise"))

    result = sem.extract_semantics(
        "玛尔基特打得我有点烦",
        "casual_chat",
        _game_state("恶兆妖鬼 Margit"),
        run_llm_primary=True,
    )

    assert result["final_decision"]["emotion"]["type"] == "frustrated"
    assert result["final_decision"]["game_event"]["frustration_delta"] == 1


def test_llm_primary_invalid_json_does_not_apply_unknown_alias(monkeypatch):
    _mock_primary(monkeypatch, "not json")

    result = sem.extract_semantics(
        "我在那个骑马金甲大哥那里又寄了几次。",
        "casual_chat",
        _game_state(),
        run_llm_primary=True,
    )

    assert result["parse_error"] == "semantic_extraction_invalid_json"
    assert result["llm_guard_decision"] == "no_op"
    assert result["final_decision"]["game_event"]["type"] == "none"
    assert result["applied_updates"] == []


def test_llm_primary_schema_tolerates_unknown_operations_without_crashing(monkeypatch):
    _mock_primary(
        monkeypatch,
        {
            "is_game_related": True,
            "confidence": 0.8,
            "boss": {"operation": "teleport", "value": "margit", "confidence": 0.8},
            "safe_trace_summary": "未知操作应安全降级",
        },
    )

    result = sem.extract_semantics(
        "我现在在打玛尔基特",
        "casual_chat",
        _game_state(),
        run_llm_primary=True,
    )

    assert result["parse_error"] is None
    assert result["llm_schema_valid"] is True
    assert result["llm_shadow"]["boss"]["operation"] == "unknown"
    assert result["llm_guard_decision"] in {"candidate_only", "no_op"}


@pytest.mark.parametrize(
    "wrapped",
    [
        lambda payload: f"```json\n{payload}\n```",
        lambda payload: f"先给结论：{payload}\n就这些。",
        lambda payload: f"[{payload}]",
    ],
)
def test_llm_primary_recovers_fenced_prefixed_and_array_json(monkeypatch, wrapped):
    payload = json.dumps(
        _primary_updates_payload(
            updates=[
                {
                    "field": "boss",
                    "value": "玛尔基特",
                    "canonical": "margit",
                    "confidence": 0.93,
                    "reason": "用户说换去打玛尔基特",
                }
            ],
        ),
        ensure_ascii=False,
    )
    _mock_primary(monkeypatch, wrapped(payload))

    result = sem.extract_semantics(
        "我换去打玛尔基特了。",
        "casual_chat",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert result["parse_error"] is None
    assert result["llm_schema_valid"] is True
    assert result["llm_shadow"]["json_recovered"] is True
    assert result["llm_guard_decision"] == "apply"


def test_llm_primary_compat_retry_succeeds_after_invalid_json(monkeypatch):
    calls = _mock_primary_sequence(
        monkeypatch,
        [
            "not json",
            _primary_updates_payload(
                updates=[
                    {
                        "field": "boss",
                        "value": "玛尔基特",
                        "canonical": "margit",
                        "confidence": 0.93,
                        "reason": "兼容重试输出合法 JSON",
                    }
                ],
            ),
        ],
    )

    result = sem.extract_semantics(
        "我换去打玛尔基特了。",
        "casual_chat",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert len(calls) == 2
    assert calls[0]["use_response_format"] is True
    assert calls[1]["use_response_format"] is False
    assert calls[1]["compat_retry"] is True
    assert result["parse_error"] is None
    assert result["llm_schema_valid"] is True
    assert result["compat_retry_used"] is True
    assert result["compat_retry_succeeded"] is True
    assert result["first_attempt_failed"] == "invalid_json"
    assert result["llm_guard_decision"] == "apply"


def test_llm_primary_ultra_compact_retry_succeeds_after_compat_invalid_json(monkeypatch):
    calls = _mock_primary_sequence(
        monkeypatch,
        [
            "not json",
            "{\"is_game_related\": true,",
            _primary_updates_payload(
                updates=[
                    {
                        "field": "boss",
                        "value": "玛尔基特",
                        "canonical": "margit",
                        "confidence": 0.94,
                    }
                ],
                previous_target="malenia",
                negated_entity="malenia",
                new_current_target="margit",
            ),
        ],
    )

    result = sem.extract_semantics(
        "我现在不打女武神了，换去打玛尔基特。",
        "casual_chat",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert len(calls) == 3
    assert calls[0]["use_response_format"] is True
    assert calls[1]["use_response_format"] is False
    assert calls[1]["compat_retry"] is True
    assert calls[2]["use_response_format"] is False
    assert calls[2]["compat_retry"] is True
    assert calls[2]["ultra_compact"] is True
    assert result["parse_error"] is None
    assert result["llm_schema_valid"] is True
    assert result["compat_retry_used"] is True
    assert result["compat_retry_succeeded"] is True
    assert result["llm_shadow"]["ultra_compact_used"] is True
    assert result["llm_shadow"]["attempts"] == ["normal_json", "compat_retry", "ultra_compact"]
    assert result["llm_guard_decision"] == "apply"
    assert result["source"] == "llm_primary"
    assert result["applied_by"] == "llm_primary"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_llm_primary_compat_retry_failure_reports_invalid_json(monkeypatch):
    _mock_primary_sequence(monkeypatch, ["not json", "still not json"])

    result = sem.extract_semantics(
        "我现在不打女武神了，换去打玛尔基特。",
        "casual_chat",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert result["parse_error"] == "semantic_extraction_invalid_json"
    assert result["llm_provider_status"] == "invalid_json"
    assert result["llm_schema_valid"] is False
    assert result["first_attempt_failed"] == "invalid_json"
    assert result["compat_retry_used"] is True
    assert result["compat_retry_succeeded"] is False
    assert result["llm_shadow"]["ultra_compact_used"] is True
    assert result["llm_guard_decision"] == "no_op"


def test_llm_primary_schema_invalid_is_distinct_from_invalid_json(monkeypatch):
    invalid_schema_payload = {
        "is_game_related": True,
        "confidence": 0.9,
        "updates": [
            {
                "field": "boss",
                "value": {"unexpected": "object"},
                "canonical": "margit",
                "confidence": 0.9,
            }
        ],
    }
    _mock_primary_sequence(monkeypatch, [invalid_schema_payload, invalid_schema_payload])

    result = sem.extract_semantics(
        "我换去打玛尔基特了。",
        "casual_chat",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert result["parse_error"] == "semantic_extraction_schema_invalid"
    assert result["llm_provider_status"] == "schema_error"
    assert result["llm_schema_valid"] is False
    assert result["first_attempt_failed"] == "schema_invalid"
    assert result["compat_retry_used"] is True
    assert result["compat_retry_succeeded"] is False


def test_llm_primary_invalid_json_rule_fallback_trace_is_explicit(monkeypatch):
    _mock_primary_sequence(monkeypatch, ["not json", "still not json"])

    result = sem.extract_semantics(
        "我现在卡在玛尔基特",
        "casual_chat",
        _game_state(),
        run_llm_primary=True,
    )

    assert result["parse_error"] == "semantic_extraction_invalid_json"
    assert result["llm_provider_status"] == "invalid_json"
    assert result["llm_guard_decision"] == "fallback_to_rule"
    assert result["primary_extractor"] == "llm"
    assert result["fallback_extractor"] == "rule"
    assert result["guard_final_decision"] == "fallback_to_rule"
    assert result["applied_by"] == "rule_fallback"
    assert result["source"] == "rule"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_llm_primary_timeout_falls_back_to_high_confidence_rule(monkeypatch):
    _mock_primary(monkeypatch, TimeoutError("slow provider"))

    result = sem.extract_semantics(
        "我现在卡在玛尔基特",
        "casual_chat",
        _game_state(),
        run_llm_primary=True,
    )

    assert result["parse_error"] == "semantic_extraction_timeout"
    assert result["llm_guard_decision"] == "fallback_to_rule"
    assert "LLM extraction timeout" in result["llm_guard_summary"]
    assert result["llm_provider_status"] == "timeout"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_llm_primary_timeout_does_not_fallback_to_negated_old_target(monkeypatch):
    _mock_primary(monkeypatch, TimeoutError("slow provider"))

    result = sem.extract_semantics(
        "我现在不打女武神了，换去打玛尔基特。",
        "casual_chat",
        _game_state("女武神"),
        run_llm_primary=True,
    )

    assert result["parse_error"] == "semantic_extraction_timeout"
    assert result["llm_guard_decision"] == "no_op"
    assert result["final_decision"]["game_event"]["type"] == "none"
    assert result["applied_updates"] == []
    assert "LLM extraction timeout" in result["llm_guard_summary"]


def test_llm_primary_timeout_noops_without_rule_grounding(monkeypatch):
    _mock_primary(monkeypatch, TimeoutError("slow provider"))

    result = sem.extract_semantics(
        "那个骑马金甲大哥又寄了",
        "casual_chat",
        _game_state(),
        run_llm_primary=True,
    )

    assert result["parse_error"] == "semantic_extraction_timeout"
    assert result["llm_guard_decision"] == "no_op"
    assert result["final_decision"]["game_event"]["type"] == "none"


def test_llm_primary_rule_agreement_applies_medium_candidate(monkeypatch):
    _mock_primary(monkeypatch, _primary_payload(boss="margit", confidence="medium"))

    result = sem.extract_semantics(
        "我现在卡在玛尔基特",
        "casual_chat",
        _game_state(),
        run_llm_primary=True,
    )

    assert result["llm_guard_decision"] == "apply"
    assert result["llm_guard_reason"] == "llm_rule_agree"


def test_llm_primary_rule_conflict_asks_clarification_instead_of_rule_override(monkeypatch):
    _mock_primary(monkeypatch, _primary_payload(boss="tree_sentinel"))

    result = sem.extract_semantics(
        "我现在卡在玛尔基特",
        "casual_chat",
        _game_state(),
        run_llm_primary=True,
    )

    assert result["llm_guard_decision"] == "ask_clarification"
    assert result["llm_guard"]["conflict_summary"] == "boss_conflict"
    assert result["final_decision"]["game_event"]["type"] == "none"


def test_llm_primary_low_confidence_candidate_is_not_applied(monkeypatch):
    _mock_primary(monkeypatch, _primary_payload(boss="tree_sentinel", confidence="low"))

    result = sem.extract_semantics(
        "那个骑马金甲大哥又寄了",
        "casual_chat",
        _game_state(),
        run_llm_primary=True,
    )

    assert result["llm_guard_decision"] == "candidate_only"
    assert result["final_decision"]["game_event"]["type"] == "none"


def test_llm_primary_medium_unknown_alias_is_candidate_only(monkeypatch):
    _mock_primary(monkeypatch, _primary_payload(boss="tree_sentinel", confidence="medium"))

    result = sem.extract_semantics(
        "那个骑马金甲大哥又寄了",
        "casual_chat",
        _game_state(),
        run_llm_primary=True,
    )

    assert result["llm_guard_decision"] == "candidate_only"
    assert result["final_decision"]["game_event"]["type"] == "none"


def test_llm_primary_descriptive_plan_is_candidate_only(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_payload(
            boss="tree_sentinel",
            candidate_boss="tree_sentinel",
            candidate_event="boss_attempt",
            candidate_reason="descriptive_nickname",
            needs_confirmation=True,
            confidence="high",
        ),
    )

    result = sem.extract_semantics(
        "我去打那个金甲的",
        "casual_chat",
        _game_state(),
        run_llm_primary=True,
    )

    assert result["llm_guard_decision"] == "ask_clarification"
    assert result["llm_guard_reason"] == "uncertain_entity_candidate"
    assert result["candidate_boss"] == "tree_sentinel"
    assert result["candidate_event"] == "boss_attempt"
    assert result["needs_confirmation"] is True
    assert result["final_decision"]["game_event"]["type"] == "none"


def test_llm_primary_voice_direct_descriptive_entity_does_not_bypass_guard(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_payload(
            boss="tree_sentinel",
            candidate_boss="tree_sentinel",
            candidate_event="boss_attempt",
            candidate_reason="descriptive_nickname",
            needs_confirmation=True,
            confidence="high",
        ),
    )

    result = sem.extract_semantics(
        "我去打那个金甲的",
        "casual_chat",
        _game_state(),
        input_source="voice_direct",
        run_llm_primary=True,
    )

    assert result["input_source"] == "voice_direct"
    assert result["llm_guard_decision"] == "ask_clarification"
    assert result["final_decision"]["game_event"]["type"] == "none"


@pytest.mark.parametrize(
    "message",
    [
        "有可能是大树守卫吧？我没看清名字，死太快了",
        "名字太长我没记住，但是也许是吧？",
    ],
)
def test_llm_primary_uncertain_confirmation_keeps_candidate_without_apply(monkeypatch, message):
    _mock_primary(
        monkeypatch,
        _primary_payload(
            boss="tree_sentinel",
            candidate_boss="tree_sentinel",
            candidate_event="boss_failed",
            candidate_reason="uncertain_confirmation",
            confirmation_intent="uncertain",
            needs_confirmation=True,
            confidence="high",
        ),
    )
    game_state = _game_state()
    game_state["pending_candidate"] = {"candidate_boss": "tree_sentinel", "candidate_event": "boss_failed"}

    result = sem.extract_semantics(message, "casual_chat", game_state, run_llm_primary=True)

    assert result["llm_guard_decision"] == "candidate_only"
    assert result["llm_guard_reason"] == "uncertain_confirmation"
    assert result["confirmation_intent"] == "uncertain"
    assert result["candidate_boss"] == "tree_sentinel"
    assert result["final_decision"]["game_event"]["type"] == "none"


def test_llm_primary_clear_confirm_trace_does_not_apply_pending_runtime(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_payload(
            candidate_boss="tree_sentinel",
            candidate_event="boss_failed",
            confirmation_intent="confirm",
            confidence="high",
        ),
    )
    game_state = _game_state()
    game_state["pending_candidate"] = {"candidate_boss": "tree_sentinel", "candidate_event": "boss_failed"}

    result = sem.extract_semantics("对，就是它", "casual_chat", game_state, run_llm_primary=True)

    assert result["confirmation_intent"] == "confirm"
    assert result["llm_guard_decision"] == "candidate_only"
    assert result["llm_guard_reason"] == "pending_candidate_runtime_not_implemented"
    assert result["final_decision"]["game_event"]["type"] == "none"


def test_llm_primary_correction_applies_new_exact_target_without_old_candidate(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_payload(
            candidate_boss="margit",
            candidate_event="boss_attempt",
            confirmation_intent="correct",
            confidence="high",
        ),
    )
    game_state = _game_state()
    game_state["pending_candidate"] = {"candidate_boss": "tree_sentinel", "candidate_event": "boss_failed"}

    result = sem.extract_semantics("不是，是玛尔基特", "casual_chat", game_state, run_llm_primary=True)

    assert result["confirmation_intent"] == "correct"
    assert result["llm_guard_decision"] == "apply"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"


def test_llm_primary_high_unknown_alias_stays_candidate_without_confirmed_context(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_payload(
            boss="tree_sentinel",
            candidate_boss="tree_sentinel",
            candidate_event="boss_failed",
            candidate_reason="descriptive_nickname",
            needs_confirmation=True,
            death_operation="increment",
            death_value=1,
        ),
    )

    result = sem.extract_semantics(
        "那个骑马金甲大哥又寄了",
        "casual_chat",
        _game_state(),
        run_llm_primary=True,
    )

    assert result["llm_guard_decision"] == "ask_clarification"
    assert result["llm_guard_reason"] == "uncertain_entity_candidate"
    assert result["final_decision"]["game_event"]["type"] == "none"
    assert result["candidate_boss"] == "tree_sentinel"
    assert result["candidate_event"] == "boss_failed"
    assert result["needs_confirmation"] is True


def test_llm_primary_descriptive_alias_can_apply_when_current_boss_is_confirmed(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_payload(
            boss="tree_sentinel",
            candidate_boss="tree_sentinel",
            candidate_event="boss_failed",
            candidate_reason="descriptive_nickname",
            death_operation="increment",
            death_value=1,
        ),
    )

    result = sem.extract_semantics(
        "那个骑马金甲大哥又寄了",
        "casual_chat",
        _game_state("大树守卫"),
        run_llm_primary=True,
    )

    assert result["llm_guard_decision"] == "apply"
    assert result["final_decision"]["game_event"]["type"] == "failed_attempt"
    assert result["final_decision"]["game_event"]["boss_name"] == "大树守卫"


def test_llm_primary_memory_and_proactive_candidates_are_blocked(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_payload(game="unknown", memory=True, proactive="frustration_check", confidence="high"),
    )

    result = sem.extract_semantics(
        "记住我打 Boss 喜欢长攻略",
        "casual_chat",
        _game_state(),
        run_llm_primary=True,
    )

    assert result["llm_guard_decision"] == "no_op"
    assert result["final_decision"]["memory_candidate"]["should_create_pending"] is False
    assert "memory_candidate_created" not in result["applied_updates"]


def test_llm_primary_safe_trace_does_not_expose_raw_prompt_transcript_or_paths(monkeypatch):
    _mock_primary(
        monkeypatch,
        _primary_payload(
            boss="tree_sentinel",
            confidence="medium",
            reasoning="raw prompt /Users/aragoto/.env transcript sk-test stdout",
        ),
    )

    result = sem.extract_semantics(
        "那个骑马金甲大哥又寄了 /Users/aragoto/.env sk-test raw prompt",
        "casual_chat",
        _game_state(),
        input_source="voice_confirmed",
        run_llm_primary=True,
    )

    serialized = json.dumps(
        {
            "latest_user_message": result["latest_user_message"],
            "extraction_trace": result["extraction_trace"],
            "llm_shadow_summary": result["llm_shadow_summary"],
            "llm_guard": result["llm_guard"],
        },
        ensure_ascii=False,
    ).lower()
    assert "私密转写" not in serialized
    assert "/users/aragoto" not in serialized
    assert ".env" not in serialized
    assert "sk-test" not in serialized
    assert "raw prompt" not in serialized
    assert "transcript" not in serialized


def test_semantic_extraction_old_flow_without_primary_still_works(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "mock")

    result = sem.extract_semantics("我现在卡在玛尔基特", "casual_chat", _game_state(), run_llm_primary=False)

    assert result["llm_called"] is False
    assert result["source"] == "rule"
    assert result["final_decision"]["game_event"]["boss_name"] == "恶兆妖鬼 Margit"
