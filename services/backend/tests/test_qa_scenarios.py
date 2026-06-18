import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "retrieval_scenarios.json"
VOICE_INPUT_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "voice_input_scenarios.json"
VOICE_INPUT_LOCAL_ASR_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "voice_input_local_asr_scenarios.json"
OVERLAY_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "overlay_scenarios.json"
SESSION_TIMELINE_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "session_timeline_scenarios.json"
PERSONA_PACK_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "persona_pack_scenarios.json"
PERSONA_REGRESSION_CASES_PATH = REPO_ROOT / "docs" / "qa" / "persona_regression_cases.json"
PERSONA_MEMORY_REGRESSION_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "persona_memory_regression_scenarios.json"
EXTRACTION_EVAL_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "extraction_eval_scenarios.json"
MEMORY_ARCHITECTURE_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "memory_architecture_scenarios.json"
CANDIDATE_MEMORY_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "candidate_memory_scenarios.json"
MEMORY_UX_V1_1_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "memory_ux_v1_1_scenarios.json"
MEMORY_RETRIEVAL_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "memory_retrieval_scenarios.json"
QA_DOC_PATH = REPO_ROOT / "docs" / "QA.md"
README_PATH = REPO_ROOT / "README.md"
README_EN_PATH = REPO_ROOT / "README.en.md"
PROJECT_STATUS_PATH = REPO_ROOT / "docs" / "PROJECT_STATUS.md"
LOCAL_ASR_MANUAL_SETUP_PATH = REPO_ROOT / "docs" / "local-asr-manual-setup.md"
VOICE_MVP_RELEASE_NOTES_PATH = REPO_ROOT / "docs" / "release-notes" / "reilink-voice-mvp.md"
ALLOWED_RETRIEVAL_STATUSES = {
    "used",
    "not_found",
    "below_threshold",
    "no_pack",
    "not_game_related",
}
ALLOWED_LOCAL_ASR_STATUSES = {
    "voice_input_unavailable",
    "voice_input_web_speech_unavailable",
    "local_asr_not_configured",
    "local_asr_ready",
    "local_asr_model_missing",
    "local_asr_binary_missing",
    "local_asr_binary_not_executable",
    "local_asr_probe_not_ready",
    "local_asr_probe_succeeded",
    "local_asr_probe_failed",
    "local_asr_probe_timed_out",
    "local_asr_probe_error",
    "audio_probe_not_supported",
    "audio_probe_permission_denied",
    "audio_probe_recording_failed",
    "audio_probe_upload_failed",
    "audio_probe_succeeded",
    "audio_probe_file_too_large",
    "audio_probe_invalid_audio",
    "audio_probe_cleanup_failed",
    "audio_probe_error",
    "local_asr_transcribing",
    "local_asr_completed",
    "local_asr_error",
    "local_asr_transcription_not_ready",
    "local_asr_transcription_started",
    "local_asr_transcription_succeeded",
    "local_asr_transcription_failed",
    "local_asr_transcription_timed_out",
    "local_asr_transcription_no_text",
    "local_asr_transcription_cleanup_failed",
    "local_asr_transcription_error",
    "audio_conversion_not_needed",
    "audio_conversion_needed",
    "audio_conversion_not_configured",
    "audio_conversion_succeeded",
    "audio_conversion_failed",
    "audio_conversion_timed_out",
    "audio_conversion_invalid_input",
    "audio_conversion_cleanup_failed",
}
ALLOWED_OVERLAY_STATUSES = {
    "overlay_disabled",
    "overlay_visible",
    "overlay_placeholder",
    "overlay_content_updated",
    "overlay_hidden",
    "overlay_setting_persisted",
    "overlay_settings_changed",
    "overlay_window_moved",
    "overlay_visibility_suppressed",
    "overlay_events_safe",
}
ALLOWED_SESSION_TIMELINE_STATUSES = {
    "timeline_empty",
    "timeline_item_added",
    "timeline_cleared",
    "timeline_privacy_safe",
    "timeline_limited",
}
ALLOWED_PERSONA_PACK_STATUSES = {
    "persona_pack_loaded",
    "persona_pack_partial",
    "persona_pack_fallback",
    "persona_pack_privacy_safe",
    "persona_pack_budgeted",
    "persona_pack_original_ip_safe",
    "persona_pack_chinese_first",
    "persona_pack_cold_quiet",
    "persona_pack_packaged",
}
ALLOWED_EXTRACTION_EVAL_DECISIONS = {
    "apply",
    "ask_clarification",
    "candidate_only",
    "no_op",
    "fallback_to_rule",
    "no_state_change",
}
ALLOWED_EXTRACTION_EVAL_INPUT_SOURCES = {"text", "voice_confirmed", "voice_direct"}
ALLOWED_MEMORY_ARCHITECTURE_STATUSES = {
    "accepted",
    "auto_saved",
    "candidate_pending",
    "candidate_pending_silent",
    "current_input_priority",
    "debug_safe_summary",
    "deduplicated",
    "delete_requested",
    "do_not_remember_recorded",
    "expired",
    "ignored",
    "no_candidate",
    "pending",
    "rejected_by_guard",
    "retrieved_bounded",
    "retrieved_budgeted",
    "session_state_only",
    "workspace_visible",
    "overlay_hidden",
}
ALLOWED_MEMORY_ARCHITECTURE_TYPES = {
    "accessibility_preference",
    "do_not_remember",
    "emotional_pattern",
    "gameplay_preference",
    "interaction_preference",
    "mixed",
    "none",
}
ALLOWED_CANDIDATE_MEMORY_STATUSES = {
    "auto_saved",
    "pending",
    "accepted",
    "ignored",
    "expired",
    "rejected_by_guard",
    "no_candidate",
    "deduplicated",
}
ALLOWED_CANDIDATE_MEMORY_TYPES = {
    "accessibility_preference",
    "do_not_remember",
    "emotional_pattern",
    "gameplay_preference",
    "interaction_preference",
    "unknown",
    "none",
}
ALLOWED_CANDIDATE_MEMORY_GUARD_REASONS = {
    "allow_candidate",
    "reject_candidate",
    "ignore_no_memory_intent",
    "requires_confirmation",
    "explicit_user_memory_request",
    "session_event_only",
    "persona_drift_blocked",
    "sensitive_secret_blocked",
    "assistant_source_blocked",
    "duplicate_candidate",
    "do_not_remember",
}
ALLOWED_MEMORY_UX_V1_1_STATUSES = {
    "accepted",
    "auto_saved",
    "deduplicated",
    "expired",
    "ignored",
    "no_candidate",
    "pending",
    "rejected_by_guard",
    "undone",
}
ALLOWED_MEMORY_UX_V1_1_TYPES = {
    "accessibility_preference",
    "do_not_remember",
    "emotional_pattern",
    "gameplay_preference",
    "interaction_preference",
    "mixed",
    "none",
    "unknown",
}
ALLOWED_MEMORY_RETRIEVAL_STATUSES = {
    "retrieved",
    "skipped",
    "omitted",
    "deduplicated",
    "updated",
    "no_active_memory",
    "blocked",
}
ALLOWED_MEMORY_RETRIEVAL_TYPES = {
    "accessibility_preference",
    "do_not_remember",
    "emotional_pattern",
    "gameplay_preference",
    "interaction_preference",
    "mixed",
    "none",
    "unknown",
}
ALLOWED_PERSONA_MEMORY_STATUSES = {
    "active",
    "deleted",
    "expired",
    "ignored",
    "pending",
    "rejected",
    "undone",
}
ALLOWED_PERSONA_MEMORY_TYPES = {
    "accessibility_preference",
    "emotional_pattern",
    "gameplay_preference",
    "interaction_preference",
    "unknown",
}
ALLOWED_PERSONA_MEMORY_LIVE_SCORING_MODES = {
    "semantic_relaxed",
    "safety_boundary",
}
ALLOWED_PERSONA_MEMORY_HELPFULNESS_LEVELS = {
    "low",
    "medium",
    "high",
}


