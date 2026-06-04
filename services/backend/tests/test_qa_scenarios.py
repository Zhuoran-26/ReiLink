import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "retrieval_scenarios.json"
VOICE_INPUT_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "voice_input_scenarios.json"
VOICE_INPUT_LOCAL_ASR_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "voice_input_local_asr_scenarios.json"
QA_DOC_PATH = REPO_ROOT / "docs" / "QA.md"
README_PATH = REPO_ROOT / "README.md"
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
    "local_asr_transcribing",
    "local_asr_completed",
    "local_asr_error",
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
        "local-asr-transcription-completed",
        "local-asr-transcription-error",
        "local-asr-transcript-awaits-send",
        "local-asr-transcript-does-not-enter-memory-before-send",
        "local-asr-temporary-audio-cleanup",
        "local-asr-event-stream-privacy",
        "local-asr-packaged-unavailable-fallback",
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


def test_readme_qa_links_point_to_existing_files():
    readme = README_PATH.read_text(encoding="utf-8")
    qa_doc = QA_DOC_PATH.read_text(encoding="utf-8")
    links = re.findall(
        r"\((docs/(?:QA\.md|voice-input-local-asr-spike\.md|qa/(?:retrieval_scenarios|voice_input_scenarios|voice_input_local_asr_scenarios)\.json))\)",
        readme,
    )

    assert {
        "docs/QA.md",
        "docs/voice-input-local-asr-spike.md",
        "docs/qa/retrieval_scenarios.json",
        "docs/qa/voice_input_scenarios.json",
        "docs/qa/voice_input_local_asr_scenarios.json",
    } <= set(links)
    for link in links:
        assert (REPO_ROOT / link).is_file()

    assert "docs/voice-input-local-asr-spike.md" in qa_doc
    assert "docs/qa/voice_input_local_asr_scenarios.json" in qa_doc
