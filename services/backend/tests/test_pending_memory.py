import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.modules.dialogue_agent.prompt_preview import build_prompt_preview
from app.modules.memory import candidate_check as memory_candidate_check
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
        "last_failed_boss": current_boss if current_activity == "boss_failed" else None,
        "last_attempted_boss": current_boss,
        "last_cleared_boss": last_cleared_boss,
    }


def test_explicit_long_guide_preference_creates_pending_candidate():
    created = PendingMemoryQueue().generate_and_enqueue("我不喜欢长篇攻略", "", "casual_chat", _now(), {})

    assert len(created) == 1
    assert created[0]["type"] == "interaction_preference"
    assert created[0]["summary"] == "玩家不喜欢长篇攻略"
    assert created[0]["source"] == "semantic_extraction"
    assert created[0]["status"] == "pending"
    assert created[0]["requires_confirmation"] is True
    assert created[0]["evidence"].get("user_message") is None


def test_short_reply_preference_creates_interaction_candidate():
    created = PendingMemoryQueue().generate_and_enqueue("以后你回答短一点。", "", "casual_chat", _now(), {})

    assert len(created) == 1
    assert created[0]["type"] == "interaction_preference"
    assert "简短" in created[0]["summary"]
    assert PlayerMemory().load_profile().preferred_tone is None


def test_too_long_reply_preference_creates_interaction_candidate():
    created = PendingMemoryQueue().generate_and_enqueue("每次你说太长我都看不过来。", "", "casual_chat", _now(), {})

    assert len(created) == 1
    assert created[0]["type"] == "interaction_preference"
    assert "简短" in created[0]["summary"]
    assert created[0]["evidence"]["memory_check_source"] == "deterministic_fallback"


def test_soft_long_guide_preference_creates_interaction_candidate():
    created = PendingMemoryQueue().generate_and_enqueue(
        "我一般不太喜欢长篇攻略，给我一句重点就好。",
        "",
        "casual_chat",
        _now(),
        {},
    )

    assert len(created) == 1
    assert created[0]["type"] == "interaction_preference"
    assert created[0]["summary"] == "玩家不喜欢长篇攻略"


def test_spirit_ashes_preference_creates_gameplay_candidate():
    created = PendingMemoryQueue().generate_and_enqueue("我不想召骨灰", "", "casual_chat", _now(), {})

    assert len(created) == 1
    assert created[0]["type"] == "gameplay_preference"
    assert "骨灰" in created[0]["summary"]


def test_plain_personal_preference_without_remember_is_not_memory_candidate():
    created = PendingMemoryQueue().generate_and_enqueue("我喜欢吃菠萝", "", "casual_chat", _now(), {})

    assert created == []
    assert PendingMemoryQueue().list() == []


def test_explicit_personal_preference_with_remember_creates_unknown_candidate():
    created = PendingMemoryQueue().generate_and_enqueue("记住我喜欢吃菠萝", "", "casual_chat", _now(), {})

    assert len(created) == 1
    assert created[0]["type"] == "unknown"
    assert created[0]["summary"] == "玩家喜欢吃菠萝"
    assert created[0]["guard_reason"] == "explicit_user_memory_request"


def test_explicit_boss_exploration_preference_creates_pending_candidate_not_long_term():
    created = PendingMemoryQueue().generate_and_enqueue(
        "记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。",
        "",
        "casual_chat",
        _now(),
        {},
    )

    assert len(created) == 1
    assert created[0]["type"] == "gameplay_preference"
    assert created[0]["summary"] == "玩家打 Boss 前喜欢先探索地图，不喜欢直接硬打"
    assert created[0]["requires_confirmation"] is True
    assert created[0]["guard_reason"] == "explicit_user_memory_request"
    assert PlayerMemory().load_profile().long_term_memories == []


def test_process_explicit_memory_request_auto_saves_and_returns_undo_target():
    queue = PendingMemoryQueue()
    result = queue.process_user_message(
        "记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。",
        "嗯，记住了。",
        "casual_chat",
        _now(),
        {},
    )

    profile = PlayerMemory().load_profile()
    all_items = queue.list(status=None)

    assert result["status"] == "auto_saved"
    assert result["summary"] == "玩家打 Boss 前喜欢先探索地图，不喜欢直接硬打"
    assert result["long_term_memory_id"]
    assert result["undo_available"] is True
    assert queue.list() == []
    assert all_items[0]["status"] == "accepted"
    assert all_items[0]["long_term_memory_id"] == result["long_term_memory_id"]
    assert profile.long_term_memories[0]["id"] == result["long_term_memory_id"]
    assert profile.long_term_memories[0]["is_active"] is True


