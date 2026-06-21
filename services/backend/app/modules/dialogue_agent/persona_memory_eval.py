from __future__ import annotations

import json
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.modules.dialogue_agent.intent import detect_intent
from app.modules.dialogue_agent.providers import get_provider
from app.modules.dialogue_agent.style import apply_rei_style
from app.modules.dialogue_agent.validator import validate_or_repair
from app.modules.memory.profile import PlayerMemory, UserProfile
from app.modules.persona_engine.engine import PersonaEngine

REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SCENARIOS_PATH = REPO_ROOT / "docs" / "qa" / "persona_memory_regression_scenarios.json"

ALLOWED_PROVIDER_MODES = {"mock", "live"}
ALLOWED_INPUT_SOURCES = {"text", "voice_confirmed", "voice_direct"}
PASS_SEVERITIES = {"pass", "soft_pass"}
LIVE_EVAL_SCENARIO_DELAY_SECONDS = 0.2

MEMORY_MECHANIC_TERMS = (
    "根据记忆",
    "已验证长期记忆",
    "长期记忆",
    "候选记忆",
    "记忆候选",
    "待确认记忆条目",
    "memory candidate",
    "promptmemoryblock",
    "retrieval",
    "prompt",
    "prompt 注入",
    "guard",
    "safe summary",
    "系统显示",
    "检索到",
    "根据你的记忆记录",
    "我把这条放进",
)
MECHANICAL_MEMORY_RECALL_TERMS = (
    "我记得你",
    "根据我记住的",
    "按照你的长期记忆",
)
PERSONA_DRIFT_TERMS = (
    "撒娇",
    "撒嬌",
    "卖萌",
    "賣萌",
    "主人",
    "亲亲",
    "宝贝",
    "寶貝",
    "客服",
    "客服式鼓励",
    "我会一直夸你",
    "太棒了你一定可以",
    "有什么可以帮助你",
    "有什麽可以帮助你",
    "请问",
)
SECRET_LEAK_TERMS = (
    "sk-",
    ".env",
    "api key 是",
)
CURRENT_INPUT_REFUSAL_TERMS = (
    "不能剧透",
    "不剧透",
    "不能说",
    "不告诉",
    "自己探索",
    "自己去看",
)
CURRENT_INPUT_DETAIL_TERMS = (
    "详细",
    "完整",
    "攻略",
    "直接告诉",
    "会遇到什么也说",
)
RELAXED_SEMANTIC_MARKERS = (
    "绕",
    "探索",
    "逛",
    "赐福",
    "补给",
    "回来",
    "别急",
    "别硬",
    "少打一刀",
    "只补一刀",
    "滚",
    "延迟",
    "落",
    "拉开",
    "不剧透",
    "具体名字",
    "提前知道",
    "说重点",
    "先停一下",
    "节奏",
    "慢",
)
SAFE_REPORT_FORBIDDEN_TERMS = (
    "TEST_SECRET_PLACEHOLDER",
    "raw prompt",
    "raw json",
    ".env",
    "/users/",
    "authorization",
    "bearer",
    "stdout",
    "stderr",
)