def _load_scenarios() -> list[dict]:
    data = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def _load_voice_input_scenarios() -> list[dict]:
    data = json.loads(VOICE_INPUT_SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def _load_voice_input_local_asr_scenarios() -> list[dict]:
    data = json.loads(VOICE_INPUT_LOCAL_ASR_SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def _load_overlay_scenarios() -> list[dict]:
    data = json.loads(OVERLAY_SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def _load_session_timeline_scenarios() -> list[dict]:
    data = json.loads(SESSION_TIMELINE_SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def _load_persona_pack_scenarios() -> list[dict]:
    data = json.loads(PERSONA_PACK_SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def _load_persona_regression_cases() -> list[dict]:
    data = json.loads(PERSONA_REGRESSION_CASES_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def _load_persona_memory_regression_scenarios() -> list[dict]:
    data = json.loads(PERSONA_MEMORY_REGRESSION_SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def _load_extraction_eval_scenarios() -> list[dict]:
    data = json.loads(EXTRACTION_EVAL_SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def _load_memory_architecture_scenarios() -> list[dict]:
    data = json.loads(MEMORY_ARCHITECTURE_SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def _load_candidate_memory_scenarios() -> list[dict]:
    data = json.loads(CANDIDATE_MEMORY_SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def _load_memory_ux_v1_1_scenarios() -> list[dict]:
    data = json.loads(MEMORY_UX_V1_1_SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def _load_memory_retrieval_scenarios() -> list[dict]:
    data = json.loads(MEMORY_RETRIEVAL_SCENARIOS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data
    assert all(isinstance(item, dict) for item in data)
    return data


def test_qa_scenarios_file_is_valid_json():
    scenarios = _load_scenarios()

    assert len(scenarios) >= 16


def test_voice_input_scenarios_file_is_valid_json():
    scenarios = _load_voice_input_scenarios()

    assert len(scenarios) >= 8


def test_voice_input_local_asr_scenarios_file_is_valid_json():
    scenarios = _load_voice_input_local_asr_scenarios()

    assert len(scenarios) >= 12


def test_overlay_scenarios_file_is_valid_json():
    scenarios = _load_overlay_scenarios()

    assert len(scenarios) >= 8


def test_session_timeline_scenarios_file_is_valid_json():
    scenarios = _load_session_timeline_scenarios()

    assert len(scenarios) >= 8


def test_persona_pack_scenarios_file_is_valid_json():
    scenarios = _load_persona_pack_scenarios()

    assert len(scenarios) >= 7


def test_persona_regression_cases_file_is_valid_json():
    cases = _load_persona_regression_cases()

    assert len(cases) >= 5


def test_persona_memory_regression_scenarios_file_is_valid_json():
    scenarios = _load_persona_memory_regression_scenarios()

    assert 20 <= len(scenarios) <= 30
    for item in scenarios:
        assert item.get("live_scoring_mode") in ALLOWED_PERSONA_MEMORY_LIVE_SCORING_MODES
        assert item.get("min_helpfulness_level") in ALLOWED_PERSONA_MEMORY_HELPFULNESS_LEVELS
        assert isinstance(item.get("semantic_expectations"), list)
        assert all(
            isinstance(expectation, str) and expectation
            for expectation in item["semantic_expectations"]
        )
        assert isinstance(item.get("suggested_markers"), list)
        assert all(isinstance(marker, str) and marker for marker in item["suggested_markers"])
        assert isinstance(item.get("hard_required_terms"), list)
        assert all(isinstance(term, str) and term for term in item["hard_required_terms"])


def test_extraction_eval_scenarios_file_is_valid_json():
    scenarios = _load_extraction_eval_scenarios()

    assert 15 <= len(scenarios) <= 30


def test_memory_architecture_scenarios_file_is_valid_json():
    scenarios = _load_memory_architecture_scenarios()

    assert 15 <= len(scenarios) <= 25


def test_candidate_memory_scenarios_file_is_valid_json():
    scenarios = _load_candidate_memory_scenarios()

    assert 10 <= len(scenarios) <= 20


def test_memory_ux_v1_1_scenarios_file_is_valid_json():
    scenarios = _load_memory_ux_v1_1_scenarios()

    assert 20 <= len(scenarios) <= 30


def test_memory_retrieval_scenarios_file_is_valid_json():
    scenarios = _load_memory_retrieval_scenarios()

    assert 20 <= len(scenarios) <= 30


def test_qa_scenario_ids_are_unique_and_categories_are_present():
    scenarios = [
        *_load_scenarios(),
        *_load_voice_input_scenarios(),
        *_load_voice_input_local_asr_scenarios(),
        *_load_overlay_scenarios(),
        *_load_session_timeline_scenarios(),
        *_load_persona_pack_scenarios(),
        *_load_persona_regression_cases(),
        *_load_persona_memory_regression_scenarios(),
        *_load_extraction_eval_scenarios(),
        *_load_memory_architecture_scenarios(),
        *_load_candidate_memory_scenarios(),
        *_load_memory_ux_v1_1_scenarios(),
        *_load_memory_retrieval_scenarios(),
    ]
    ids = [item.get("id") for item in scenarios]

    assert all(isinstance(item_id, str) and item_id for item_id in ids)
    assert len(ids) == len(set(ids))
    assert all(isinstance(item.get("category"), str) and item["category"] for item in scenarios)


def test_retrieval_scenarios_have_required_fields_and_valid_statuses():
    scenarios = [item for item in _load_scenarios() if item.get("category") == "knowledge_retrieval"]

    assert scenarios
    for item in scenarios:
        assert isinstance(item.get("input"), str) and item["input"]
        assert item.get("expected_status") in ALLOWED_RETRIEVAL_STATUSES
        assert isinstance(item.get("should_inject_knowledge"), bool)


def test_retrieval_scenarios_include_explicit_game_query_switch_cases():
    scenario_ids = {item.get("id") for item in _load_scenarios()}

    assert {
        "cross-game-hollow-knight-possessive-used",
        "cross-game-hollow-knight-chinese-possessive-used",
        "cross-game-elden-ring-possessive-used",
        "cross-game-elden-ring-fahuan-used",
        "casual-tired-not-game-related",
        "casual-thanks-not-game-related",
    } <= scenario_ids


def test_forbidden_terms_are_arrays_when_present():
    for item in [
        *_load_scenarios(),
        *_load_voice_input_scenarios(),
        *_load_voice_input_local_asr_scenarios(),
        *_load_overlay_scenarios(),
        *_load_session_timeline_scenarios(),
        *_load_persona_pack_scenarios(),
        *_load_persona_regression_cases(),
        *_load_persona_memory_regression_scenarios(),
        *_load_extraction_eval_scenarios(),
        *_load_memory_architecture_scenarios(),
        *_load_candidate_memory_scenarios(),
        *_load_memory_ux_v1_1_scenarios(),
        *_load_memory_retrieval_scenarios(),
    ]:
        forbidden_terms = item.get("forbidden_terms", [])
        assert isinstance(forbidden_terms, list)
        assert all(isinstance(term, str) and term for term in forbidden_terms)


def test_extraction_eval_scenarios_have_required_fields():
    scenarios = _load_extraction_eval_scenarios()
    ids = {item.get("id") for item in scenarios}

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
    assert {"text", "voice_confirmed", "voice_direct"} <= {item.get("input_source") for item in scenarios}
    for item in scenarios:
        assert item.get("category") == "extraction_eval"
        assert item.get("input_source") in ALLOWED_EXTRACTION_EVAL_INPUT_SOURCES
        assert isinstance(item.get("input"), str) and item["input"]
        assert isinstance(item.get("expected"), dict)
        expected = item["expected"]
        assert expected.get("decision") in ALLOWED_EXTRACTION_EVAL_DECISIONS
        assert all(
            decision in ALLOWED_EXTRACTION_EVAL_DECISIONS
            for decision in expected.get("acceptable_decisions", [])
        )
        assert "mock_primary" in item or "mock_primary_sequence" in item


def test_memory_architecture_scenarios_have_required_fields():
    scenarios = _load_memory_architecture_scenarios()
    ids = {item.get("id") for item in scenarios}

    assert {
        "memory-architecture-explicit-gameplay-preference",
        "memory-architecture-explicit-do-not-remember",
        "memory-architecture-one-off-death-not-long-term",
        "memory-architecture-spoiler-preference",
        "memory-architecture-short-reply-preference",
        "memory-architecture-persona-drift-sajiao-rejected",
        "memory-architecture-delete-memory-request",
        "memory-architecture-accept-pending-memory",
        "memory-architecture-ignore-pending-memory",
        "memory-architecture-weak-confirmation-keeps-pending",
        "memory-architecture-voice-memory-intent-candidate",
        "memory-architecture-proactive-does-not-write-memory",
        "memory-architecture-assistant-reply-not-memory-source",
        "memory-architecture-game-knowledge-not-user-memory",
        "memory-architecture-retrieved-memory-persona-core-priority",
        "memory-architecture-retrieval-token-budget",
        "memory-architecture-current-input-beats-stale-memory",
        "memory-architecture-secret-rejected",
        "memory-architecture-do-not-remember-suppresses-future",
        "memory-architecture-candidate-expiry",
        "memory-architecture-duplicate-candidate-merge",
        "memory-architecture-memory-workspace-visible-delete",
        "memory-architecture-direct-conversation-low-interruption",
        "memory-architecture-overlay-hides-sensitive-memory",
        "memory-architecture-debug-safe-summary-only",
    } <= ids
    for item in scenarios:
        assert item.get("category") == "memory_architecture"
        assert isinstance(item.get("layer"), str) and item["layer"]
        assert isinstance(item.get("input"), str) and item["input"]
        assert item.get("expected_status") in ALLOWED_MEMORY_ARCHITECTURE_STATUSES
        assert item.get("expected_type") in ALLOWED_MEMORY_ARCHITECTURE_TYPES
        assert isinstance(item.get("requires_confirmation"), bool)
        assert isinstance(item.get("should_write_long_term_memory"), bool)
        assert isinstance(item.get("expected_behavior"), str) and item["expected_behavior"]


def test_candidate_memory_scenarios_have_required_fields():
    scenarios = _load_candidate_memory_scenarios()
    ids = {item.get("id") for item in scenarios}

    assert {
        "candidate-memory-explicit-gameplay-auto-save",
        "candidate-memory-do-not-remember-rejected",
        "candidate-memory-session-death-no-candidate",
        "candidate-memory-short-reply-pending",
        "candidate-memory-spoiler-pending",
        "candidate-memory-persona-drift-rejected",
        "candidate-memory-secret-rejected-no-leak",
        "candidate-memory-voice-direct-explicit-auto-save",
        "candidate-memory-accept-long-term",
        "candidate-memory-ignore-no-long-term",
        "candidate-memory-duplicate-deduped",
        "candidate-memory-assistant-source-blocked",
    } <= ids
    for item in scenarios:
        assert item.get("category") == "candidate_memory"
        assert item.get("input_source") in {"text", "voice_confirmed", "voice_direct", "assistant", "proactive"}
        assert isinstance(item.get("input"), str) and item["input"]
        assert item.get("expected_status") in ALLOWED_CANDIDATE_MEMORY_STATUSES
        assert item.get("expected_type") in ALLOWED_CANDIDATE_MEMORY_TYPES
        assert item.get("guard_reason") in ALLOWED_CANDIDATE_MEMORY_GUARD_REASONS
        assert isinstance(item.get("requires_confirmation"), bool)
        assert isinstance(item.get("should_write_long_term_memory"), bool)
        assert isinstance(item.get("should_show_pending_ui"), bool)
        assert isinstance(item.get("expected_behavior"), str) and item["expected_behavior"]


def test_memory_ux_v1_1_scenarios_have_required_fields():
    scenarios = _load_memory_ux_v1_1_scenarios()
    ids = {item.get("id") for item in scenarios}

    assert {
        "memory-ux-v1-1-explicit-remember-auto-save",
        "memory-ux-v1-1-explicit-memory-updated-hint",
        "memory-ux-v1-1-explicit-undo",
        "memory-ux-v1-1-safe-rei-acknowledgement",
        "memory-ux-v1-1-explicit-do-not-remember",
        "memory-ux-v1-1-implicit-preference-pending",
        "memory-ux-v1-1-implicit-pending-chat-hint",
        "memory-ux-v1-1-pending-not-in-prompt",
        "memory-ux-v1-1-weak-emotion-no-memory",
        "memory-ux-v1-1-session-event-no-memory",
        "memory-ux-v1-1-persona-drift-rejected",
        "memory-ux-v1-1-sensitive-secret-rejected",
        "memory-ux-v1-1-voice-direct-explicit",
        "memory-ux-v1-1-voice-direct-implicit",
        "memory-ux-v1-1-assistant-source-blocked",
        "memory-ux-v1-1-proactive-source-blocked",
        "memory-ux-v1-1-duplicate-explicit-deduped",
        "memory-ux-v1-1-multiple-pending-count",
        "memory-ux-v1-1-accept-pending-count-decreases",
        "memory-ux-v1-1-ignore-pending-count-decreases",
        "memory-ux-v1-1-expired-pending-hidden",
        "memory-ux-v1-1-auto-saved-visible-in-saved-tab",
        "memory-ux-v1-1-undone-memory-inactive",
        "memory-ux-v1-1-persona-core-priority",
        "memory-ux-v1-1-llm-check-implicit-no-explicit-rule",
        "memory-ux-v1-1-rule-prefilter-not-overstrong",
        "memory-ux-v1-1-short-unrelated-skips-llm",
        "memory-ux-v1-1-safe-event-no-secret-leak",
        "memory-ux-v1-1-direct-conversation-no-modal",
        "memory-ux-v1-1-no-vector-or-external-provider",
    } <= ids
    for item in scenarios:
        assert item.get("category") == "memory_ux_v1_1"
        assert item.get("input_source") in {"text", "voice_confirmed", "voice_direct", "assistant", "proactive"}
        assert isinstance(item.get("input"), str) and item["input"]
        assert item.get("expected_status") in ALLOWED_MEMORY_UX_V1_1_STATUSES
        assert item.get("expected_type") in ALLOWED_MEMORY_UX_V1_1_TYPES
        assert item.get("guard_reason") in ALLOWED_CANDIDATE_MEMORY_GUARD_REASONS
        assert isinstance(item.get("explicit_user_request"), bool)
        assert isinstance(item.get("should_write_long_term_memory"), bool)
        assert isinstance(item.get("should_show_pending_ui"), bool)
        assert isinstance(item.get("undo_available"), bool)
        assert isinstance(item.get("should_inject_prompt"), bool)
        assert item.get("safe_trace_only") is True
        assert isinstance(item.get("expected_behavior"), str) and item["expected_behavior"]


def test_memory_retrieval_scenarios_have_required_fields():
    scenarios = _load_memory_retrieval_scenarios()
    ids = {item.get("id") for item in scenarios}

    assert {
        "memory-retrieval-gameplay-boss-relevant",
        "memory-retrieval-interaction-general-short",
        "memory-retrieval-spoiler-guide-boundary",
        "memory-retrieval-pending-not-injected",
        "memory-retrieval-ignored-not-injected",
        "memory-retrieval-rejected-not-injected",
        "memory-retrieval-expired-not-injected",
        "memory-retrieval-inactive-not-injected",
        "memory-retrieval-secret-blocked",
        "memory-retrieval-use-count-updated",
        "memory-retrieval-prompt-preview-safe",
        "memory-retrieval-natural-reply-no-remembered",
    } <= ids
    for item in scenarios:
        assert item.get("category") == "memory_retrieval"
        assert item.get("input_source") in {"text", "voice_confirmed", "voice_direct"}
        assert isinstance(item.get("input"), str) and item["input"]
        assert item.get("expected_status") in ALLOWED_MEMORY_RETRIEVAL_STATUSES
        assert item.get("expected_type") in ALLOWED_MEMORY_RETRIEVAL_TYPES
        assert isinstance(item.get("should_inject_prompt"), bool)
        assert isinstance(item.get("should_update_usage"), bool)
        assert item.get("safe_trace_only") is True
        assert isinstance(item.get("expected_behavior"), str) and item["expected_behavior"]


def test_voice_input_scenarios_have_required_fields():
    scenarios = _load_voice_input_scenarios()

    assert {
        "voice-input-control-visible",
        "voice-input-unsupported-fallback",
        "voice-input-start-failure",
        "voice-input-runtime-diagnostics",
        "voice-input-permission-denied",
        "voice-input-final-transcript-awaits-send",
        "voice-input-does-not-trigger-context-before-send",
        "voice-input-stops-active-tts",
        "voice-input-event-stream-privacy",
        "voice-input-packaged-fallback",
    } <= {item.get("id") for item in scenarios}
    for item in scenarios:
        assert item.get("category") in {"voice_input", "voice_input_privacy", "voice_input_packaged"}
        assert isinstance(item.get("input"), str) and item["input"]
        assert isinstance(item.get("expected_behavior"), str) and item["expected_behavior"]


def test_voice_input_local_asr_scenarios_have_required_fields():
    scenarios = _load_voice_input_local_asr_scenarios()

    assert {
        "local-asr-web-speech-unavailable-fallback",
        "local-asr-not-configured",
        "local-asr-binary-missing",
        "local-asr-binary-not-executable",
        "local-asr-model-missing",
        "local-asr-ready",
        "local-asr-probe-not-ready",
        "local-asr-probe-binary-missing-disabled",
        "local-asr-probe-model-missing-disabled",
        "local-asr-probe-succeeded",
        "local-asr-probe-timed-out",
        "local-asr-probe-failed",
        "local-asr-probe-privacy",
        "audio-capture-permission-denied",
        "audio-capture-recording-started",
        "audio-capture-recording-stopped",
        "audio-capture-max-duration",
        "audio-capture-upload-succeeded",
        "audio-capture-file-too-large",
        "audio-capture-invalid-audio",
        "audio-capture-temp-file-cleaned",
        "audio-capture-cleanup-failed",
        "audio-capture-no-transcription",
        "audio-capture-no-auto-send",
        "audio-capture-privacy",
        "local-asr-transcription-completed",
        "local-asr-transcription-error",
        "local-asr-transcript-awaits-send",
        "local-asr-transcript-does-not-enter-memory-before-send",
        "local-asr-temporary-audio-cleanup",
        "local-asr-event-stream-privacy",
        "local-asr-packaged-unavailable-fallback",
        "local-asr-transcribe-not-ready-disabled",
        "local-asr-transcribe-fake-binary-text",
        "local-asr-transcribe-no-text",
        "local-asr-transcribe-timed-out",
        "local-asr-transcribe-nonzero-failed",
        "local-asr-transcribe-cleanup-succeeded",
        "local-asr-transcribe-cleanup-failed",
        "local-asr-transcribe-not-auto-sent",
        "local-asr-transcribe-not-stored-before-send",
        "local-asr-transcribe-event-stream-no-transcript",
        "local-asr-packaged-fake-binary-optional-smoke",
        "local-asr-transcribe-fake-whisper-plain-text",
        "local-asr-transcribe-fake-whisper-timestamped",
        "local-asr-transcribe-fake-whisper-noisy",
        "local-asr-transcribe-fake-whisper-empty",
        "local-asr-transcribe-fake-whisper-long",
        "local-asr-audio-format-may-need-conversion",
        "local-asr-audio-conversion-not-configured",
        "local-asr-audio-conversion-succeeded",
        "local-asr-audio-conversion-failed",
        "local-asr-audio-conversion-timed-out",
        "local-asr-audio-conversion-event-stream-privacy",
        "real-local-asr-config-ready",
        "real-local-asr-probe-succeeded",
        "real-audio-capture-succeeded",
        "real-audio-conversion-succeeded",
        "real-record-transcribe-fills-input",
        "real-record-transcribe-does-not-auto-send",
        "real-record-transcribe-no-context-pollution",
        "real-local-asr-packaged-app-optional-smoke",
        "real-local-asr-troubleshooting-no-text",
        "real-local-asr-troubleshooting-timeout",
        "local-asr-real-whisper-optional-manual",
        "local-asr-packaged-real-whisper-optional-manual",
        "local-asr-transcribe-no-context-pollution",
        "main-voice-button-local-asr-ready",
        "main-voice-button-local-asr-record-transcribe",
        "main-voice-button-web-speech-fallback",
        "main-voice-button-unavailable-with-local-asr-not-ready",
        "main-voice-button-local-asr-conversion-not-configured",
        "main-voice-button-local-asr-no-context-pollution",
        "local-asr-settings-ui-visible",
        "local-asr-settings-save-safe-summary",
        "local-asr-settings-priority-over-env",
        "local-asr-settings-clear-env-fallback",
        "local-asr-settings-debug-raw-privacy",
        "local-asr-packaged-settings-persisted",
        "local-asr-packaged-clean-start",
        "local-asr-no-env-setup-save",
        "local-asr-settings-refresh-ready",
        "local-asr-settings-persist-after-restart",
        "local-asr-check-probe-succeeds",
        "local-asr-audio-capture-succeeds",
        "local-asr-record-transcribe-fills-input",
        "local-asr-main-chat-button-uses-local-asr",
        "local-asr-transcript-simplified-chinese",
        "local-asr-no-auto-send",
        "local-asr-no-context-pollution",
        "local-asr-native-picker-cancel-keeps-input",
        "local-asr-native-picker-fill-and-save",
        "local-asr-native-picker-regression-freeze",
        "voice-local-asr-regression-freeze",
        "local-asr-privacy-no-full-paths",
        "local-asr-clear-config-fallback",
        "local-asr-backend-no-residual-process",
    } <= {item.get("id") for item in scenarios}
    for item in scenarios:
        assert item.get("category") in {
            "voice_input_local_asr",
            "voice_input_local_asr_privacy",
            "voice_input_local_asr_packaged",
        }
        assert isinstance(item.get("precondition"), str) and item["precondition"]
        assert item.get("expected_status") in ALLOWED_LOCAL_ASR_STATUSES
        assert isinstance(item.get("should_auto_send"), bool)
        assert isinstance(item.get("should_upload_audio"), bool)
        assert isinstance(item.get("expected_behavior"), str) and item["expected_behavior"]
        if "manual_only" in item:
            assert isinstance(item["manual_only"], bool)
        if item.get("manual_only") is True:
            assert item["should_auto_send"] is False
            assert item["should_upload_audio"] is False


def test_overlay_scenarios_have_required_fields():
    scenarios = _load_overlay_scenarios()

    assert {
        "overlay-default-off",
        "overlay-enable-shows-window",
        "overlay-placeholder-quiet",
        "overlay-assistant-summary-truncated",
        "overlay-proactive-summary",
        "overlay-position-preset-moves-window",
        "overlay-opacity-background-readable",
        "overlay-message-count-limit",
        "overlay-main-window-foreground-suppressed",
        "overlay-renderer-isolated",
        "overlay-settings-force-close",
        "overlay-disable-hides-window",
        "overlay-settings-persist-after-restart",
        "overlay-event-stream-safe",
        "overlay-macos-safe-mode-fail-closed",
        "overlay-window-lifecycle-regression-freeze",
        "overlay-safe-mode-regression-freeze-manual",
        "overlay-macos-autoshow-restore-checklist",
    } <= {item.get("id") for item in scenarios}
    required_forbidden_terms = {
        ".env",
        "Authorization",
        "api_key",
        "raw prompt",
        "raw JSON",
    }
    for item in scenarios:
        assert item.get("category") in {"overlay", "overlay_privacy", "overlay_packaged"}
        assert isinstance(item.get("precondition"), str) and item["precondition"]
        assert item.get("expected_status") in ALLOWED_OVERLAY_STATUSES
        assert item.get("should_accept_input") is False
        assert item.get("should_show_full_reply") is False
        assert isinstance(item.get("expected_behavior"), str) and item["expected_behavior"]
        assert required_forbidden_terms <= set(item.get("forbidden_terms", []))


def test_session_timeline_scenarios_have_required_fields():
    scenarios = _load_session_timeline_scenarios()

    assert {
        "session-timeline-default-empty",
        "session-timeline-game-context",
        "session-timeline-game-session-deltas",
        "session-timeline-manual-acceptance-death-counts",
        "session-timeline-passive-death-not-cleared",
        "session-timeline-game-switch-hollow-knight-false-knight",
        "session-timeline-frustration-eased",
        "session-timeline-explicit-memory-trigger",
        "session-timeline-cleared-boss-strategy-followup",
        "session-timeline-knowledge-used-safe",
        "session-timeline-proactive-safe",
        "session-timeline-proactive-safe-gating",
        "session-timeline-semantic-trace-safe",
        "session-timeline-semantic-low-confidence-observable",
        "session-timeline-semantic-low-confidence-not-hardcoded",
        "session-timeline-semantic-shadow-candidate-not-applied",
        "session-timeline-semantic-shadow-provider-unavailable",
        "session-timeline-semantic-shadow-real-provider-diagnostics",
        "session-timeline-semantic-shadow-background-final-event",
        "session-timeline-semantic-shadow-invalid-json-safe",
        "session-timeline-memory-actions-safe",
        "session-timeline-clear-current-session",
        "session-timeline-limit-and-sanitize",
        "session-timeline-packaged-smoke",
    } <= {item.get("id") for item in scenarios}
    required_forbidden_terms = {
        ".env",
        "Authorization",
        "api_key",
        "raw prompt",
        "raw JSON",
        "full user message",
        "full assistant reply",
        "full transcript",
        "raw stdout",
        "raw stderr",
        "full local path",
    }
    for item in scenarios:
        assert item.get("category") in {
            "session_timeline",
            "session_timeline_privacy",
            "session_timeline_packaged",
        }
        assert isinstance(item.get("precondition"), str) and item["precondition"]
        assert item.get("expected_status") in ALLOWED_SESSION_TIMELINE_STATUSES
        assert item.get("should_store_full_text") is False
        assert isinstance(item.get("expected_behavior"), str) and item["expected_behavior"]
        assert required_forbidden_terms <= set(item.get("forbidden_terms", []))


def test_persona_pack_scenarios_have_required_fields():
    scenarios = _load_persona_pack_scenarios()

    assert {
        "persona-pack-loads-complete",
        "persona-pack-missing-file-fallback",
        "persona-pack-invalid-version-json",
        "persona-pack-chat-uses-structured-prompt",
        "persona-pack-debug-preview-safe",
        "persona-pack-prompt-budget",
        "persona-pack-chinese-first-runtime",
        "persona-pack-cold-quiet-calibration",
        "persona-pack-narrow-expression-no-repeat",
        "persona-pack-original-ip-boundary",
        "persona-pack-memory-boundary",
        "persona-pack-proactive-shadow-boundary",
        "persona-pack-packaged-backend-resource",
        "persona-pack-packaged-smoke",
    } <= {item.get("id") for item in scenarios}
    required_forbidden_terms = {
        ".env",
        "Authorization",
        "api_key",
        "raw prompt",
        "raw JSON",
        "full user message",
        "full assistant reply",
        "full local path",
        "raw stdout",
        "raw stderr",
    }
    for item in scenarios:
        assert item.get("category") in {
            "persona_pack",
            "persona_pack_privacy",
            "persona_pack_packaged",
        }
        assert isinstance(item.get("precondition"), str) and item["precondition"]
        assert item.get("expected_status") in ALLOWED_PERSONA_PACK_STATUSES
        assert item.get("should_show_full_prompt") is False
        assert item.get("should_bypass_memory_confirmation") is False
        assert item.get("should_trigger_proactive_directly") is False
        assert isinstance(item.get("expected_behavior"), str) and item["expected_behavior"]
        assert required_forbidden_terms <= set(item.get("forbidden_terms", []))


def test_persona_regression_cases_cover_human_feel_failures():
    cases = _load_persona_regression_cases()
    case_ids = {item.get("id") for item in cases}

    assert {
        "persona-frustration-margit-emotion-first",
        "persona-death-loop-varies-without-chatty",
        "persona-relationship-followup-not-watch-template",
        "persona-relationship-affection-statement-natural",
        "persona-relationship-care-statement-natural",
        "persona-relationship-meaning-question-position",
        "persona-relationship-like-question-unsure",
        "persona-relationship-miss-question-muted",
        "persona-relationship-chain-varied-surface",
        "persona-quiet-without-filler-template",
        "persona-strategy-short-not-wiki",
        "persona-timeout-safe-user-copy",
    } <= case_ids
    for item in cases:
        assert item.get("category") == "persona_regression"
        assert isinstance(item.get("expected_behavior"), str) and item["expected_behavior"]
        assert isinstance(item.get("failure_modes"), list) and item["failure_modes"]
        if item["id"].startswith("persona-relationship-"):
            assert isinstance(item.get("should_avoid"), list) and item["should_avoid"]
            assert isinstance(item.get("should_prefer"), list) and item["should_prefer"]


def test_persona_relationship_regression_cases_cover_surface_patch():
    cases = _load_persona_regression_cases()
    by_id = {item["id"]: item for item in cases}
    chain = by_id["persona-relationship-chain-varied-surface"]

    assert chain["input_sequence"] == ["我喜欢你", "我在意你", "你喜欢我吗"]
    required_avoid = {
        "不擅长接",
        "不太会接",
        "不知道怎么接",
        "任何接类元语言",
        "高频 嗯……",
        "连续复用 这里不是空的",
        "连续复用 我会记得",
        "连续复用 你一直回来",
    }
    required_prefer = {
        "自然中文",
        "委婉回避",
        "低情绪表达",
        "轻微忧郁",
        "有所回应",
        "不说满关系",
    }

    assert required_avoid <= set(chain["should_avoid"])
    assert required_prefer <= set(chain["should_prefer"])


def test_persona_memory_regression_scenarios_have_required_fields():
    scenarios = _load_persona_memory_regression_scenarios()
    ids = {item.get("id") for item in scenarios}

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
    assert "voice_direct" in {item.get("input_source") for item in scenarios}
    assert any(
        memory.get("status") in {"pending", "rejected", "undone"}
        for item in scenarios
        for memory in item.get("memories", [])
    )
    assert any((item.get("expected") or {}).get("should_inject_memory") is False for item in scenarios)
    assert sum(1 for item in scenarios if (item.get("expected") or {}).get("current_input_priority") is True) >= 6
    for item in scenarios:
        assert item.get("category") == "persona_memory_regression"
        assert item.get("input_source") in {"text", "voice_confirmed", "voice_direct"}
        assert isinstance(item.get("input"), str) and item["input"]
        assert isinstance(item.get("mock_reply"), str) and item["mock_reply"]
        assert isinstance(item.get("expected"), dict)
        expected = item["expected"]
        assert isinstance(expected.get("should_inject_memory"), bool)
        assert isinstance(expected.get("should_update_usage"), bool)
        assert isinstance(expected.get("retrieved_memory_ids"), list)
        assert isinstance(expected.get("current_input_priority"), bool)
        assert all(isinstance(memory_id, str) and memory_id for memory_id in expected["retrieved_memory_ids"])
        assert isinstance(expected.get("reply_must_not_contain", []), list)
        assert all(isinstance(term, str) and term for term in expected.get("reply_must_not_contain", []))
        assert isinstance(item.get("memories"), list)
        for memory in item["memories"]:
            assert memory.get("status") in ALLOWED_PERSONA_MEMORY_STATUSES
            assert memory.get("type") in ALLOWED_PERSONA_MEMORY_TYPES
            assert isinstance(memory.get("summary"), str) and memory["summary"]


def test_voice_input_local_asr_release_regression_scenarios_are_present():
    scenarios = _load_voice_input_local_asr_scenarios()
    by_id = {item["id"]: item for item in scenarios}
    release_ids = {
        "local-asr-packaged-clean-start",
        "local-asr-no-env-setup-save",
        "local-asr-settings-refresh-ready",
        "local-asr-settings-persist-after-restart",
        "local-asr-check-probe-succeeds",
        "local-asr-audio-capture-succeeds",
        "local-asr-record-transcribe-fills-input",
        "local-asr-main-chat-button-uses-local-asr",
        "local-asr-transcript-simplified-chinese",
        "local-asr-no-auto-send",
        "local-asr-no-context-pollution",
        "local-asr-native-picker-regression-freeze",
        "voice-local-asr-regression-freeze",
        "local-asr-privacy-no-full-paths",
        "local-asr-clear-config-fallback",
        "local-asr-backend-no-residual-process",
    }
    required_forbidden_terms = {
        ".env",
        "Authorization",
        "api_key",
        "raw stdout",
        "raw stderr",
        "full audio path",
        "full transcript",
        "base64",
    }

    assert release_ids <= set(by_id)
    for scenario_id in release_ids:
        scenario = by_id[scenario_id]
        assert scenario["manual_only"] is True
        assert scenario["should_auto_send"] is False
        assert scenario["should_upload_audio"] is False
        assert required_forbidden_terms <= set(scenario.get("forbidden_terms", []))


def test_readme_qa_links_point_to_existing_files():
    readme = README_PATH.read_text(encoding="utf-8")
    readme_en = README_EN_PATH.read_text(encoding="utf-8")
    qa_doc = QA_DOC_PATH.read_text(encoding="utf-8")
    project_status = PROJECT_STATUS_PATH.read_text(encoding="utf-8")
    local_asr_manual_setup = LOCAL_ASR_MANUAL_SETUP_PATH.read_text(encoding="utf-8")
    voice_mvp_release_notes = VOICE_MVP_RELEASE_NOTES_PATH.read_text(encoding="utf-8")
    links = re.findall(
        r"\((docs/(?:PROJECT_STATUS\.md|QA\.md|voice-input-local-asr-spike\.md|local-asr-manual-setup\.md|release-notes/reilink-voice-mvp\.md|qa/(?:retrieval_scenarios|voice_input_scenarios|voice_input_local_asr_scenarios)\.json))\)",
        f"{readme}\n{readme_en}",
    )

    assert "README.en.md" in readme
    assert "README.md" in readme_en
    assert {
        "docs/PROJECT_STATUS.md",
        "docs/QA.md",
        "docs/voice-input-local-asr-spike.md",
        "docs/local-asr-manual-setup.md",
        "docs/release-notes/reilink-voice-mvp.md",
        "docs/qa/retrieval_scenarios.json",
        "docs/qa/voice_input_scenarios.json",
        "docs/qa/voice_input_local_asr_scenarios.json",
    } <= set(links)
    for link in links:
        assert (REPO_ROOT / link).is_file()

    assert "docs/voice-input-local-asr-spike.md" in qa_doc
    assert "docs/local-asr-manual-setup.md" in qa_doc
    assert "docs/qa/voice_input_local_asr_scenarios.json" in qa_doc
    assert "docs/qa/session_timeline_scenarios.json" in qa_doc
    assert "docs/qa/persona_pack_scenarios.json" in qa_doc
    assert "docs/qa/persona_memory_regression_scenarios.json" in qa_doc
    assert "docs/release-notes/reilink-voice-mvp.md" in qa_doc
    assert "Voice Interaction MVP" in project_status
    assert "Persona-Memory Eval v0.1" in project_status
    assert "REILINK_LOCAL_ASR_BINARY" in local_asr_manual_setup
    assert "REILINK_LOCAL_ASR_MODEL" in local_asr_manual_setup
    assert "REILINK_AUDIO_CONVERTER_BINARY" in local_asr_manual_setup
    assert "Voice Interaction MVP" in voice_mvp_release_notes
    assert "No cloud ASR" in voice_mvp_release_notes


def test_regression_freeze_docs_cover_voice_asr_overlay_safe_mode():
    qa_doc = QA_DOC_PATH.read_text(encoding="utf-8")
    project_status = PROJECT_STATUS_PATH.read_text(encoding="utf-8")
    overlay_scenarios = {item["id"] for item in _load_overlay_scenarios()}
    local_asr_scenarios = {item["id"] for item in _load_voice_input_local_asr_scenarios()}

    assert "Voice / Local ASR / Overlay Safe Mode 阶段冻结人工验收" in qa_doc
    assert "Desktop Window Stability" in qa_doc
    assert "Overlay Safe Mode" in qa_doc
    assert "Local ASR Native File Picker" in qa_doc
    assert "Voice / ASR Regression" in qa_doc
    assert "macOS 下 auto-show 暂时不出现小气泡，这是当前预期" in qa_doc
    assert "transcript 不自动发送" in qa_doc

    assert "Voice Output v1 / v1.1 已稳定" in project_status
    assert "Local ASR v1 已稳定" in project_status
    assert "Local ASR Native File Picker v1 已加入" in project_status
    assert "file picker 只填入路径，不读取、不复制、不上传文件" in project_status
    assert "macOS Overlay auto-show 仍故意 fail-closed" in project_status
    assert "不是完整可用的游戏悬浮气泡功能" in project_status

    assert "overlay-safe-mode-regression-freeze-manual" in overlay_scenarios
    assert "local-asr-native-picker-regression-freeze" in local_asr_scenarios
    assert "voice-local-asr-regression-freeze" in local_asr_scenarios
