from app.modules.dialogue_agent.extraction_eval import (
    load_extraction_eval_scenarios,
    run_extraction_eval,
)


def test_extraction_eval_runner_mock_scenarios_pass():
    report = run_extraction_eval(provider_mode="mock")
    metrics = report["metrics"]

    assert metrics["total_scenarios"] >= 15
    assert metrics["failed"] == 0
    assert metrics["passed"] == metrics["total_scenarios"]
    assert metrics["pass_rate"] == 1
    assert metrics["llm_primary_success_count"] >= 12
    assert metrics["schema_valid_count"] >= 12
    assert metrics["invalid_json_count"] >= 1
    assert metrics["schema_invalid_count"] >= 1
    assert metrics["fallback_to_rule_count"] >= 1
    assert metrics["compat_retry_used_count"] >= 3
    assert metrics["ultra_compact_used_count"] >= 2
    assert metrics["wrong_apply_count"] == 0
    assert metrics["missed_apply_count"] == 0
    assert metrics["candidate_only_correct_count"] >= 2


def test_extraction_eval_scenarios_cover_required_input_sources_and_cases():
    scenarios = load_extraction_eval_scenarios()
    ids = {item["id"] for item in scenarios}
    input_sources = {item["input_source"] for item in scenarios}

    assert {"text", "voice_confirmed", "voice_direct"} <= input_sources
    assert {
        "extraction-eval-text-boss-set-margit",
        "extraction-eval-text-boss-switch-to-margit",
        "extraction-eval-text-negation-switch-to-malenia",
        "extraction-eval-text-guide-only-margit-no-switch",
        "extraction-eval-text-death-absolute-three",
        "extraction-eval-text-death-increment-two",
        "extraction-eval-text-death-not-cleared-tree-sentinel",
        "extraction-eval-text-boss-cleared-malenia",
        "extraction-eval-memory-intent-boundary",
        "extraction-eval-negative-memory-no-pending",
        "extraction-eval-voice-confirmed-margit-asr-variant",
        "extraction-eval-voice-direct-negation-switch-to-malenia",
        "extraction-eval-voice-direct-uncertain-guide-candidate-only",
        "extraction-eval-invalid-json-rule-fallback",
        "extraction-eval-schema-invalid-no-op",
        "extraction-eval-compat-retry-success",
        "extraction-eval-ultra-compact-retry-success",
        "extraction-eval-descriptive-failure-current-context-applies",
        "extraction-eval-uncertain-confirmation-keeps-candidate",
        "extraction-eval-weak-confirmation-keeps-candidate",
        "extraction-eval-clear-confirm-trace-only",
        "extraction-eval-correction-replaces-old-candidate",
        "extraction-eval-harmless-game-context-not-risky",
    } <= ids


def test_extraction_eval_result_shape_is_stable_and_safe():
    report = run_extraction_eval(provider_mode="mock")
    result = report["results"][0]

    assert {
        "scenario_id",
        "input_text",
        "input_source",
        "expected_decision",
        "actual_decision",
        "expected_applied_updates",
        "actual_applied_updates",
        "expected_state",
        "actual_state",
        "expected_state_delta",
        "actual_state_delta",
        "primary_extractor",
        "primary_status",
        "provider_status",
        "schema_valid",
        "invalid_json",
        "schema_invalid",
        "compat_retry_used",
        "compat_retry_succeeded",
        "ultra_compact_used",
        "fallback_extractor",
        "applied_by",
        "candidate_boss",
        "candidate_event",
        "candidate_confidence",
        "candidate_reason",
        "needs_confirmation",
        "guide_entity",
        "confirmation_intent",
        "risky_state_delta",
        "harmless_state_delta",
        "parse_diagnostic",
        "pass",
        "failure_reason",
    } <= set(result)
    serialized = str(report).lower()
    assert "api_key" not in serialized
    assert ".env" not in serialized
    assert "raw prompt" not in serialized