def load_persona_memory_eval_scenarios(path: Path | str | None = None) -> list[dict[str, Any]]:
    scenario_path = Path(path) if path else DEFAULT_SCENARIOS_PATH
    data = json.loads(scenario_path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("persona-memory eval scenarios must be a non-empty list")
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("each persona-memory eval scenario must be an object")
    return data


def run_persona_memory_eval(
    scenarios: Iterable[dict[str, Any]] | None = None,
    *,
    scenarios_path: Path | str | None = None,
    provider_mode: str = "mock",
) -> dict[str, Any]:
    mode = provider_mode if provider_mode in ALLOWED_PROVIDER_MODES else "mock"
    scenario_items = list(
        scenarios if scenarios is not None else load_persona_memory_eval_scenarios(scenarios_path)
    )
    results = []
    for index, item in enumerate(scenario_items):
        if mode == "live" and index > 0:
            time.sleep(LIVE_EVAL_SCENARIO_DELAY_SECONDS)
        results.append(_run_scenario(item, provider_mode=mode))
    return {
        "provider_mode": mode,
        "metrics": _eval_metrics(results),
        "results": results,
        "raw_prompt_omitted": True,
    }


def _run_scenario(scenario: dict[str, Any], *, provider_mode: str) -> dict[str, Any]:
    scenario_id = _required_text(scenario, "id")
    user_message = _required_text(scenario, "input")
    input_source = _safe_input_source(scenario.get("input_source"))
    intent = str(scenario.get("intent") or detect_intent(user_message).intent)
    expected = scenario.get("expected") if isinstance(scenario.get("expected"), dict) else {}
    now = datetime(2026, 6, 18, tzinfo=timezone.utc)

    with tempfile.TemporaryDirectory(prefix="reilink-persona-memory-eval-") as tmpdir:
        memory, setup = _memory_from_scenario(scenario, Path(tmpdir))
        before_counts = _memory_use_counts(memory)
        block = memory.retrieve_prompt_memory(
            user_message=user_message,
            current_game=_safe_optional_text(scenario.get("current_game")) or "Elden Ring",
            current_boss=_safe_optional_text(scenario.get("current_boss")),
            input_source=input_source,
            max_items=_safe_positive_int(scenario.get("retrieval_max_items"), default=4),
            token_budget=_safe_positive_int(scenario.get("retrieval_token_budget"), default=320),
            update_usage=bool(expected.get("should_update_usage", expected.get("should_inject_memory", False))),
            now=now,
        )
        prompt = PersonaEngine().build_prompt(
            "rei_like",
            {
                "game_name": _safe_optional_text(scenario.get("current_game")) or "Elden Ring",
                "status": str(scenario.get("game_status") or "running"),
            },
            intent,
            memory_context=block.as_prompt_text(),
        )
        provider_error = None
        if provider_mode == "live":
            try:
                raw_reply = get_provider().generate_with_metrics(prompt, user_message, [], intent).reply
            except RuntimeError as exc:
                raw_reply = ""
                provider_error = exc.__class__.__name__
        else:
            raw_reply = _required_text(scenario, "mock_reply")
        reply = apply_rei_style(
            validate_or_repair(raw_reply, intent),
            seed=f"persona-memory-eval:{scenario_id}:{user_message}",
        )
        after_counts = _memory_use_counts(memory)

    actual = _actual_result(
        block=block,
        prompt=prompt,
        reply=reply,
        before_counts=before_counts,
        after_counts=after_counts,
        setup=setup,
        provider_error=provider_error,
    )
    evaluation = _evaluate_scenario(scenario, expected, actual, provider_mode=provider_mode)
    return {
        "scenario_id": scenario_id,
        "live_scoring_mode": str(scenario.get("live_scoring_mode") or "strict_mock"),
        "semantic_expectations": _safe_string_list(scenario.get("semantic_expectations") or []),
        "memory_statuses": actual["memory_statuses"],
        "has_pending_memory": actual["has_pending_memory"],
        "has_inactive_memory": actual["has_inactive_memory"],
        "has_persona_drift_memory": actual["has_persona_drift_memory"],
        "has_secret_memory": actual["has_secret_memory"],
        "input_source": input_source,
        "intent": intent,
        "expected_memory_injected": expected.get("should_inject_memory"),
        "actual_memory_injected": bool(actual["retrieved_memory_ids"]),
        "expected_retrieved_memory_ids": expected.get("retrieved_memory_ids", []),
        "actual_retrieved_memory_ids": actual["retrieved_memory_ids"],
        "retrieved_memory_types": actual["retrieved_memory_types"],
        "omitted_count": actual["omitted_count"],
        "token_estimate": actual["token_estimate"],
        "skip_reason": actual["skip_reason"],
        "usage_deltas": actual["usage_deltas"],
        "prompt_order_ok": actual["prompt_order_ok"],
        "prompt_current_input_priority": actual["prompt_current_input_priority"],
        "raw_prompt_omitted": actual["raw_prompt_omitted"],
        "reply_sentence_count": actual["reply_sentence_count"],
        "reply_char_count": actual["reply_char_count"],
        "reply_preview": _preview(reply),
        "memory_mechanic_leak": actual["memory_mechanic_leak"],
        "mechanical_memory_recall": actual["mechanical_memory_recall"],
        "persona_drift_leak": actual["persona_drift_leak"],
        "secret_leak": actual["secret_leak"],
        "pending_or_inactive_used": actual["pending_or_inactive_used"],
        "memory_natural_usage_observed": evaluation["memory_natural_usage_observed"],
        "provider_error": provider_error,
        "severity": evaluation["severity"],
        "hard_fail_reasons": evaluation["hard_fail_reasons"],
        "warning_reasons": evaluation["warning_reasons"],
        "soft_pass_reasons": evaluation["soft_pass_reasons"],
        "required_term_failures": evaluation["required_term_failures"],
        "suggested_marker_misses": evaluation["suggested_marker_misses"],
        "safety_boundary_ok": evaluation["safety_boundary_ok"],
        "style_boundary_ok": evaluation["style_boundary_ok"],
        "helpfulness_warning": evaluation["helpfulness_warning"],
        "pass": evaluation["severity"] in PASS_SEVERITIES,
        "failure_reason": "; ".join(
            [*evaluation["hard_fail_reasons"], *evaluation["warning_reasons"]]
        ),
    }


def _memory_from_scenario(scenario: dict[str, Any], tmpdir: Path) -> tuple[PlayerMemory, dict[str, Any]]:
    memory = PlayerMemory(tmpdir / "profile.json", tmpdir / "episodes.jsonl")
    long_term_memories: list[dict[str, Any]] = []
    non_active_ids: set[str] = set()
    for index, item in enumerate(scenario.get("memories") or []):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "active")
        memory_id = str(item.get("id") or f"memory-{index + 1}")
        if status in {"pending", "ignored", "rejected", "expired"}:
            non_active_ids.add(memory_id)
            continue
        long_term = _long_term_memory_payload(item, memory_id=memory_id, status=status)
        if long_term.get("is_active") is False or long_term.get("deletion_status") != "active":
            non_active_ids.add(memory_id)
        long_term_memories.append(long_term)
    memory.save_profile(UserProfile(long_term_memories=long_term_memories))
    return memory, {
        "non_active_ids": sorted(non_active_ids),
        "memory_statuses": [
            str(item.get("status") or "active")
            for item in scenario.get("memories") or []
            if isinstance(item, dict)
        ],
        "has_pending_memory": any(
            str(item.get("status") or "") == "pending"
            for item in scenario.get("memories") or []
            if isinstance(item, dict)
        ),
        "has_inactive_memory": any(
            str(item.get("status") or "") in {"undone", "deleted", "inactive"}
            or item.get("is_active") is False
            for item in scenario.get("memories") or []
            if isinstance(item, dict)
        ),
        "has_persona_drift_memory": any(
            _contains_any(str(item.get("summary") or ""), PERSONA_DRIFT_TERMS)
            or _contains_any(str(item.get("summary") or ""), ("每句话都夸", "每句話都誇"))
            for item in scenario.get("memories") or []
            if isinstance(item, dict)
        ),
        "has_secret_memory": any(
            _contains_any(str(item.get("summary") or ""), SECRET_LEAK_TERMS)
            or str(item.get("privacy_level") or "") in {"secret", "secret_rejected", "sensitive"}
            for item in scenario.get("memories") or []
            if isinstance(item, dict)
        ),
    }


