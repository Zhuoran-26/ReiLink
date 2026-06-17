from __future__ import annotations

import json
import tempfile
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.modules.dialogue_agent import semantic_extraction as sem
from app.modules.dialogue_agent.intent import detect_intent
from app.modules.elden_ring_knowledge.terminology import normalize_terminology
from app.modules.game_session.state import CurrentBoss, GameSessionState, GameSessionStore

REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "extraction_eval_scenarios.json"

ALLOWED_INPUT_SOURCES = {"text", "voice_confirmed", "voice_direct"}
ALLOWED_PROVIDER_MODES = {"mock", "live"}


def load_extraction_eval_scenarios(path: Path | str | None = None) -> list[dict[str, Any]]:
    scenario_path = Path(path) if path else DEFAULT_SCENARIOS_PATH
    data = json.loads(scenario_path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("extraction eval scenarios must be a non-empty list")
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("each extraction eval scenario must be an object")
    return data


def run_extraction_eval(
    scenarios: Iterable[dict[str, Any]] | None = None,
    *,
    scenarios_path: Path | str | None = None,
    provider_mode: str = "mock",
) -> dict[str, Any]:
    mode = provider_mode if provider_mode in ALLOWED_PROVIDER_MODES else "mock"
    scenario_items = list(scenarios if scenarios is not None else load_extraction_eval_scenarios(scenarios_path))
    results = [_run_scenario(item, provider_mode=mode) for item in scenario_items]
    return {
        "provider_mode": mode,
        "metrics": _eval_metrics(results),
        "results": results,
    }


def _run_scenario(scenario: dict[str, Any], *, provider_mode: str) -> dict[str, Any]:
    scenario_id = _required_text(scenario, "id")
    input_text = _required_text(scenario, "input")
    input_source = _safe_input_source(scenario.get("input_source"))
    intent = str(scenario.get("intent") or detect_intent(input_text).intent)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pre_state = _game_session_state_from_data(scenario.get("pre_state"), now=now)
    session_focus_boss = normalize_terminology(str(scenario.get("session_focus_boss") or "")) or None

    with tempfile.TemporaryDirectory(prefix="reilink-extraction-eval-") as tmpdir:
        store = GameSessionStore(state_path=Path(tmpdir) / "game_session.json")
        store.save(pre_state)
        before_state = _state_snapshot(store.debug_state(now=now))
        game_state = store.debug_state(now=now)
        game_status = _game_status(scenario)
        mock_context = (
            _mock_primary_provider_context(_mock_sequence_for_scenario(scenario))
            if provider_mode == "mock"
            else nullcontext()
        )
        with mock_context:
            debug = sem.extract_semantics(
                input_text,
                intent,
                game_state,
                session_focus_boss=session_focus_boss,
                input_source=input_source,
                run_llm_primary=True,
                run_llm_shadow=False,
            )
        final_event = ((debug.get("final_decision") or {}).get("game_event") or {})
        if str(final_event.get("type") or "none") != "none":
            store.update_from_user_message(
                "",
                "casual_chat",
                game_status,
                now,
                session_focus_boss=None,
                semantic_game_event=final_event,
            )
        after_state = _state_snapshot(store.debug_state(now=now))

    actual = _actual_result(debug, before_state=before_state, after_state=after_state)
    expected = scenario.get("expected") if isinstance(scenario.get("expected"), dict) else {}
    failures = _evaluate_scenario(expected, actual)
    return {
        "scenario_id": scenario_id,
        "input_text": input_text,
        "input_source": input_source,
        "expected_decision": expected.get("decision"),
        "actual_decision": actual["decision"],
        "expected_applied_updates": expected.get("applied_updates", []),
        "actual_applied_updates": actual["applied_updates"],
        "expected_state": _expected_state_summary(expected),
        "actual_state": actual["state"],
        "expected_state_delta": expected.get("state_delta", {}),
        "actual_state_delta": actual["state_delta"],
        "primary_extractor": actual["primary_extractor"],
        "primary_status": actual["primary_status"],
        "provider_status": actual["provider_status"],
        "schema_valid": actual["schema_valid"],
        "invalid_json": actual["invalid_json"],
        "schema_invalid": actual["schema_invalid"],
        "compat_retry_used": actual["compat_retry_used"],
        "compat_retry_succeeded": actual["compat_retry_succeeded"],
        "ultra_compact_used": actual["ultra_compact_used"],
        "fallback_extractor": actual["fallback_extractor"],
        "applied_by": actual["applied_by"],
        "pass": not failures,
        "failure_reason": "; ".join(failures),
    }


@contextmanager
def _mock_primary_provider_context(sequence: list[Any]):
    old_provider = sem.settings.llm_provider
    old_key = sem.settings.deepseek_api_key
    old_call = sem._call_llm_primary
    responses = list(sequence)
    last_response = responses[-1] if responses else _no_op_mock_payload()
    sem.settings.llm_provider = "deepseek"
    sem.settings.deepseek_api_key = "test-key"

    def fake_primary(*args: Any, **kwargs: Any) -> str:
        del args, kwargs
        payload = responses.pop(0) if responses else last_response
        if isinstance(payload, str):
            return payload
        return json.dumps(payload, ensure_ascii=False)

    sem._call_llm_primary = fake_primary
    try:
        yield
    finally:
        sem._call_llm_primary = old_call
        sem.settings.llm_provider = old_provider
        sem.settings.deepseek_api_key = old_key


def _mock_sequence_for_scenario(scenario: dict[str, Any]) -> list[Any]:
    if isinstance(scenario.get("mock_primary_sequence"), list):
        return list(scenario["mock_primary_sequence"])
    if "mock_primary" in scenario:
        return [scenario["mock_primary"]]
    return [_no_op_mock_payload()]


def _no_op_mock_payload() -> dict[str, Any]:
    return {
        "is_game_related": False,
        "intent": "none",
        "confidence": 0.0,
        "updates": [],
        "safe_trace_summary": "no-op eval fallback",
    }


def _actual_result(
    debug: dict[str, Any],
    *,
    before_state: dict[str, Any],
    after_state: dict[str, Any],
) -> dict[str, Any]:
    trace = debug.get("extraction_trace") if isinstance(debug.get("extraction_trace"), dict) else {}
    final_decision = debug.get("final_decision") if isinstance(debug.get("final_decision"), dict) else {}
    final_event = final_decision.get("game_event") if isinstance(final_decision.get("game_event"), dict) else {}
    llm_shadow = debug.get("llm_shadow") if isinstance(debug.get("llm_shadow"), dict) else {}
    parse_error = str(debug.get("parse_error") or "")
    provider_status = str(debug.get("llm_provider_status") or "")
    return {
        "decision": str(trace.get("final_decision") or debug.get("guard_final_decision") or debug.get("llm_guard_decision") or "no_op"),
        "event_type": str(final_event.get("type") or "none"),
        "applied_updates": _safe_string_list(trace.get("applied_updates") or debug.get("applied_updates") or []),
        "primary_extractor": trace.get("primary_extractor") or debug.get("primary_extractor"),
        "primary_status": trace.get("primary_status") or debug.get("primary_status") or debug.get("llm_primary_status"),
        "provider_status": provider_status or None,
        "schema_valid": debug.get("llm_schema_valid"),
        "invalid_json": parse_error == "semantic_extraction_invalid_json" or provider_status == "invalid_json",
        "schema_invalid": parse_error == "semantic_extraction_schema_invalid" or provider_status == "schema_error",
        "compat_retry_used": bool(debug.get("compat_retry_used")),
        "compat_retry_succeeded": debug.get("compat_retry_succeeded") if isinstance(debug.get("compat_retry_succeeded"), bool) else None,
        "ultra_compact_used": bool(debug.get("ultra_compact_used")),
        "fallback_extractor": trace.get("fallback_extractor") or debug.get("fallback_extractor"),
        "applied_by": trace.get("applied_by") or debug.get("applied_by"),
        "state": after_state,
        "state_delta": _state_delta(before_state, after_state),
        "pending_memory": bool(((final_decision.get("memory_candidate") or {}).get("should_create_pending"))),
        "guide_request": bool((llm_shadow.get("guide_request") or {}).get("value")),
        "guide_only_entity": (llm_shadow.get("guide_only_entity") or {}).get("value"),
    }


def _evaluate_scenario(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    expected_decision = expected.get("decision")
    acceptable = set(expected.get("acceptable_decisions") or ([expected_decision] if expected_decision else []))
    if acceptable and actual["decision"] not in acceptable:
        failures.append(f"decision expected {sorted(acceptable)} got {actual['decision']}")
    for key, actual_key in (
        ("applied_by", "applied_by"),
        ("fallback_extractor", "fallback_extractor"),
        ("primary_status", "primary_status"),
        ("provider_status", "provider_status"),
        ("schema_valid", "schema_valid"),
        ("invalid_json", "invalid_json"),
        ("schema_invalid", "schema_invalid"),
        ("compat_retry_used", "compat_retry_used"),
        ("compat_retry_succeeded", "compat_retry_succeeded"),
        ("ultra_compact_used", "ultra_compact_used"),
        ("event_type", "event_type"),
        ("pending_memory", "pending_memory"),
        ("guide_request", "guide_request"),
        ("guide_only_entity", "guide_only_entity"),
    ):
        if key in expected and expected[key] != actual.get(actual_key):
            failures.append(f"{key} expected {expected[key]!r} got {actual.get(actual_key)!r}")
    for update in _safe_string_list(expected.get("applied_updates") or []):
        if update not in actual["applied_updates"]:
            failures.append(f"missing applied update {update}")
    for update in _safe_string_list(expected.get("absent_applied_updates") or []):
        if update in actual["applied_updates"]:
            failures.append(f"unexpected applied update {update}")
    _compare_state_expectations(expected, actual, failures)
    if expected.get("must_not_clear_boss") and actual["event_type"] == "boss_cleared":
        failures.append("unexpected boss_cleared event")
    forbidden_bosses = {normalize_terminology(item) for item in _safe_string_list(expected.get("forbidden_current_boss") or [])}
    if actual["state"]["current_boss"] in forbidden_bosses:
        failures.append(f"forbidden current boss {actual['state']['current_boss']}")
    return failures


def _compare_state_expectations(expected: dict[str, Any], actual: dict[str, Any], failures: list[str]) -> None:
    state = actual["state"]
    expected_boss = expected.get("current_boss", "__missing__")
    if expected_boss != "__missing__" and _normalize_optional(expected_boss) != _normalize_optional(state["current_boss"]):
        failures.append(f"current_boss expected {expected_boss!r} got {state['current_boss']!r}")
    for key in ("current_game", "death_count", "frustration_count", "current_activity"):
        if key in expected and expected[key] != state.get(key):
            failures.append(f"{key} expected {expected[key]!r} got {state.get(key)!r}")
    if "last_cleared_boss" in expected and _normalize_optional(expected["last_cleared_boss"]) != _normalize_optional(state["last_cleared_boss"]):
        failures.append(f"last_cleared_boss expected {expected['last_cleared_boss']!r} got {state['last_cleared_boss']!r}")


def _eval_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for item in results if item["pass"])
    failed = total - passed
    return {
        "total_scenarios": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "llm_primary_success_count": sum(1 for item in results if item["primary_status"] == "succeeded"),
        "schema_valid_count": sum(1 for item in results if item["schema_valid"] is True),
        "invalid_json_count": sum(1 for item in results if item["invalid_json"]),
        "schema_invalid_count": sum(1 for item in results if item["schema_invalid"]),
        "fallback_to_rule_count": sum(1 for item in results if item["actual_decision"] == "fallback_to_rule"),
        "compat_retry_used_count": sum(1 for item in results if item["compat_retry_used"]),
        "ultra_compact_used_count": sum(1 for item in results if item["ultra_compact_used"]),
        "wrong_apply_count": sum(
            1
            for item in results
            if item["actual_decision"] == "apply" and item["expected_decision"] not in {"apply", "fallback_to_rule"}
        ),
        "missed_apply_count": sum(
            1
            for item in results
            if item["expected_decision"] == "apply" and item["actual_decision"] != "apply"
        ),
        "candidate_only_correct_count": sum(
            1
            for item in results
            if item["actual_decision"] == "candidate_only"
            and item["expected_decision"] in {"candidate_only", "no_state_change"}
            and item["pass"]
        ),
    }


def _game_session_state_from_data(value: Any, *, now: datetime) -> GameSessionState:
    data = value if isinstance(value, dict) else {}
    current_boss = _current_boss(data.get("current_boss"), now=now)
    current_boss_name = current_boss.name if current_boss else None
    return GameSessionState(
        current_game=data.get("current_game"),
        current_boss=current_boss,
        last_boss=normalize_terminology(str(data.get("last_boss") or current_boss_name or "")) or None,
        last_attempted_boss=normalize_terminology(str(data.get("last_attempted_boss") or current_boss_name or "")) or None,
        last_failed_boss=normalize_terminology(str(data.get("last_failed_boss") or "")) or None,
        last_cleared_boss=normalize_terminology(str(data.get("last_cleared_boss") or "")) or None,
        current_activity=data.get("current_activity"),
        death_count=int(data.get("death_count") or 0),
        frustration_count=int(data.get("frustration_count") or 0),
        last_updated_at=now.isoformat(),
    )


def _current_boss(value: Any, *, now: datetime) -> CurrentBoss | None:
    if value is None:
        return None
    if isinstance(value, dict):
        name = normalize_terminology(str(value.get("name") or ""))
        confidence = float(value.get("confidence") or 0.95)
        source = str(value.get("source") or "eval_prestate")
        mention_count = int(value.get("mention_count") or 1)
    else:
        name = normalize_terminology(str(value or ""))
        confidence = 0.95
        source = "eval_prestate"
        mention_count = 1
    if not name:
        return None
    return CurrentBoss(
        name=name,
        updated_at=now.isoformat(),
        confidence=confidence,
        source=source,
        mention_count=mention_count,
    )


def _game_status(scenario: dict[str, Any]) -> dict[str, Any]:
    data = scenario.get("game_status") if isinstance(scenario.get("game_status"), dict) else {}
    return {
        "game_id": data.get("game_id", "elden_ring"),
        "game_name": data.get("game_name", "Elden Ring"),
        "status": data.get("status", "running"),
        "confidence": data.get("confidence", 1.0),
        "tags": data.get("tags", []),
        "detected_game_id": data.get("detected_game_id", "elden_ring"),
        "knowledge_game_id": data.get("knowledge_game_id", "elden_ring"),
    }


def _state_snapshot(debug_state: dict[str, Any]) -> dict[str, Any]:
    current_boss = debug_state.get("current_boss") if isinstance(debug_state.get("current_boss"), dict) else None
    return {
        "current_game": debug_state.get("current_game"),
        "current_boss": current_boss.get("name") if current_boss else None,
        "death_count": int(debug_state.get("death_count") or 0),
        "frustration_count": int(debug_state.get("frustration_count") or 0),
        "last_cleared_boss": debug_state.get("last_cleared_boss"),
        "current_activity": debug_state.get("current_activity"),
    }


def _state_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }


def _expected_state_summary(expected: dict[str, Any]) -> dict[str, Any]:
    keys = ("current_game", "current_boss", "death_count", "frustration_count", "last_cleared_boss", "current_activity")
    return {key: expected[key] for key in keys if key in expected}


def _required_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"extraction eval scenario missing required text field: {key}")
    return value


def _safe_input_source(value: Any) -> str:
    text = str(value or "text")
    return text if text in ALLOWED_INPUT_SOURCES else "text"


def _safe_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _normalize_optional(value: Any) -> str | None:
    if value is None:
        return None
    return normalize_terminology(str(value)) or None