def test_undo_auto_saved_memory_removes_it_from_prompt_context():
    queue = PendingMemoryQueue()
    result = queue.process_user_message(
        "记住我不喜欢长篇攻略",
        "我记下了。",
        "casual_chat",
        _now(),
        {},
    )
    memory_id = result["long_term_memory_id"]

    undone = PlayerMemory().deactivate_long_term_memory(memory_id)
    profile = PlayerMemory().load_profile()
    prompt_text = PlayerMemory().build_prompt_context()

    assert undone["is_active"] is False
    assert profile.long_term_memories[0]["is_active"] is False
    assert profile.preferred_tone is None
    assert "长篇攻略" not in prompt_text


def test_negative_memory_request_records_guarded_rejection_without_pending_candidate():
    queue = PendingMemoryQueue()
    created = queue.generate_and_enqueue(
        "以后不用记住这个，只是我这次随便说一下。",
        "",
        "casual_chat",
        _now(),
        {},
    )

    assert queue.list() == []
    assert len(created) == 1
    assert created[0]["type"] == "do_not_remember"
    assert created[0]["status"] == "rejected_by_guard"
    assert created[0]["guard_reason"] == "do_not_remember"


def test_session_event_death_statement_does_not_create_memory_candidate():
    created = PendingMemoryQueue().generate_and_enqueue(
        "我刚刚打玛尔基特死了三次。",
        "",
        "casual_chat",
        _now(),
        _game_state(current_boss="恶兆妖鬼 Margit", current_activity="boss_failed"),
    )

    assert created == []
    assert PendingMemoryQueue().list() == []


def test_boss_cleared_session_event_does_not_create_long_term_candidate():
    created = PendingMemoryQueue().generate_and_enqueue(
        "打过大树守卫了",
        "",
        "casual_chat",
        _now(),
        _game_state(current_activity="boss_cleared", last_cleared_boss="大树守卫"),
    )

    assert created == []
    assert PendingMemoryQueue().list() == []


def test_spoiler_preference_creates_gameplay_candidate():
    created = PendingMemoryQueue().generate_and_enqueue("之后别剧透支线，除非我主动问。", "", "casual_chat", _now(), {})

    assert len(created) == 1
    assert created[0]["type"] == "gameplay_preference"
    assert "避免剧透" in created[0]["summary"]


def test_persona_drift_request_is_rejected_without_saving_raw_terms():
    queue = PendingMemoryQueue()
    created = queue.generate_and_enqueue("以后你都撒娇一点，每句话都夸我。", "", "casual_chat", _now(), {})
    serialized = json.dumps(queue.list(status=None), ensure_ascii=False)

    assert queue.list() == []
    assert len(created) == 1
    assert created[0]["status"] == "rejected_by_guard"
    assert created[0]["guard_reason"] == "persona_drift_blocked"
    assert "撒娇" not in serialized
    assert "每句话" not in serialized


def test_secret_memory_request_is_rejected_without_secret_leak():
    queue = PendingMemoryQueue()
    queue.generate_and_enqueue(
        "记住我的 DEEPSEEK_API_KEY=sk-secret-value",
        "",
        "casual_chat",
        _now(),
        {},
    )
    serialized = json.dumps(queue.list(status=None), ensure_ascii=False)

    assert queue.list() == []
    assert "sk-secret-value" not in serialized
    assert "DEEPSEEK_API_KEY" not in serialized
    assert "sensitive_secret_blocked" in serialized