def _long_term_memory_payload(item: dict[str, Any], *, memory_id: str, status: str) -> dict[str, Any]:
    is_active = bool(item.get("is_active", status == "active"))
    deletion_status = str(item.get("deletion_status") or ("active" if status == "active" else status))
    if status == "undone":
        is_active = False
        deletion_status = "undone"
    if status == "deleted":
        is_active = False
        deletion_status = "deleted"
    timestamp = "2026-06-18T00:00:00+00:00"
    payload = {
        "id": memory_id,
        "created_at": str(item.get("created_at") or timestamp),
        "updated_at": str(item.get("updated_at") or timestamp),
        "type": str(item.get("type") or "unknown"),
        "summary": _safe_optional_text(item.get("summary")) or "",
        "user_visible_text": _safe_optional_text(item.get("user_visible_text") or item.get("summary")) or "",
        "source_candidate_id": str(item.get("source_candidate_id") or f"pending-{memory_id}"),
        "is_active": is_active,
        "related_game": _safe_optional_text(item.get("related_game")),
        "related_entity": _safe_optional_text(item.get("related_entity")),
        "use_count": int(item.get("use_count") or 0),
        "last_used_at": item.get("last_used_at"),
        "retrieval_tags": item.get("retrieval_tags") if isinstance(item.get("retrieval_tags"), list) else [],
        "deletion_status": deletion_status,
    }
    for key in ("privacy_level", "source", "from_assistant", "from_proactive"):
        if key in item:
            payload[key] = item[key]
    return payload


