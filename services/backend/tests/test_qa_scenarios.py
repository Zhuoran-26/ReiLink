import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "retrieval_scenarios.json"
VOICE_INPUT_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "voice_input_scenarios.json"
VOICE_INPUT_LOCAL_ASR_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "voice_input_local_asr_scenarios.json"
QA_DOC_PATH = REPO_ROOT / "docs" / "QA.md"
README_PATH = REPO_ROOT / "README.md"
LOCAL_ASR_MANUAL_SETUP_PATH = REPO_ROOT / "docs" / "local-asr-manual-setup.md"
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


def test_qa_scenarios_file_is_valid_json():
    scenarios = _load_scenarios()

    assert len(scenarios) >= 16


def test_voice_input_scenarios_file_is_valid_json():
    scenarios = _load_voice_input_scenarios()

    assert len(scenarios) >= 8


def test_voice_input_local_asr_scenarios_file_is_valid_json():
    scenarios = _load_voice_input_local_asr_scenarios()

    assert len(scenarios) >= 12


def test_qa_scenario_ids_are_unique_and_categories_are_present():
    scenarios = [
        *_load_scenarios(),
        *_load_voice_input_scenarios(),
        *_load_voice_input_local_asr_scenarios(),
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
    for item in [*_load_scenarios(), *_load_voice_input_scenarios(), *_load_voice_input_local_asr_scenarios()]:
        forbidden_terms = item.get("forbidden_terms", [])
        assert isinstance(forbidden_terms, list)
        assert all(isinstance(term, str) and term for term in forbidden_terms)


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


def test_readme_qa_links_point_to_existing_files():
    readme = README_PATH.read_text(encoding="utf-8")
    qa_doc = QA_DOC_PATH.read_text(encoding="utf-8")
    local_asr_manual_setup = LOCAL_ASR_MANUAL_SETUP_PATH.read_text(encoding="utf-8")
    links = re.findall(
        r"\((docs/(?:QA\.md|voice-input-local-asr-spike\.md|local-asr-manual-setup\.md|qa/(?:retrieval_scenarios|voice_input_scenarios|voice_input_local_asr_scenarios)\.json))\)",
        readme,
    )

    assert {
        "docs/QA.md",
        "docs/voice-input-local-asr-spike.md",
        "docs/local-asr-manual-setup.md",
        "docs/qa/retrieval_scenarios.json",
        "docs/qa/voice_input_scenarios.json",
        "docs/qa/voice_input_local_asr_scenarios.json",
    } <= set(links)
    for link in links:
        assert (REPO_ROOT / link).is_file()

    assert "docs/voice-input-local-asr-spike.md" in qa_doc
    assert "docs/local-asr-manual-setup.md" in qa_doc
    assert "docs/qa/voice_input_local_asr_scenarios.json" in qa_doc
    assert "REILINK_LOCAL_ASR_BINARY" in local_asr_manual_setup
    assert "REILINK_LOCAL_ASR_MODEL" in local_asr_manual_setup
    assert "REILINK_AUDIO_CONVERTER_BINARY" in local_asr_manual_setup