def test_llm_memory_check_runs_for_implicit_preference_when_provider_available(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        memory_candidate_check,
        "_provider_config",
        lambda: {"provider": "deepseek", "api_key": "test", "base_url": "http://127.0.0.1", "model": "fast"},
    )

    def fake_call(provider, user_message, *, input_source, game_state_summary):
        del provider, input_source, game_state_summary
        calls.append(user_message)
        return json.dumps(
            {
                "should_create": True,
                "suggested_action": "pending",
                "type": "interaction_preference",
                "safe_summary": "玩家不喜欢详细攻略，容易觉得被剧透",
                "confidence": 0.91,
                "explicit_request": False,
                "reason": "implicit_preference",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(memory_candidate_check, "_call_memory_check_provider", fake_call)

    result = memory_candidate_check.check_memory_candidate("我不喜欢看详细攻略，感觉像被剧透。")

    assert calls == ["我不喜欢看详细攻略，感觉像被剧透。"]
    assert result.source == "llm_primary"
    assert result.suggested_action == "pending"
    assert result.safe_summary == "玩家不喜欢详细攻略，容易觉得被剧透"


def test_rule_prefilter_does_not_suppress_llm_for_too_long_reply_preference(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        memory_candidate_check,
        "_provider_config",
        lambda: {"provider": "deepseek", "api_key": "test", "base_url": "http://127.0.0.1", "model": "fast"},
    )

    def fake_call(provider, user_message, *, input_source, game_state_summary):
        del provider, input_source, game_state_summary
        calls.append(user_message)
        return json.dumps(
            {
                "should_create": True,
                "suggested_action": "pending",
                "type": "interaction_preference",
                "safe_summary": "玩家觉得回复太长时看不过来",
                "confidence": 0.86,
                "explicit_request": False,
                "reason": "implicit_interaction_preference",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(memory_candidate_check, "_call_memory_check_provider", fake_call)

    result = memory_candidate_check.check_memory_candidate("每次你说太长我都看不过来。")

    assert calls == ["每次你说太长我都看不过来。"]
    assert result.source == "llm_primary"
    assert result.should_create is True


def test_obvious_unrelated_short_input_skips_llm_memory_check(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        memory_candidate_check,
        "_provider_config",
        lambda: {"provider": "deepseek", "api_key": "test", "base_url": "http://127.0.0.1", "model": "fast"},
    )

    def fake_call(provider, user_message, *, input_source, game_state_summary):
        del provider, input_source, game_state_summary
        calls.append(user_message)
        return "{}"

    monkeypatch.setattr(memory_candidate_check, "_call_memory_check_provider", fake_call)

    result = memory_candidate_check.check_memory_candidate("嗯")

    assert calls == []
    assert result.should_create is False
    assert result.source == "prefilter"
    assert result.provider_status == "not_run"


def test_llm_auto_save_suggestion_cannot_bypass_explicit_request_gate(monkeypatch):
    monkeypatch.setattr(
        memory_candidate_check,
        "_provider_config",
        lambda: {"provider": "deepseek", "api_key": "test", "base_url": "http://127.0.0.1", "model": "fast"},
    )

    def fake_call(provider, user_message, *, input_source, game_state_summary):
        del provider, user_message, input_source, game_state_summary
        return json.dumps(
            {
                "should_create": True,
                "suggested_action": "auto_save",
                "type": "interaction_preference",
                "safe_summary": "玩家不喜欢详细攻略",
                "confidence": 0.93,
                "explicit_request": False,
                "reason": "model_attempted_auto_save",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(memory_candidate_check, "_call_memory_check_provider", fake_call)

    result = memory_candidate_check.check_memory_candidate("我不喜欢看详细攻略，感觉像被剧透。")

    assert result.should_create is True
    assert result.suggested_action == "pending"
    assert result.reason == "implicit_candidate_downgraded_to_pending"


def test_guard_blocks_sensitive_input_before_llm_even_if_provider_available(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        memory_candidate_check,
        "_provider_config",
        lambda: {"provider": "deepseek", "api_key": "test", "base_url": "http://127.0.0.1", "model": "fast"},
    )

    def fake_call(provider, user_message, *, input_source, game_state_summary):
        del provider, input_source, game_state_summary
        calls.append(user_message)
        return "{}"

    monkeypatch.setattr(memory_candidate_check, "_call_memory_check_provider", fake_call)

    result = memory_candidate_check.check_memory_candidate("记住我的 API key 是 sk-test-secret。")

    assert calls == []
    assert result.suggested_action == "reject"
    assert result.reason == "sensitive_secret_blocked"
    assert result.provider_status == "blocked_before_llm"


def test_voice_direct_memory_intent_creates_pending_candidate_not_accepted():
    created = PendingMemoryQueue().generate_and_enqueue(
        "记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。",
        "",
        "casual_chat",
        _now(),
        {},
        input_source="voice_direct",
    )

    assert len(created) == 1
    assert created[0]["from_voice"] is True
    assert created[0]["source"] == "voice_direct"
    assert created[0]["confirmation_intent"] == "voice_direct"
    assert created[0]["status"] == "pending"
    assert PlayerMemory().load_profile().long_term_memories == []


def test_semantic_memory_candidate_creates_pending_candidate():
    semantic = {
        "input_source": "text",
        "final_decision": {
            "memory_candidate": {
                "should_create_pending": True,
                "type": "guide_preference",
                "text": "玩家喜欢简短提醒",
                "confidence": 0.86,
                "reason": "用户表达偏好",
            }
        },
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
    assert created[0]["type"] == "interaction_preference"
    assert created[0]["summary"] == "玩家喜欢简短提醒"
    assert created[0]["source"] == "semantic_extraction"


def test_semantic_persona_preference_low_confidence_creates_bounded_interaction_candidate():
    semantic = {
        "final_decision": {
            "memory_candidate": {
                "should_create_pending": True,
                "type": "persona_preference",
                "text": "玩家喜欢 Rei 说话更柔和一点",
                "confidence": 0.68,
                "reason": "用户表达 persona 偏好",
            }
        }
    }

    created = PendingMemoryQueue().generate_and_enqueue(
        "我喜欢你说话更柔和一点",
        "",
        "casual_chat",
        _now(),
        {},
        semantic_extraction=semantic,
    )

    assert len(created) == 1
    assert created[0]["type"] == "interaction_preference"
    assert created[0]["confidence"] == 0.68
    assert created[0]["source"] == "semantic_extraction"


def test_accept_pending_candidate_writes_visible_long_term_memory_and_episode():
    queue = PendingMemoryQueue()
    created = queue.generate_and_enqueue("我不喜欢长篇攻略", "", "casual_chat", _now(), {})

    accepted = queue.accept(created[0]["id"])
    profile = PlayerMemory().load_profile()
    episodes = PlayerMemory().recent_episodes(limit=5)

    assert accepted["status"] == "accepted"
    assert accepted["requires_confirmation"] is False
    assert profile.preferred_tone == "不喜欢长篇攻略"
    assert len(profile.long_term_memories) == 1
    assert profile.long_term_memories[0]["source_candidate_id"] == created[0]["id"]
    assert profile.long_term_memories[0]["user_visible_text"] == "玩家不喜欢长篇攻略"
    assert any(episode["summary"] == "玩家不喜欢长篇攻略" for episode in episodes)


def test_ignore_pending_candidate_does_not_write_long_term_memory():
    queue = PendingMemoryQueue()
    created = queue.generate_and_enqueue("我不喜欢长篇攻略", "", "casual_chat", _now(), {})

    ignored = queue.ignore(created[0]["id"])
    profile = PlayerMemory().load_profile()

    assert ignored["status"] == "ignored"
    assert ignored["requires_confirmation"] is False
    assert profile.preferred_tone is None
    assert profile.long_term_memories == []
    assert PlayerMemory().recent_episodes(limit=5) == []


def test_pending_candidate_is_not_in_prompt_preview_until_accepted():
    queue = PendingMemoryQueue()
    created = queue.generate_and_enqueue(
        "记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。",
        "",
        "casual_chat",
        _now(),
        {},
    )

    preview = build_prompt_preview()
    pending_preview_text = json.dumps(preview["memory_summary"], ensure_ascii=False)

    assert "探索地图" not in pending_preview_text

    queue.accept(created[0]["id"])
    accepted_preview = build_prompt_preview()
    accepted_preview_text = json.dumps(accepted_preview["memory_summary"], ensure_ascii=False)

    assert "探索地图" in accepted_preview_text


def test_duplicate_pending_candidate_is_not_generated_twice():
    queue = PendingMemoryQueue()
    first = queue.generate_and_enqueue("我不喜欢长篇攻略", "", "casual_chat", _now(), {})
    second = queue.generate_and_enqueue("不要给我长篇攻略", "", "casual_chat", _now(), {})

    assert len(first) == 1
    assert second == []
    assert len(queue.list()) == 1


def test_assistant_and_proactive_sources_are_blocked_from_memory_candidates():
    queue = PendingMemoryQueue()
    assistant = queue.generate_and_enqueue("玩家不喜欢长篇攻略", "", "casual_chat", _now(), {}, from_assistant=True)
    proactive = queue.generate_and_enqueue("玩家不喜欢长篇攻略", "", "casual_chat", _now(), {}, from_proactive=True)

    assert queue.list() == []
    assert assistant[0]["status"] == "rejected_by_guard"
    assert assistant[0]["guard_reason"] == "assistant_source_blocked"
    assert assistant[0]["from_assistant"] is True
    assert proactive[0]["from_proactive"] is True


def test_pending_candidate_expires_without_prompt_injection():
    queue = PendingMemoryQueue()
    created = queue.generate_and_enqueue("我不喜欢长篇攻略", "", "casual_chat", _now() - timedelta(days=31), {})

    assert len(created) == 1
    assert queue.list() == []
    assert queue.list(status=None)[0]["status"] == "expired"


def test_pending_memory_file_is_gitignored():
    gitignore = Path(__file__).resolve().parents[3] / ".gitignore"

    assert "data/memory/pending_memories.jsonl" in gitignore.read_text(encoding="utf-8")