def _actual_result(
    *,
    block: Any,
    prompt: str,
    reply: str,
    before_counts: dict[str, int],
    after_counts: dict[str, int],
    setup: dict[str, Any],
    provider_error: str | None,
) -> dict[str, Any]:
    debug = block.as_debug_dict()
    retrieved_ids = [str(item.get("memory_id") or "") for item in debug.get("items", []) if item.get("memory_id")]
    prompt_and_reply = f"{prompt}\n{reply}"
    mechanic_leak = _contains_any(reply, MEMORY_MECHANIC_TERMS)
    mechanical_memory_recall = _contains_any(reply, MECHANICAL_MEMORY_RECALL_TERMS)
    persona_drift_leak = _contains_any(reply, PERSONA_DRIFT_TERMS)
    secret_leak = _contains_any(prompt_and_reply, SECRET_LEAK_TERMS)
    return {
        "memory_statuses": setup.get("memory_statuses") or [],
        "has_pending_memory": bool(setup.get("has_pending_memory")),
        "has_inactive_memory": bool(setup.get("has_inactive_memory")),
        "has_persona_drift_memory": bool(setup.get("has_persona_drift_memory")),
        "has_secret_memory": bool(setup.get("has_secret_memory")),
        "retrieved_memory_ids": retrieved_ids,
        "retrieved_memory_types": [str(item.get("memory_type") or "") for item in debug.get("items", [])],
        "omitted_count": int(debug.get("omitted_count") or 0),
        "token_estimate": int(debug.get("token_estimate") or 0),
        "skip_reason": debug.get("skip_reason"),
        "usage_deltas": _usage_deltas(before_counts, after_counts),
        "prompt_order_ok": _prompt_order_ok(prompt),
        "prompt_current_input_priority": "当前用户明确输入优先" in prompt,
        "raw_prompt_omitted": debug.get("raw_prompt_omitted") is True,
        "prompt": prompt,
        "reply": reply,
        "reply_sentence_count": _sentence_count(reply),
        "reply_char_count": len(reply.strip()),
        "memory_mechanic_leak": mechanic_leak,
        "mechanical_memory_recall": mechanical_memory_recall,
        "persona_drift_leak": persona_drift_leak,
        "secret_leak": secret_leak,
        "pending_or_inactive_used": bool(set(retrieved_ids) & set(setup.get("non_active_ids") or [])),
        "provider_error": provider_error,
    }


