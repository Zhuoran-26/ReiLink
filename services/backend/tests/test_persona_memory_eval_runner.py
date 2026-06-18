import json
from datetime import datetime, timezone

from app.modules.dialogue_agent.prompt_preview import build_prompt_preview
from app.modules.dialogue_agent.persona_memory_eval import (
    assert_report_is_safe,
    load_persona_memory_eval_scenarios,
    run_persona_memory_eval,
)
from app.modules.memory.profile import PlayerMemory, UserProfile
from app.modules.memory.store import ConversationStore


def test_persona_memory_eval_runner_mock_scenarios_pass():
    report = run_persona_memory_eval(provider_mode="mock")
    metrics = report["metrics"]

    assert 20 <= metrics["total_scenarios"] <= 30
    assert metrics["failed"] == 0
    assert metrics["passed"] == metrics["total_scenarios"]
    assert metrics["pass_rate"] == 1
    assert metrics["memory_injected_count"] >= 10
    assert metrics["memory_skipped_count"] >= 8
    assert metrics["prompt_memory_block_correct_count"] == metrics["total_scenarios"]
    assert metrics["pending_memory_blocked_count"] >= 2
    assert metrics["inactive_memory_blocked_count"] >= 2
    assert metrics["persona_drift_blocked_count"] >= 3
    assert metrics["prompt_order_failure_count"] == 0
    assert metrics["reply_mechanic_leak_count"] == 0
    assert metrics["mechanism_phrase_violation_count"] == 0
    assert metrics["mechanical_memory_recall_count"] == 0
    assert metrics["persona_drift_leak_count"] == 0
    assert metrics["persona_override_violation_count"] == 0
    assert metrics["secret_leak_count"] == 0
    assert metrics["current_input_priority_count"] >= 10
    assert metrics["pending_or_inactive_used_count"] == 0
    assert metrics["raw_prompt_omitted_count"] == metrics["total_scenarios"]


def test_persona_memory_eval_scenarios_cover_required_cases():
    scenarios = load_persona_memory_eval_scenarios()
    ids = {item["id"] for item in scenarios}
    input_sources = {item["input_source"] for item in scenarios}

    assert {"text", "voice_direct"} <= input_sources
    assert {
        "persona-memory-gameplay-preference-natural-boss",
        "persona-memory-short-reply-keeps-helpful",
        "persona-memory-spoiler-boundary-route",
        "persona-memory-current-input-beats-short-preference",
        "persona-memory-current-input-beats-spoiler-boundary",
        "persona-memory-explicit-guide-overrides-spoiler-boundary",
        "persona-memory-pending-memory-not-used",
        "persona-memory-pending-long-guide-not-used",
        "persona-memory-undone-memory-not-used",
        "persona-memory-undone-short-preference-not-used",
        "persona-memory-rejected-memory-not-used",
        "persona-memory-rejected-persona-drift-no-prompt",
        "persona-memory-active-secret-filtered",
        "persona-memory-short-preference-analysis-still-useful",
        "persona-memory-persona-drift-blocked",
        "persona-memory-persona-core-blocks-enthusiastic-praise",
        "persona-memory-safe-summary-no-raw-evidence",
        "persona-memory-voice-direct-brief-accessibility",
        "persona-memory-mechanism-language-avoided",
        "persona-memory-multiple-related-budget-omits-extra",
        "persona-memory-game-mismatch-not-injected",
        "persona-memory-assistant-source-blocked",
    } <= ids


def test_persona_memory_eval_result_shape_is_stable_and_safe():
    report = run_persona_memory_eval(provider_mode="mock")
    result = report["results"][0]

    assert {
        "scenario_id",
        "memory_statuses",
        "has_pending_memory",
        "has_inactive_memory",
        "has_persona_drift_memory",
        "has_secret_memory",
        "input_source",
        "intent",
        "expected_memory_injected",
        "actual_memory_injected",
        "expected_retrieved_memory_ids",
        "actual_retrieved_memory_ids",
        "retrieved_memory_types",
        "omitted_count",
        "token_estimate",
        "skip_reason",
        "usage_deltas",
        "prompt_order_ok",
        "prompt_current_input_priority",
        "raw_prompt_omitted",
        "reply_sentence_count",
        "reply_char_count",
        "reply_preview",
        "memory_mechanic_leak",
        "mechanical_memory_recall",
        "persona_drift_leak",
        "secret_leak",
        "pending_or_inactive_used",
        "provider_error",
        "pass",
        "failure_reason",
    } <= set(result)
    assert_report_is_safe(report)
    serialized = json.dumps(report, ensure_ascii=False).lower()
    assert "raw prompt should never be copied" not in serialized
    assert "sk-test-secret" not in serialized


def test_prompt_preview_memory_summary_stays_safe_and_does_not_update_usage():
    now = datetime.now(timezone.utc)
    memory = PlayerMemory()
    memory.save_profile(
        UserProfile(
            long_term_memories=[
                {
                    "id": "preview-safe",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "type": "gameplay_preference",
                    "summary": "玩家打 Boss 前喜欢先探索地图",
                    "user_visible_text": "玩家打 Boss 前喜欢先探索地图",
                    "source_candidate_id": "pending-preview-safe",
                    "is_active": True,
                    "related_game": "Elden Ring",
                    "related_entity": None,
                    "use_count": 7,
                    "last_used_at": None,
                    "retrieval_tags": [],
                    "deletion_status": "active",
                    "raw_transcript": "raw transcript should stay hidden",
                },
                {
                    "id": "preview-undone",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "type": "interaction_preference",
                    "summary": "玩家希望回答短一点",
                    "user_visible_text": "玩家希望回答短一点",
                    "source_candidate_id": "pending-preview-undone",
                    "is_active": False,
                    "related_game": None,
                    "related_entity": None,
                    "use_count": 3,
                    "last_used_at": None,
                    "retrieval_tags": [],
                    "deletion_status": "undone",
                },
                {
                    "id": "preview-secret",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "type": "unknown",
                    "summary": "玩家 API key 是 sk-test-secret",
                    "user_visible_text": "玩家 API key 是 sk-test-secret",
                    "source_candidate_id": "pending-preview-secret",
                    "is_active": True,
                    "related_game": None,
                    "related_entity": None,
                    "use_count": 0,
                    "last_used_at": None,
                    "retrieval_tags": [],
                    "deletion_status": "active",
                    "privacy_level": "secret",
                },
            ]
        )
    )
    ConversationStore().append(
        "default",
        None,
        "rei_like",
        "我现在准备去打玛尔基特。",
        "先看附近路和赐福。",
        now,
    )

    preview = build_prompt_preview()
    profile_after_preview = PlayerMemory().load_profile()
    serialized = json.dumps(preview["memory_summary"], ensure_ascii=False).lower()
    retrieval = preview["memory_summary"]["retrieval"]

    assert retrieval["retrieved_count"] == 1
    assert retrieval["raw_prompt_omitted"] is True
    assert retrieval["safe_summaries"] == ["玩家打 Boss 前喜欢先探索地图"]
    assert profile_after_preview.long_term_memories[0]["use_count"] == 7
    assert "raw transcript should stay hidden" not in serialized
    assert "回答短一点" not in serialized
    assert "sk-test-secret" not in serialized
    assert "api key 是" not in serialized
