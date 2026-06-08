import json

from app.modules.dialogue_agent import semantic_extraction as sem


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "game_event": {
                                        "type": "failed_attempt",
                                        "boss_name": "Margit",
                                        "confidence": 0.82,
                                        "should_update_current_boss": True,
                                    },
                                    "memory_candidate": {
                                        "should_create_pending": False,
                                        "type": "none",
                                        "text": "",
                                        "confidence": 0,
                                        "reason": "",
                                    },
                                    "emotion": {"type": "frustrated", "intensity": 0.55},
                                },
                                ensure_ascii=False,
                            )
                        }
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


def test_passive_death_statement_calls_llm_fallback_when_provider_available(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(
        sem,
        "_call_deepseek_flash",
        lambda *args, **kwargs: json.dumps(
            {
                "game_event": {
                    "type": "failed_attempt",
                    "boss_name": "大树守卫",
                    "confidence": 0.82,
                    "should_update_current_boss": True,
                },
                "memory_candidate": {
                    "should_create_pending": False,
                    "type": "none",
                    "text": "",
                    "confidence": 0,
                    "reason": "",
                },
                "emotion": {"type": "frustrated", "intensity": 0.6},
            },
            ensure_ascii=False,
        ),
    )

    result = sem.extract_semantics("我被大树守卫杀了4次，有点烦。", "casual_chat", _game_state())

    assert result["llm_called"] is True
    assert result["fallback_reason"] == "passive_death_statement"
    assert result["source"] in {"mixed", "llm_fallback"}
    assert result["confidence"] == "high"
    assert result["parse_error"] is None
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


def test_llm_fallback_can_resolve_ambiguous_game_event(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(
        sem,
        "_call_deepseek_flash",
        lambda *args, **kwargs: json.dumps(
            {
                "game_event": {
                    "type": "failed_attempt",
                    "boss_name": "Margit",
                    "confidence": 0.82,
                    "should_update_current_boss": True,
                },
                "memory_candidate": {
                    "should_create_pending": False,
                    "type": "none",
                    "text": "",
                    "confidence": 0,
                    "reason": "",
                },
                "emotion": {"type": "frustrated", "intensity": 0.55},
            },
            ensure_ascii=False,
        ),
    )

    result = sem.extract_semantics("差点过", "casual_chat", _game_state("恶兆妖鬼 Margit"))

    assert result["llm_called"] is True
    assert result["parse_error"] is None
    assert result["final_decision"]["game_event"]["type"] == "failed_attempt"
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
            {
                "game_event": {
                    "type": "boss_cleared",
                    "boss_name": "Margit",
                    "confidence": 0.99,
                    "should_update_current_boss": True,
                },
                "memory_candidate": {
                    "should_create_pending": False,
                    "type": "none",
                    "text": "",
                    "confidence": 0,
                    "reason": "",
                },
                "emotion": {"type": "none", "intensity": 0},
            },
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