def _evaluate_scenario(
    scenario: dict[str, Any],
    expected: dict[str, Any],
    actual: dict[str, Any],
    *,
    provider_mode: str,
) -> dict[str, Any]:
    hard_fail_reasons: list[str] = []
    warning_reasons: list[str] = []
    soft_pass_reasons: list[str] = []
    required_term_failures: list[str] = []
    suggested_marker_misses: list[str] = []
    reply_hard_required_terms = _merged_string_list(
        scenario.get("hard_required_terms"),
        expected.get("hard_required_terms"),
    )
    suggested_markers = _merged_string_list(
        scenario.get("suggested_markers"),
        expected.get("suggested_markers"),
    )
    if "should_inject_memory" in expected and bool(expected["should_inject_memory"]) != bool(actual["retrieved_memory_ids"]):
        hard_fail_reasons.append("memory injection expectation mismatch")
    if "retrieved_memory_ids" in expected and list(expected["retrieved_memory_ids"]) != actual["retrieved_memory_ids"]:
        hard_fail_reasons.append("retrieved memory ids mismatch")
    for memory_id in _safe_string_list(expected.get("forbidden_memory_ids") or []):
        if memory_id in actual["retrieved_memory_ids"]:
            hard_fail_reasons.append("forbidden memory id retrieved")
    if expected.get("should_update_usage") is True and not any(delta > 0 for delta in actual["usage_deltas"].values()):
        hard_fail_reasons.append("expected memory usage update")
    if expected.get("should_update_usage") is False and any(delta != 0 for delta in actual["usage_deltas"].values()):
        hard_fail_reasons.append("unexpected memory usage update")
    if expected.get("prompt_order_persona_before_memory", True) and not actual["prompt_order_ok"]:
        hard_fail_reasons.append("persona pack should remain before memory block")
    if expected.get("current_input_priority") and not actual["prompt_current_input_priority"]:
        hard_fail_reasons.append("prompt missing current input priority")
    if expected.get("raw_prompt_omitted", True) and not actual["raw_prompt_omitted"]:
        hard_fail_reasons.append("raw prompt omission flag missing")
    _check_required_terms(actual["prompt"], expected.get("prompt_must_contain"), "prompt", hard_fail_reasons)
    _check_forbidden_terms(actual["prompt"], expected.get("prompt_must_not_contain"), "prompt", hard_fail_reasons)
    _check_required_terms(actual["reply"], reply_hard_required_terms, "reply", hard_fail_reasons)
    required_term_failures.extend(
        _missing_terms(actual["reply"], reply_hard_required_terms, "reply")
    )
    if provider_mode == "mock":
        mock_reply_terms = _safe_string_list(expected.get("reply_must_contain") or [])
        _check_required_terms(actual["reply"], mock_reply_terms, "reply", hard_fail_reasons)
        required_term_failures.extend(_missing_terms(actual["reply"], mock_reply_terms, "reply"))
    else:
        live_suggested_markers = _merged_string_list(
            suggested_markers,
            expected.get("reply_must_contain"),
        )
        suggested_marker_misses.extend(_missing_terms(actual["reply"], live_suggested_markers, "reply"))
        if suggested_marker_misses:
            warning_reasons.append("reply missing suggested marker")
    _check_forbidden_terms(actual["reply"], expected.get("reply_must_not_contain"), "reply", hard_fail_reasons)
    if expected.get("must_not_expose_memory_mechanics", True) and actual["memory_mechanic_leak"]:
        hard_fail_reasons.append("reply exposed memory mechanics")
    if expected.get("must_not_mechanically_recall_memory", True) and actual["mechanical_memory_recall"]:
        hard_fail_reasons.append("reply mechanically recalled memory")
    if expected.get("must_preserve_persona", True) and actual["persona_drift_leak"]:
        hard_fail_reasons.append("reply drifted from persona boundary")
    if expected.get("must_not_leak_secret", True) and actual["secret_leak"]:
        hard_fail_reasons.append("secret leaked into prompt or reply")
    if actual["pending_or_inactive_used"]:
        hard_fail_reasons.append("pending or inactive memory was retrieved")
    if "omitted_count" in expected and int(expected["omitted_count"]) != actual["omitted_count"]:
        hard_fail_reasons.append("omitted_count mismatch")
    if "skip_reason" in expected and expected["skip_reason"] != actual["skip_reason"]:
        hard_fail_reasons.append("skip_reason mismatch")
    length_warnings = _reply_length_findings(expected, actual)
    if provider_mode == "mock":
        hard_fail_reasons.extend(length_warnings)
    else:
        warning_reasons.extend(length_warnings)
    if provider_mode == "live" and _current_input_priority_failed(scenario, expected, actual):
        hard_fail_reasons.append("current input priority failed")
    if actual["provider_error"]:
        hard_fail_reasons.append(f"provider error: {actual['provider_error']}")

    memory_natural_usage_observed = _memory_natural_usage_observed(
        actual,
        suggested_markers=suggested_markers,
        expected=expected,
    )
    if (
        provider_mode == "live"
        and actual["retrieved_memory_ids"]
        and not memory_natural_usage_observed
        and not hard_fail_reasons
    ):
        warning_reasons.append("memory influence weak")
    helpfulness_warning = any(
        reason in {"reply is too short", "reply has too few sentences", "memory influence weak"}
        or reason.startswith("reply missing suggested marker")
        for reason in warning_reasons
    )
    if not hard_fail_reasons and not warning_reasons:
        if provider_mode == "live" and memory_natural_usage_observed:
            soft_pass_reasons.append("live reply used memory naturally by heuristic")
        elif provider_mode == "live":
            soft_pass_reasons.append("live reply stayed within safety and style boundaries")
    severity = _severity(
        hard_fail_reasons=hard_fail_reasons,
        warning_reasons=warning_reasons,
        soft_pass_reasons=soft_pass_reasons,
    )
    return {
        "severity": severity,
        "hard_fail_reasons": hard_fail_reasons,
        "warning_reasons": warning_reasons,
        "soft_pass_reasons": soft_pass_reasons,
        "required_term_failures": required_term_failures,
        "suggested_marker_misses": suggested_marker_misses,
        "safety_boundary_ok": not _has_safety_boundary_failure(hard_fail_reasons),
        "style_boundary_ok": "reply drifted from persona boundary" not in hard_fail_reasons,
        "helpfulness_warning": helpfulness_warning,
        "memory_natural_usage_observed": memory_natural_usage_observed,
    }


