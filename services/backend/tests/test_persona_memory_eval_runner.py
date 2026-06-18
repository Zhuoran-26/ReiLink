import json

from app.modules.dialogue_agent.persona_memory_eval import (
    assert_report_is_safe,
    load_persona_memory_eval_scenarios,
    run_persona_memory_eval,
)


def test_persona_memory_eval_runner_mock_scenarios_pass():
    report = run_persona_memory_eval(provider_mode="mock")
    metrics = report["metrics"]

    assert metrics["total_scenarios"] >= 10
    assert metrics["failed"] == 0
    assert metrics["passed"] == metrics["total_scenarios"]
    assert metrics["pass_rate"] == 1
    assert metrics["memory_injected_count"] >= 6
    assert metrics["memory_skipped_count"] >= 3
    assert metrics["prompt_order_failure_count"] == 0
    assert metrics["reply_mechanic_leak_count"] == 0
    assert metrics["persona_drift_leak_count"] == 0
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
        "persona-memory-pending-memory-not-used",
        "persona-memory-undone-memory-not-used",
        "persona-memory-rejected-memory-not-used",
        "persona-memory-persona-drift-blocked",
        "persona-memory-safe-summary-no-raw-evidence",
        "persona-memory-voice-direct-brief-accessibility",
        "persona-memory-mechanism-language-avoided",
    } <= ids


def test_persona_memory_eval_result_shape_is_stable_and_safe():
    report = run_persona_memory_eval(provider_mode="mock")
    result = report["results"][0]

    assert {
        "scenario_id",
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
        "persona_drift_leak",
        "pending_or_inactive_used",
        "provider_error",
        "pass",
        "failure_reason",
    } <= set(result)
    assert_report_is_safe(report)
    serialized = json.dumps(report, ensure_ascii=False).lower()
    assert "raw prompt should never be copied" not in serialized
    assert "sk-test-secret" not in serialized
