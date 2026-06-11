import json
import socket
import urllib.error

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
    assert captured["payload"]["max_tokens"] == 700
    assert 8 <= captured["timeout"] <= 15


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