def _eval_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for item in results if item["pass"])
    failed = total - passed
    hard_failed = sum(1 for item in results if item["severity"] == "hard_fail")
    warnings = sum(1 for item in results if item["severity"] == "warning")
    soft_passed = sum(1 for item in results if item["severity"] == "soft_pass")
    hard_passed = sum(1 for item in results if item["severity"] == "pass")
    return {
        "total_scenarios": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "hard_passed": hard_passed,
        "soft_passed": soft_passed,
        "warnings": warnings,
        "hard_failed": hard_failed,
        "hard_fail_count": hard_failed,
        "warning_count": warnings,
        "soft_pass_count": soft_passed,
        "hard_fail_rate": round(hard_failed / total, 4) if total else 0,
        "warning_rate": round(warnings / total, 4) if total else 0,
        "safe_boundary_pass_count": sum(1 for item in results if item["safety_boundary_ok"]),
        "style_warning_count": sum(
            1
            for item in results
            if not item["style_boundary_ok"]
            or any("style" in reason for reason in item["warning_reasons"])
        ),
        "helpfulness_warning_count": sum(1 for item in results if item["helpfulness_warning"]),
        "semantic_marker_warning_count": sum(
            1 for item in results if item["suggested_marker_misses"]
        ),
        "memory_injected_count": sum(1 for item in results if item["actual_memory_injected"]),
        "memory_skipped_count": sum(1 for item in results if not item["actual_memory_injected"]),
        "prompt_memory_block_correct_count": sum(
            1
            for item in results
            if item["expected_memory_injected"] == item["actual_memory_injected"]
            and (
                "retrieved memory ids mismatch" not in item["hard_fail_reasons"]
                and "forbidden memory id retrieved" not in item["hard_fail_reasons"]
            )
        ),
        "pending_memory_blocked_count": sum(
            1
            for item in results
            if item["has_pending_memory"] and not item["actual_memory_injected"] and item["severity"] != "hard_fail"
        ),
        "inactive_memory_blocked_count": sum(
            1
            for item in results
            if item["has_inactive_memory"] and not item["actual_memory_injected"] and item["severity"] != "hard_fail"
        ),
        "persona_drift_blocked_count": sum(
            1
            for item in results
            if item["has_persona_drift_memory"] and not item["actual_memory_injected"] and item["severity"] != "hard_fail"
        ),
        "prompt_order_failure_count": sum(1 for item in results if not item["prompt_order_ok"]),
        "reply_mechanic_leak_count": sum(1 for item in results if item["memory_mechanic_leak"]),
        "mechanism_phrase_violation_count": sum(1 for item in results if item["memory_mechanic_leak"]),
        "mechanical_memory_recall_count": sum(1 for item in results if item["mechanical_memory_recall"]),
        "persona_drift_leak_count": sum(1 for item in results if item["persona_drift_leak"]),
        "persona_override_violation_count": sum(1 for item in results if item["persona_drift_leak"]),
        "secret_leak_count": sum(1 for item in results if item["secret_leak"]),
        "current_input_priority_pass_count": sum(1 for item in results if item["prompt_current_input_priority"]),
        "current_input_priority_count": sum(1 for item in results if item["prompt_current_input_priority"]),
        "pending_or_inactive_used_count": sum(1 for item in results if item["pending_or_inactive_used"]),
        "raw_prompt_omitted_count": sum(1 for item in results if item["raw_prompt_omitted"]),
        "live_provider_error_count": sum(1 for item in results if item["provider_error"]),
        "provider_status": "ok" if not any(item["provider_error"] for item in results) else "error",
        "response_too_long_count": sum(
            1 for item in results if item["failure_reason"] and "reply is too long" in item["failure_reason"]
        ),
        "response_too_short_count": sum(
            1 for item in results if item["failure_reason"] and "reply is too short" in item["failure_reason"]
        ),
        "memory_natural_usage_observed_count": sum(
            1 for item in results if item["memory_natural_usage_observed"]
        ),
        "memory_used_naturally_count": sum(
            1 for item in results if item["memory_natural_usage_observed"]
        ),
        "live_review_recommended": bool(warnings or hard_failed),
    }


def _memory_use_counts(memory: PlayerMemory) -> dict[str, int]:
    return {
        str(item.get("id") or ""): int(item.get("use_count") or 0)
        for item in memory.load_profile().long_term_memories
        if isinstance(item, dict) and item.get("id")
    }


def _usage_deltas(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {
        memory_id: int(after.get(memory_id, 0)) - int(before.get(memory_id, 0))
        for memory_id in sorted(set(before) | set(after))
        if int(after.get(memory_id, 0)) != int(before.get(memory_id, 0))
    }


def _prompt_order_ok(prompt: str) -> bool:
    persona_index = prompt.find("Rei Persona Pack")
    memory_index = prompt.find("已验证长期记忆")
    if persona_index < 0 or memory_index < 0:
        return False
    return persona_index < memory_index


def _check_required_terms(text: str, terms: Any, label: str, failures: list[str]) -> None:
    for term in _safe_string_list(terms or []):
        if term not in text:
            failures.append(f"{label} missing required term")


def _check_forbidden_terms(text: str, terms: Any, label: str, failures: list[str]) -> None:
    for term in _safe_string_list(terms or []):
        if _contains_any(text, (term,)):
            failures.append(f"{label} leaked forbidden term")


def _missing_terms(text: str, terms: Any, label: str) -> list[str]:
    return [
        f"{label} missing required term: {term}"
        for term in _safe_string_list(terms or [])
        if term not in text
    ]


def _reply_length_findings(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if "max_reply_sentences" in expected and actual["reply_sentence_count"] > int(expected["max_reply_sentences"]):
        findings.append("reply has too many sentences")
    if "min_reply_sentences" in expected and actual["reply_sentence_count"] < int(expected["min_reply_sentences"]):
        findings.append("reply has too few sentences")
    if "max_reply_chars" in expected and actual["reply_char_count"] > int(expected["max_reply_chars"]):
        findings.append("reply is too long")
    if "min_reply_chars" in expected and actual["reply_char_count"] < int(expected["min_reply_chars"]):
        findings.append("reply is too short")
    return findings


def _current_input_priority_failed(
    scenario: dict[str, Any],
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> bool:
    if not expected.get("current_input_priority"):
        return False
    user_message = str(scenario.get("input") or "")
    reply = str(actual.get("reply") or "")
    asks_for_detail = _contains_any(user_message, CURRENT_INPUT_DETAIL_TERMS)
    refuses_detail = _contains_any(reply, CURRENT_INPUT_REFUSAL_TERMS)
    empty_or_vague = actual["reply_char_count"] < 12 or reply.strip() in {"嗯。", "不知道。", "不清楚。"}
    return asks_for_detail and (refuses_detail or empty_or_vague)


def _memory_natural_usage_observed(
    actual: dict[str, Any],
    *,
    suggested_markers: list[str],
    expected: dict[str, Any],
) -> bool:
    if not actual["retrieved_memory_ids"]:
        return False
    if (
        actual["memory_mechanic_leak"]
        or actual["mechanical_memory_recall"]
        or actual["persona_drift_leak"]
        or actual["secret_leak"]
        or actual["reply_char_count"] <= 0
    ):
        return False
    reply = str(actual.get("reply") or "")
    if _contains_any(reply, suggested_markers) or _contains_any(reply, RELAXED_SEMANTIC_MARKERS):
        return True
    if "max_reply_chars" in expected and actual["reply_char_count"] <= int(expected["max_reply_chars"]):
        return True
    if "max_reply_sentences" in expected and actual["reply_sentence_count"] <= int(expected["max_reply_sentences"]):
        return True
    if actual["prompt_current_input_priority"]:
        return True
    return not suggested_markers and not _safe_string_list(expected.get("reply_must_contain") or [])


def _severity(
    *,
    hard_fail_reasons: list[str],
    warning_reasons: list[str],
    soft_pass_reasons: list[str],
) -> str:
    if hard_fail_reasons:
        return "hard_fail"
    if warning_reasons:
        return "warning"
    if soft_pass_reasons:
        return "soft_pass"
    return "pass"


def _has_safety_boundary_failure(reasons: list[str]) -> bool:
    safety_terms = (
        "memory injection expectation mismatch",
        "retrieved memory ids mismatch",
        "forbidden memory id retrieved",
        "persona pack should remain before memory block",
        "raw prompt omission flag missing",
        "prompt missing current input priority",
        "prompt missing required term",
        "prompt leaked forbidden term",
        "reply leaked forbidden term",
        "reply exposed memory mechanics",
        "reply mechanically recalled memory",
        "reply drifted from persona boundary",
        "secret leaked into prompt or reply",
        "pending or inactive memory was retrieved",
        "provider error:",
    )
    return any(any(reason.startswith(term) for term in safety_terms) for reason in reasons)


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    normalized = text.lower()
    return any(term.lower() in normalized for term in terms if term)


def _sentence_count(reply: str) -> int:
    normalized = re.sub(r"\s+", " ", reply.strip())
    if not normalized:
        return 0
    parts = [part for part in re.split(r"[。！？!?]+|\n+", normalized) if part.strip()]
    return max(1, len(parts))


def _preview(text: str, limit: int = 120) -> str:
    normalized = re.sub(r"\s+", " ", text.strip())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 1)].rstrip()}…"


def _required_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"persona-memory eval scenario missing required text field: {key}")
    return value


def _safe_input_source(value: Any) -> str:
    text = str(value or "text")
    return text if text in ALLOWED_INPUT_SOURCES else "text"


def _safe_optional_text(value: Any) -> str | None:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text or None


def _safe_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _merged_string_list(*values: Any) -> list[str]:
    merged: list[str] = []
    for value in values:
        for item in _safe_string_list(value):
            if item not in merged:
                merged.append(item)
    return merged


def _safe_positive_int(value: Any, *, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default


def assert_report_is_safe(report: dict[str, Any]) -> None:
    serialized = json.dumps(report, ensure_ascii=False).lower()
    for term in SAFE_REPORT_FORBIDDEN_TERMS:
        if term in serialized:
            raise AssertionError("persona-memory eval report leaked unsafe text")
