from __future__ import annotations

import json
import re
import socket
import threading
import time
import urllib.error
import urllib.request
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.elden_ring_knowledge.terminology import normalize_terminology
from app.modules.game_session.state import (
    _abandons_current_boss,
    _clears_current_boss,
    _detect_boss,
    _fails_current_boss,
    _has_passive_death_statement,
    _near_clear_signal,
)

logger = get_logger(__name__)

ALLOWED_GAME_EVENTS = {"failed_attempt", "near_clear", "boss_cleared", "boss_switch", "boss_attempt", "none"}
ALLOWED_MEMORY_TYPES = {
    "guide_preference",
    "playstyle_preference",
    "persona_preference",
    "personal_preference",
    "game_progress",
    "none",
}
ALLOWED_EMOTIONS = {"frustrated", "tired", "calm", "none"}
CONFIDENCE_LABELS = {"high", "medium", "low"}
SHADOW_STATUSES = {"skipped", "succeeded", "failed"}
SHADOW_GAME_OPERATIONS = {"set", "keep", "none", "unknown"}
SHADOW_BOSS_OPERATIONS = {"set", "keep", "clear", "none", "unknown"}
SHADOW_DEATH_OPERATIONS = {"set", "increment", "none", "unknown"}
SHADOW_FRUSTRATION_OPERATIONS = {"raise", "lower", "clear", "keep", "none", "unknown"}
SHADOW_BOSS_CLEARED_OPERATIONS = {"set_true", "set_false", "none", "unknown"}
SHADOW_MEMORY_KINDS = {"playstyle_preference", "game_preference", "progress", "none"}
SHADOW_PROACTIVE_TYPES = {"silent_companion", "frustration_check", "repeated_death", "none"}
SHADOW_GAME_IDS = {"elden_ring", "hollow_knight", "unknown"}
SHADOW_BOSS_IDS = {"margit", "tree_sentinel", "false_knight", "unknown"}
SEMANTIC_LLM_TIMEOUT_SECONDS = 12.0
SEMANTIC_LLM_MIN_TIMEOUT_SECONDS = 8.0
SEMANTIC_LLM_MAX_TIMEOUT_SECONDS = 15.0
SEMANTIC_SHADOW_EVENT_LIMIT = 100
SEMANTIC_SHADOW_EVENT_EXPIRE_SECONDS = 25.0


class SemanticShadowAuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class SemanticShadowProviderConfig:
    provider: str
    api_key: str
    base_url: str
    model: str


@dataclass(frozen=True)
class SemanticShadowProviderResponse:
    content: str
    diagnostics: dict[str, Any]


class SemanticShadowParseError(ValueError):
    def __init__(self, message: str, diagnostics: dict[str, Any] | None = None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


def extract_semantics(
    user_message: str,
    intent: str,
    game_state: dict[str, Any] | None = None,
    session_focus_boss: str | None = None,
    run_llm_shadow: bool = True,
    llm_response_format: bool = True,
    compat_retry_used: bool = False,
    ultra_compact_used: bool = False,
) -> dict[str, Any]:
    start = time.perf_counter()
    normalized_message = normalize_terminology(user_message.strip())
    state = game_state or {}
    rule_result = _rule_result(normalized_message, intent, state, session_focus_boss)
    raw_rule_confidence = _decision_confidence(rule_result)
    ambiguity_reason = _ambiguity_reason(normalized_message)
    rule_confidence = min(raw_rule_confidence, 0.55) if ambiguity_reason else raw_rule_confidence
    should_call_llm, skip_reason = _should_call_llm_shadow(normalized_message, rule_result, rule_confidence, ambiguity_reason)
    llm_called = False
    llm_shadow = _empty_llm_shadow(status="skipped", skip_reason=skip_reason)
    parse_error: str | None = None
    extraction_model = _semantic_extraction_model()
    extraction_latency_ms = 0

    if should_call_llm and run_llm_shadow:
        llm_called = True
        llm_start = time.perf_counter()
        try:
            response = _call_deepseek_flash(
                normalized_message,
                intent,
                state,
                session_focus_boss,
                use_response_format=llm_response_format,
                ultra_compact=ultra_compact_used,
            )
            extraction_latency_ms = int((time.perf_counter() - llm_start) * 1000)
            raw, provider_diagnostics = _shadow_response_parts(
                response,
                response_format_used=llm_response_format,
                compat_retry_used=compat_retry_used,
                ultra_compact_used=ultra_compact_used,
            )
            llm_shadow = _finalize_llm_shadow(
                _parse_llm_shadow_json(raw, normalized_message, provider_diagnostics=provider_diagnostics),
                rule_result,
            )
        except Exception as exc:  # noqa: BLE001 - semantic extraction must never break chat.
            extraction_latency_ms = int((time.perf_counter() - llm_start) * 1000)
            parse_error = _safe_parse_error(exc)
            llm_shadow = _empty_llm_shadow(
                status="failed",
                failure_reason=_shadow_failure_reason(exc),
                candidate_summary=f"失败：{_shadow_failure_reason(exc)}",
                diff_summary="LLM 影子识别失败，未应用状态",
            )
            llm_shadow.update(_shadow_exception_diagnostics(exc, llm_response_format, compat_retry_used, ultra_compact_used))
            logger.warning("semantic extraction shadow skipped parse_error=%s", parse_error)
    elif should_call_llm:
        llm_shadow = _empty_llm_shadow(
            status="skipped",
            skip_reason="shadow_deferred",
            candidate_summary="跳过：shadow_deferred",
            diff_summary="LLM 影子识别后台等待",
        )

    final_decision = deepcopy(rule_result)
    trace = _extraction_trace(
        final_decision=final_decision,
        rule_result=rule_result,
        rule_confidence=rule_confidence,
        fallback_reason=ambiguity_reason or (skip_reason if should_call_llm and skip_reason else None),
        skip_reason=None if llm_called else skip_reason,
        parse_error=parse_error,
        llm_shadow=llm_shadow,
    )
    pending_reason = _pending_reason(final_decision)
    debug = {
        "latest_user_message": _safe_message_summary(normalized_message),
        "rule_result": rule_result,
        "rule_confidence": round(rule_confidence, 3),
        "raw_rule_confidence": round(raw_rule_confidence, 3),
        "ambiguity_detected": bool(ambiguity_reason),
        "fallback_reason": trace["fallback_reason"],
        "source": trace["source"],
        "confidence": trace["confidence"],
        "applied_updates": trace["applied_updates"],
        "extraction_trace": trace,
        "llm_called": llm_called,
        "semantic_extraction_model": extraction_model if llm_called else None,
        "semantic_extraction_latency_ms": extraction_latency_ms,
        "provider_latency_ms": extraction_latency_ms,
        "llm_result": llm_shadow if llm_called and llm_shadow["status"] == "succeeded" else None,
        "llm_shadow": llm_shadow,
        "llm_shadow_status": llm_shadow["status"],
        "llm_shadow_confidence": llm_shadow["confidence"],
        "llm_shadow_summary": llm_shadow["candidate_summary"],
        "llm_shadow_diff": llm_shadow["diff_summary"],
        "final_decision": final_decision,
        "skip_reason": None if llm_called else skip_reason,
        "why_pending_created": pending_reason,
        "latency_ms": int((time.perf_counter() - start) * 1000),
        "parse_error": parse_error,
    }
    _set_latest_debug(debug)
    return debug


def get_latest_semantic_extraction_debug() -> dict[str, Any]:
    return deepcopy(_latest_debug)


def _empty_decision() -> dict[str, Any]:
    return {
        "game_event": {
            "type": "none",
            "boss_name": None,
            "confidence": 0.0,
            "should_update_current_boss": False,
        },
        "memory_candidate": {
            "should_create_pending": False,
            "type": "none",
            "text": "",
            "confidence": 0.0,
            "reason": "",
        },
        "emotion": {
            "type": "none",
            "intensity": 0.0,
        },
    }


def _empty_llm_shadow(
    *,
    status: str = "skipped",
    skip_reason: str | None = "not_run",
    failure_reason: str | None = None,
    candidate_summary: str | None = None,
    diff_summary: str | None = None,
) -> dict[str, Any]:
    status_value = status if status in SHADOW_STATUSES else "skipped"
    return {
        "status": status_value,
        "skip_reason": skip_reason if status_value == "skipped" else None,
        "failure_reason": failure_reason if status_value == "failed" else None,
        "confidence": "low",
        "candidate_summary": candidate_summary or (f"跳过：{skip_reason or 'not_run'}" if status_value == "skipped" else "低置信，未应用"),
        "diff_summary": diff_summary or "规则和 LLM 均无高置信更新",
        "is_game_related": False,
        "game": {"operation": "none", "value": None, "confidence": "low"},
        "boss": {"operation": "none", "value": None, "surface_label": None, "confidence": "low"},
        "death_count": {"operation": "none", "value": None, "confidence": "low"},
        "frustration": {"operation": "none", "confidence": "low"},
        "boss_cleared": {"operation": "none", "confidence": "low"},
        "memory_candidate": {
            "should_create": False,
            "kind": "none",
            "safe_summary": None,
            "confidence": "low",
        },
        "proactive_signal": {
            "type": "none",
            "confidence": "low",
            "reason": "",
        },
        "reasoning_summary": "",
        "response_format_used": None,
        "compat_retry_used": False,
        "ultra_compact_used": False,
        "attempts": [],
        "last_failure": None,
        "json_recovery_stage": "not_run",
        "finish_reason": None,
        "content_length_bucket": "empty",
        "first_char_type": "empty",
    }


_EMPTY_LLM_SHADOW = _empty_llm_shadow()


_latest_debug: dict[str, Any] = {
    "latest_user_message": "",
    "rule_result": _empty_decision(),
    "rule_confidence": 0.0,
    "raw_rule_confidence": 0.0,
    "ambiguity_detected": False,
    "fallback_reason": None,
    "source": "none",
    "confidence": "low",
    "applied_updates": [],
    "extraction_trace": {
        "source": "none",
        "confidence": "low",
        "fallback_reason": None,
        "applied_updates": [],
        "skip_reason": "not_run",
        "parse_error": None,
        "llm_shadow_status": "skipped",
        "llm_shadow_confidence": "low",
        "llm_shadow_summary": "未运行",
        "llm_shadow_diff": "规则和 LLM 均无高置信更新",
    },
    "llm_called": False,
    "semantic_extraction_model": None,
    "semantic_extraction_latency_ms": 0,
    "provider_latency_ms": 0,
    "llm_result": None,
    "llm_shadow": _EMPTY_LLM_SHADOW,
    "llm_shadow_status": "skipped",
    "llm_shadow_confidence": "low",
    "llm_shadow_summary": "未运行",
    "llm_shadow_diff": "规则和 LLM 均无高置信更新",
    "final_decision": _empty_decision(),
    "skip_reason": "not_run",
    "why_pending_created": None,
    "latency_ms": 0,
    "parse_error": None,
}

_shadow_event_lock = threading.Lock()
_shadow_event_next_id = 0
_shadow_trace_next_id = 0
_shadow_events: list[dict[str, Any]] = []
_shadow_pending: dict[str, float] = {}
_shadow_completed_trace_ids: set[str] = set()


def _set_latest_debug(debug: dict[str, Any]) -> None:
    global _latest_debug
    _latest_debug = deepcopy(debug)


def schedule_semantic_shadow_event(debug: dict[str, Any]) -> str:
    global _shadow_trace_next_id
    now = time.time()
    timestamp = _utc_timestamp()
    with _shadow_event_lock:
        _shadow_trace_next_id += 1
        trace_id = f"shadow#{_shadow_trace_next_id}"
        _shadow_pending[trace_id] = now
        _append_shadow_event_locked(
            _shadow_event_from_debug(
                debug,
                trace_id=trace_id,
                timestamp=timestamp,
                phase="scheduled",
                event_status="shadow_deferred",
                summary="LLM 影子识别后台等待",
            )
        )
    return trace_id


def run_semantic_shadow_background(
    user_message: str,
    intent: str,
    game_state: dict[str, Any],
    *,
    session_focus_boss: str | None = None,
    trace_id: str | None = None,
) -> None:
    active_trace_id = trace_id or schedule_semantic_shadow_event(
        {
            "source": "none",
            "confidence": "low",
            "fallback_reason": None,
            "skip_reason": "shadow_deferred",
            "applied_updates": [],
            "llm_shadow": _empty_llm_shadow(skip_reason="shadow_deferred"),
            "llm_shadow_status": "skipped",
            "llm_shadow_confidence": "low",
            "llm_shadow_summary": "跳过：shadow_deferred",
            "llm_shadow_diff": "LLM 影子识别后台等待",
            "semantic_extraction_model": _semantic_extraction_model(),
            "semantic_extraction_latency_ms": 0,
            "parse_error": None,
        }
    )
    try:
        debug = extract_semantics(
            user_message,
            intent,
            game_state,
            session_focus_boss=session_focus_boss,
            run_llm_shadow=True,
        )
        if _should_retry_shadow_without_response_format(debug):
            debug = extract_semantics(
                user_message,
                intent,
                game_state,
                session_focus_boss=session_focus_boss,
                run_llm_shadow=True,
                llm_response_format=False,
                compat_retry_used=True,
            )
        if _should_retry_shadow_ultra_compact(debug):
            debug = extract_semantics(
                user_message,
                intent,
                game_state,
                session_focus_boss=session_focus_boss,
                run_llm_shadow=True,
                llm_response_format=False,
                compat_retry_used=True,
                ultra_compact_used=True,
            )
    except Exception:  # noqa: BLE001 - background observability must not affect chat.
        logger.exception("semantic extraction shadow background task failed")
        record_semantic_shadow_final_event(
            active_trace_id,
            {
                "source": "none",
                "confidence": "low",
                "fallback_reason": None,
                "skip_reason": None,
                "applied_updates": [],
                "parse_error": "semantic_extraction_provider_error",
                "llm_shadow": _empty_llm_shadow(
                    status="failed",
                    failure_reason="cancelled",
                    candidate_summary="失败：cancelled",
                    diff_summary="LLM 影子识别已取消，未应用状态",
                ),
                "llm_shadow_status": "failed",
                "llm_shadow_confidence": "low",
                "llm_shadow_summary": "失败：cancelled",
                "llm_shadow_diff": "LLM 影子识别已取消，未应用状态",
                "semantic_extraction_model": _semantic_extraction_model(),
                "semantic_extraction_latency_ms": 0,
            },
            event_status="shadow_cancelled",
        )
        return
    record_semantic_shadow_final_event(active_trace_id, debug)


def record_semantic_shadow_final_event(
    trace_id: str,
    debug: dict[str, Any],
    *,
    event_status: str | None = None,
) -> None:
    timestamp = _utc_timestamp()
    with _shadow_event_lock:
        if trace_id in _shadow_completed_trace_ids:
            return
        _shadow_pending.pop(trace_id, None)
        _shadow_completed_trace_ids.add(trace_id)
        _trim_completed_trace_ids_locked()
        status = event_status or _shadow_final_event_status(debug)
        _append_shadow_event_locked(
            _shadow_event_from_debug(
                debug,
                trace_id=trace_id,
                timestamp=timestamp,
                phase="final",
                event_status=status,
                summary=_shadow_event_summary(status, debug),
            )
        )


def _should_retry_shadow_without_response_format(debug: dict[str, Any]) -> bool:
    shadow = debug.get("llm_shadow") if isinstance(debug.get("llm_shadow"), dict) else {}
    return (
        shadow.get("status") == "failed"
        and shadow.get("failure_reason") == "invalid_json"
        and shadow.get("response_format_used") is True
        and shadow.get("compat_retry_used") is not True
    )


def _should_retry_shadow_ultra_compact(debug: dict[str, Any]) -> bool:
    shadow = debug.get("llm_shadow") if isinstance(debug.get("llm_shadow"), dict) else {}
    return (
        shadow.get("status") == "failed"
        and shadow.get("failure_reason") == "invalid_json"
        and shadow.get("compat_retry_used") is True
        and shadow.get("ultra_compact_used") is not True
    )


def get_semantic_shadow_events(since_id: int = 0, limit: int = 50) -> dict[str, Any]:
    _expire_stale_shadow_events()
    safe_since = max(0, int(since_id or 0))
    safe_limit = max(1, min(int(limit or 50), SEMANTIC_SHADOW_EVENT_LIMIT))
    with _shadow_event_lock:
        events = [event for event in _shadow_events if int(event.get("id", 0)) > safe_since]
        return {
            "events": deepcopy(events[-safe_limit:]),
            "latest_id": _shadow_event_next_id,
        }


def _append_shadow_event_locked(event: dict[str, Any]) -> None:
    global _shadow_event_next_id
    _shadow_event_next_id += 1
    event["id"] = _shadow_event_next_id
    _shadow_events.append(event)
    del _shadow_events[:-SEMANTIC_SHADOW_EVENT_LIMIT]


def _expire_stale_shadow_events() -> None:
    now = time.time()
    timestamp = _utc_timestamp()
    with _shadow_event_lock:
        expired = [
            trace_id
            for trace_id, scheduled_at in _shadow_pending.items()
            if now - scheduled_at >= SEMANTIC_SHADOW_EVENT_EXPIRE_SECONDS
        ]
        for trace_id in expired:
            _shadow_pending.pop(trace_id, None)
            _shadow_completed_trace_ids.add(trace_id)
            _append_shadow_event_locked(
                {
                    "trace_id": trace_id,
                    "timestamp": timestamp,
                    "phase": "final",
                    "status": "shadow_expired",
                    "source": "none",
                    "confidence": "low",
                    "fallback_reason": None,
                    "skip_reason": None,
                    "parse_error": "semantic_extraction_timeout",
                    "applied_updates": [],
                    "llm_shadow_status": "failed",
                    "llm_shadow_confidence": "low",
                    "llm_shadow_summary": "失败：expired",
                    "llm_shadow_diff": "LLM 影子识别超时或已过期，未应用状态",
                    "semantic_extraction_model": _semantic_extraction_model(),
                    "semantic_extraction_latency_ms": 0,
                }
            )
        if expired:
            _trim_completed_trace_ids_locked()


def _shadow_event_from_debug(
    debug: dict[str, Any],
    *,
    trace_id: str,
    timestamp: str,
    phase: str,
    event_status: str,
    summary: str,
) -> dict[str, Any]:
    trace = debug.get("extraction_trace") if isinstance(debug.get("extraction_trace"), dict) else {}
    shadow = debug.get("llm_shadow") if isinstance(debug.get("llm_shadow"), dict) else {}
    skip_reason = "shadow_deferred" if event_status == "shadow_deferred" else (
        trace.get("skip_reason") or debug.get("skip_reason") or shadow.get("skip_reason")
    )
    return {
        "trace_id": trace_id,
        "timestamp": timestamp,
        "phase": phase,
        "status": event_status,
        "source": _safe_label(trace.get("source") or debug.get("source") or "none"),
        "confidence": _safe_confidence(trace.get("confidence") or debug.get("confidence") or "low"),
        "fallback_reason": _safe_optional_label(trace.get("fallback_reason") or debug.get("fallback_reason")),
        "skip_reason": _safe_optional_label(skip_reason),
        "parse_error": _safe_optional_label(trace.get("parse_error") or debug.get("parse_error")),
        "applied_updates": _safe_label_list(trace.get("applied_updates") or debug.get("applied_updates") or []),
        "llm_shadow_status": _safe_shadow_status(trace.get("llm_shadow_status") or debug.get("llm_shadow_status") or shadow.get("status")),
        "llm_shadow_confidence": _safe_confidence(
            trace.get("llm_shadow_confidence") or debug.get("llm_shadow_confidence") or shadow.get("confidence") or "low"
        ),
        "llm_shadow_summary": _safe_short_text(
            summary
            or trace.get("llm_shadow_summary")
            or debug.get("llm_shadow_summary")
            or shadow.get("candidate_summary")
        ),
        "llm_shadow_diff": _safe_short_text(
            trace.get("llm_shadow_diff")
            or debug.get("llm_shadow_diff")
            or shadow.get("diff_summary")
        ),
        "response_format_used": _safe_bool(shadow.get("response_format_used")),
        "compat_retry_used": _safe_bool(shadow.get("compat_retry_used")),
        "ultra_compact_used": _safe_bool(shadow.get("ultra_compact_used")),
        "attempts": _safe_attempts(shadow.get("attempts")),
        "last_failure": _safe_optional_label(shadow.get("last_failure")),
        "json_recovery_stage": _safe_json_recovery_stage(shadow.get("json_recovery_stage")),
        "finish_reason": _safe_optional_label(shadow.get("finish_reason")),
        "content_length_bucket": _safe_content_length_bucket(shadow.get("content_length_bucket")),
        "first_char_type": _safe_first_char_type(shadow.get("first_char_type")),
        "semantic_extraction_model": _safe_optional_label(debug.get("semantic_extraction_model")),
        "semantic_extraction_latency_ms": max(0, int(debug.get("semantic_extraction_latency_ms") or 0)),
    }


def _shadow_final_event_status(debug: dict[str, Any]) -> str:
    shadow = debug.get("llm_shadow") if isinstance(debug.get("llm_shadow"), dict) else {}
    status = str(debug.get("llm_shadow_status") or shadow.get("status") or "")
    if status == "succeeded":
        return "shadow_succeeded"
    if status == "skipped":
        skip_reason = str(shadow.get("skip_reason") or debug.get("skip_reason") or "")
        if skip_reason == "provider_unavailable":
            return "shadow_provider_unavailable"
        return "shadow_cancelled"
    failure_reason = str(shadow.get("failure_reason") or "")
    if failure_reason == "timeout":
        return "shadow_timeout"
    if failure_reason == "invalid_json":
        return "shadow_invalid_json"
    if failure_reason == "auth_failed":
        return "shadow_auth_failed"
    if failure_reason == "provider_error":
        return "shadow_provider_error"
    if failure_reason == "provider_unavailable":
        return "shadow_provider_unavailable"
    if failure_reason == "cancelled":
        return "shadow_cancelled"
    return "shadow_provider_error"


def _shadow_event_summary(status: str, debug: dict[str, Any]) -> str:
    shadow = debug.get("llm_shadow") if isinstance(debug.get("llm_shadow"), dict) else {}
    candidate = _safe_short_text(debug.get("llm_shadow_summary") or shadow.get("candidate_summary"))
    if status == "shadow_succeeded":
        if shadow.get("ultra_compact_used"):
            return f"LLM 影子识别完成：模式 ultra_compact / {candidate or '候选已生成'}"
        if shadow.get("compat_retry_used"):
            return f"LLM 影子识别完成：兼容模式 / {candidate or '候选已生成'}"
        return f"LLM 影子识别完成：{candidate or '候选已生成'}"
    if status == "shadow_timeout":
        return "LLM 影子识别超时"
    if status == "shadow_invalid_json":
        attempts = ">".join(_safe_attempts(shadow.get("attempts"))) or "normal_json"
        if shadow.get("ultra_compact_used"):
            return f"失败：ultra_compact invalid_json / attempts:{attempts}"
        if shadow.get("compat_retry_used"):
            return f"失败：compat invalid_json / attempts:{attempts}"
        if shadow.get("response_format_used"):
            return "LLM 影子识别失败：invalid_json，尝试兼容模式"
        return "LLM 影子识别失败：invalid_json（已尝试安全恢复）"
    if status == "shadow_auth_failed":
        return "LLM 影子识别失败：auth_failed"
    if status == "shadow_provider_unavailable":
        return "LLM 影子识别跳过：provider_unavailable"
    if status == "shadow_expired":
        return "LLM 影子识别超时或已过期"
    if status == "shadow_cancelled":
        return "LLM 影子识别已取消"
    return "LLM 影子识别失败：provider_error"


def _trim_completed_trace_ids_locked() -> None:
    if len(_shadow_completed_trace_ids) <= SEMANTIC_SHADOW_EVENT_LIMIT * 2:
        return
    active_trace_ids = {str(event.get("trace_id")) for event in _shadow_events[-SEMANTIC_SHADOW_EVENT_LIMIT:]}
    _shadow_completed_trace_ids.intersection_update(active_trace_ids)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_optional_label(value: Any) -> str | None:
    text = _safe_label(value)
    return text or None


def _safe_label(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"(?i)bearer\s+[a-z0-9._-]+", "bearer [redacted]", text)
    text = re.sub(r"(?i)(api[_-]?key|authorization|\.env|stdout|stderr|raw prompt|raw json)", "[redacted]", text)
    text = re.sub(r"/[^\s]+", "[path]", text)
    return text[:80]


def _safe_confidence(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in CONFIDENCE_LABELS else "low"


def _safe_shadow_status(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in SHADOW_STATUSES else "skipped"


def _safe_label_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_safe_label(item) for item in value if _safe_label(item)][:12]


def _safe_attempts(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    allowed = {"normal_json", "compat_retry", "ultra_compact"}
    return [str(item) for item in value if str(item) in allowed][:3]


def _safe_short_text(value: Any) -> str:
    text = _safe_label(value)
    return text[:120]


def _safe_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _safe_json_recovery_stage(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in {"strict", "fenced", "object_extract", "array_first", "failed", "not_run"} else "failed"


def _safe_content_length_bucket(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in {"empty", "short", "medium", "long"} else "empty"


def _safe_first_char_type(value: Any) -> str:
    text = str(value or "").strip()
    return text if text in {"{", "[", "markdown", "prose", "empty", "unknown"} else "unknown"


def _rule_result(
    message: str,
    intent: str,
    game_state: dict[str, Any],
    session_focus_boss: str | None,
) -> dict[str, Any]:
    decision = _empty_decision()
    explicit_boss = _detect_boss(message)
    focused_boss = normalize_terminology(session_focus_boss or "") or None
    context_boss = _context_boss_for_rule(game_state, focused_boss, explicit_boss)
    fails_boss = _fails_current_boss(message)
    clears_boss = _clears_current_boss(message)
    abandons_boss = _abandons_current_boss(message)
    near_clear = _near_clear_signal(_compact(message))
    state_neutral_question = _is_state_neutral_game_question(message, intent)

    if explicit_boss and near_clear:
        decision["game_event"] = _game_event("near_clear", explicit_boss, 0.82, True)
    elif explicit_boss and fails_boss:
        decision["game_event"] = _game_event("failed_attempt", explicit_boss, 0.97, True)
    elif explicit_boss and clears_boss:
        decision["game_event"] = _game_event("boss_cleared", explicit_boss, 0.97, True)
    elif explicit_boss and not state_neutral_question:
        decision["game_event"] = _game_event("boss_attempt", explicit_boss, 0.95, True)
    elif near_clear and context_boss:
        decision["game_event"] = _game_event("near_clear", context_boss, 0.82, True)
    elif fails_boss and context_boss:
        decision["game_event"] = _game_event("failed_attempt", context_boss, 0.9, True)
    elif clears_boss and context_boss:
        decision["game_event"] = _game_event("boss_cleared", context_boss, 0.9, True)
    elif abandons_boss:
        decision["game_event"] = _game_event("boss_switch", context_boss, 0.78, bool(context_boss))

    memory_candidate = _rule_memory_candidate(message)
    if memory_candidate:
        decision["memory_candidate"] = memory_candidate

    emotion = _rule_emotion(message)
    if emotion:
        decision["emotion"] = emotion
    return decision


def _is_state_neutral_game_question(message: str, intent: str) -> bool:
    if intent not in {"elden_ring_boss_strategy", "elden_ring_location", "elden_ring_build", "elden_ring_general_help"}:
        return False
    compact = _compact(message)
    question_markers = (
        "怎么",
        "怎麼",
        "如何",
        "咋",
        "在哪",
        "哪里",
        "哪裡",
        "攻略",
        "打法",
        "二阶段",
        "二階段",
        "一阶段",
        "一階段",
        "推荐",
        "推薦",
        "?",
        "？",
    )
    return any(marker in compact for marker in question_markers)


def _game_event(event_type: str, boss_name: str | None, confidence: float, should_update: bool) -> dict[str, Any]:
    return {
        "type": event_type,
        "boss_name": normalize_terminology(boss_name or "") or None,
        "confidence": _clamp(confidence),
        "should_update_current_boss": should_update,
    }


def _rule_memory_candidate(message: str) -> dict[str, Any] | None:
    compact = _compact(message)
    if _negative_memory_request(compact):
        return None
    if _mentions_short_guide_preference(compact):
        return _memory_candidate("guide_preference", "玩家喜欢简短的游戏攻略", 0.94, "explicit guide preference")
    if _mentions_long_guide_preference(compact):
        return _memory_candidate("guide_preference", "玩家不喜欢长篇攻略", 0.95, "explicit guide preference")
    if _mentions_guide_site_preference(compact):
        return _memory_candidate("guide_preference", "玩家不喜欢攻略站式回答", 0.9, "explicit guide preference")
    if _mentions_spirit_ashes_preference(compact):
        return _memory_candidate("playstyle_preference", "玩家不喜欢召唤骨灰，倾向自己打", 0.95, "explicit playstyle preference")
    if _mentions_exploration_before_boss_preference(compact):
        return _memory_candidate(
            "playstyle_preference",
            "玩家打 Boss 前喜欢先探索地图，不喜欢直接硬打",
            0.94,
            "explicit playstyle memory request",
        )
    if _mentions_persona_preference(compact):
        return _memory_candidate("persona_preference", "玩家表达了对 Rei 表达方式的偏好", 0.68, "possible persona preference")
    personal_preference = _explicit_personal_preference(compact)
    if personal_preference:
        return _memory_candidate("personal_preference", f"玩家{personal_preference}", 0.9, "explicit memory request")
    return None


def _memory_candidate(memory_type: str, text: str, confidence: float, reason: str) -> dict[str, Any]:
    return {
        "should_create_pending": True,
        "type": memory_type,
        "text": normalize_terminology(text),
        "confidence": _clamp(confidence),
        "reason": reason,
    }


def _rule_emotion(message: str) -> dict[str, Any] | None:
    compact = _compact(message)
    if any(marker in compact for marker in ("烦", "烦躁", "红温", "紅溫", "破防", "打不过", "打不過", "过不了", "又死")):
        return {"type": "frustrated", "intensity": 0.75}
    if any(marker in compact for marker in ("累", "困", "熬夜", "凌晨", "不想说话")):
        return {"type": "tired", "intensity": 0.65}
    return None


def _should_call_llm_shadow(
    message: str,
    rule_result: dict[str, Any],
    rule_confidence: float,
    ambiguity_reason: str | None = None,
) -> tuple[bool, str]:
    if not _has_shadow_semantic_signal(message, rule_result, ambiguity_reason):
        return False, "no_semantic_signal"
    if not _shadow_provider_config():
        return False, "provider_unavailable"
    if ambiguity_reason:
        return True, ambiguity_reason
    if rule_confidence < 0.7:
        return True, "low_confidence_rule"
    return True, "shadow_mode_game_semantics"


def _has_shadow_semantic_signal(
    message: str,
    rule_result: dict[str, Any],
    ambiguity_reason: str | None = None,
) -> bool:
    if ambiguity_reason:
        return True
    compact = _compact(message)
    game_event = rule_result.get("game_event") or {}
    if str(game_event.get("type") or "none") != "none":
        return True
    emotion = rule_result.get("emotion") or {}
    if str(emotion.get("type") or "none") in {"frustrated", "tired", "calm"}:
        return True
    memory_candidate = rule_result.get("memory_candidate") or {}
    if memory_candidate.get("should_create_pending") and _has_shadow_game_hint(compact):
        return True
    if _detect_boss(message):
        return True
    return _has_shadow_game_hint(compact) and _has_semantic_signal(message)


def _has_shadow_game_hint(compact: str) -> bool:
    if not compact:
        return False
    game_markers = (
        "艾尔登法环",
        "艾爾登法環",
        "法环",
        "法環",
        "eldenring",
        "elden ring",
        "空洞骑士",
        "空洞騎士",
        "hollowknight",
        "hollow knight",
    )
    boss_or_fight_markers = (
        "boss",
        "大树守卫",
        "大樹守衛",
        "树守卫",
        "樹守衛",
        "玛尔基特",
        "瑪爾基特",
        "恶兆妖鬼",
        "惡兆妖鬼",
        "假骑士",
        "假騎士",
        "骑马",
        "騎馬",
        "打",
        "被打",
        "被杀",
        "被殺",
        "卡住",
        "卡在",
        "过了",
        "過了",
        "击败",
        "擊敗",
    )
    failure_markers = (
        "死了",
        "又死",
        "打死",
        "寄了",
        "薄纱",
        "薄紗",
        "打爆",
        "打不过",
        "打不過",
        "烦",
        "煩",
        "急",
        "心态崩",
        "心態崩",
        "冷静下来",
        "冷靜下來",
    )
    return any(marker in compact for marker in game_markers + boss_or_fight_markers + failure_markers)


def _has_semantic_signal(message: str) -> bool:
    compact = _compact(message)
    if _has_passive_death_statement(message):
        return True
    if _low_confidence_game_semantic_reason(compact):
        return True
    game_markers = (
        "没打过",
        "沒打過",
        "没过",
        "沒過",
        "过不了",
        "過不了",
        "差点过",
        "差點過",
        "差点就过",
        "差點就過",
        "差一点过",
        "差一點過",
        "差一点就过",
        "差一點就過",
        "只剩一点血",
        "只剩一點血",
        "差点赢",
        "差點贏",
        "又死",
        "被杀",
        "被殺",
        "打死",
        "把我杀",
        "把我殺",
        "换一个",
        "換一個",
        "不打这个",
        "不打這個",
        "不打了",
        "之前没打过",
        "之前沒打過",
        "之前没过",
        "之前沒過",
        "之前卡住",
        "重新挑战",
        "重新挑戰",
    )
    memory_markers = (
        "不想",
        "别像",
        "別像",
        "攻略站",
        "记住",
        "記住",
        "记得",
        "記得",
    )
    if any(marker in compact for marker in game_markers):
        return True
    if any(marker in compact for marker in ("记住", "記住", "记得", "記得", "帮我记", "幫我記")):
        return True
    if any(marker in compact for marker in memory_markers) and any(
        topic in compact for topic in ("攻略", "提醒", "回答", "骨灰", "召唤", "召喚")
    ):
        return True
    if any(marker in compact for marker in ("喜欢", "喜歡", "希望", "想要")) and any(
        topic in compact
        for topic in ("简短", "短一点", "短點", "一句", "少一点", "少點", "攻略", "提醒", "笑", "柔和", "温柔", "多回应", "多回應")
    ):
        return True
    return False


def _call_deepseek_flash(
    user_message: str,
    intent: str,
    game_state: dict[str, Any],
    session_focus_boss: str | None,
    *,
    use_response_format: bool = True,
    ultra_compact: bool = False,
) -> str | SemanticShadowProviderResponse:
    provider = _shadow_provider_config()
    if not provider:
        raise RuntimeError("semantic shadow provider unavailable")
    prompt = _ultra_compact_shadow_prompt(user_message, intent, game_state, session_focus_boss) if ultra_compact else {
        "task": "semantic_shadow_json",
        "intent": intent,
        "message": user_message,
        "focus_boss": normalize_terminology(session_focus_boss or "") or None,
        "game_state": _brief_game_state(game_state),
        "allowed": {
            "conf": ["high", "medium", "low"],
            "game": ["elden_ring", "hollow_knight", "unknown", None],
            "boss": ["margit", "tree_sentinel", "false_knight", "unknown", None],
            "op": ["set", "keep", "clear", "none", "unknown", "increment", "raise", "lower", "set_true", "set_false"],
            "proactive": ["silent_companion", "frustration_check", "repeated_death", "none"],
            "memory_kind": ["playstyle_preference", "game_preference", "progress", "none"],
        },
        "format": {
            "related": True,
            "conf": "medium",
            "game": {"op": "unknown", "value": None, "conf": "low"},
            "boss": {"op": "set", "value": "tree_sentinel", "label": "safe short label or null", "conf": "medium"},
            "death": {"op": "unknown", "value": None, "conf": "low"},
            "frustration": {"op": "none", "conf": "low"},
            "cleared": {"op": "none", "conf": "high"},
            "memory": {"create": False, "kind": "none", "summary": None, "conf": "low"},
            "proactive": {"type": "none", "conf": "low"},
            "signals": ["safe short labels only"],
            "summary": "safe short summary, no raw user text",
        },
        "instruction": (
            "Return ONLY one JSON object. No markdown. No prose. No code fences. No chain-of-thought. "
            "只输出一个 JSON 对象，不要解释，不要 Markdown，不要代码块。 "
            "Use the exact compact keys from format. Do not invent state; use unknown/none with low confidence when unsure. "
            "Distinguish player death from boss cleared, and absolute death count from increment. "
            "Memory/proactive are debug candidates only. Do not echo full user text, paths, secrets, stdout/stderr, or raw prompt."
        ),
    }
    payload = {
        "model": provider.model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are ReiLink semantic shadow extractor. Return ONLY one JSON object. "
                    "No markdown, no prose, no code fences, no explanations. "
                    "The result is debug-only and never directly writes app state."
                ),
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": 0,
        "max_tokens": 256 if ultra_compact else 512,
        "stream": False,
    }
    if use_response_format:
        payload["response_format"] = {"type": "json_object"}
    request = urllib.request.Request(
        f"{provider.base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {provider.api_key}"},
        method="POST",
    )
    timeout = _semantic_shadow_timeout_seconds()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        choice = body["choices"][0]
        message = choice.get("message") if isinstance(choice, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        text = str(content or "").strip()
        return SemanticShadowProviderResponse(
            content=text,
            diagnostics={
                "response_format_used": use_response_format,
                "ultra_compact_used": ultra_compact,
                "finish_reason": _safe_optional_label(choice.get("finish_reason") if isinstance(choice, dict) else None),
                "content_length_bucket": _content_length_bucket(text),
                "first_char_type": _first_char_type(text),
            },
        )
    except socket.timeout as exc:
        raise TimeoutError(f"semantic extraction timed out after {timeout:g}s") from exc
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise SemanticShadowAuthError(f"semantic extraction auth failed: HTTP {exc.code}") from exc
        raise RuntimeError(f"semantic extraction provider failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError | socket.timeout):
            raise TimeoutError(f"semantic extraction timed out after {timeout:g}s") from exc
        raise RuntimeError(f"semantic extraction provider failed: {exc}") from exc
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"semantic extraction provider returned invalid response: {exc}") from exc


def _ultra_compact_shadow_prompt(
    user_message: str,
    intent: str,
    game_state: dict[str, Any],
    session_focus_boss: str | None,
) -> dict[str, Any]:
    return {
        "task": "semantic_shadow_ultra_json",
        "intent": intent,
        "message": user_message,
        "focus_boss": normalize_terminology(session_focus_boss or "") or None,
        "game_state": _brief_game_state(game_state),
        "allowed": {
            "conf": ["low", "medium", "high"],
            "game": ["elden_ring", "hollow_knight", "unknown", None],
            "boss": ["margit", "tree_sentinel", "false_knight", "unknown", None],
            "frustration": ["none", "raise", "lower"],
        },
        "format": {
            "related": True,
            "conf": "medium",
            "game": "elden_ring",
            "boss": "tree_sentinel",
            "failure": True,
            "death_count": None,
            "frustration": "raise",
            "signals": ["unknown_boss_alias"],
            "summary": "short safe summary",
        },
        "instruction": (
            "Return ONLY this tiny JSON object. No markdown. No prose. No code fences. "
            "只输出极简 JSON 对象，不要解释。Use null/unknown when unsure. "
            "Do not echo full user text, paths, secrets, stdout/stderr, or raw prompt."
        ),
    }


def _semantic_extraction_model() -> str:
    provider = _shadow_provider_config()
    if provider:
        return provider.model
    return settings.deepseek_model_fast or "deepseek-chat"


def _shadow_provider_config() -> SemanticShadowProviderConfig | None:
    provider = settings.llm_provider.lower().strip()
    if provider == "deepseek":
        api_key = settings.deepseek_api_key.strip()
        if not api_key:
            return None
        return SemanticShadowProviderConfig(
            provider="deepseek",
            api_key=api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model_fast or settings.deepseek_model or "deepseek-chat",
        )
    if provider in {"openai", "openai-compatible"}:
        api_key = settings.openai_api_key.strip()
        if not api_key:
            return None
        return SemanticShadowProviderConfig(
            provider="openai",
            api_key=api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model or "gpt-4o-mini",
        )
    return None


def _semantic_shadow_timeout_seconds() -> float:
    configured = float(settings.llm_timeout_seconds or SEMANTIC_LLM_TIMEOUT_SECONDS)
    return max(SEMANTIC_LLM_MIN_TIMEOUT_SECONDS, min(configured, SEMANTIC_LLM_MAX_TIMEOUT_SECONDS))


def _shadow_response_parts(
    response: str | SemanticShadowProviderResponse,
    *,
    response_format_used: bool,
    compat_retry_used: bool,
    ultra_compact_used: bool,
) -> tuple[str, dict[str, Any]]:
    if isinstance(response, SemanticShadowProviderResponse):
        diagnostics = dict(response.diagnostics)
        diagnostics["response_format_used"] = bool(diagnostics.get("response_format_used", response_format_used))
        diagnostics["compat_retry_used"] = compat_retry_used
        diagnostics["ultra_compact_used"] = bool(diagnostics.get("ultra_compact_used", ultra_compact_used))
        diagnostics["attempts"] = _shadow_attempts(response_format_used, compat_retry_used, ultra_compact_used)
        return response.content, diagnostics
    text = str(response or "").strip()
    return text, {
        "response_format_used": response_format_used,
        "compat_retry_used": compat_retry_used,
        "ultra_compact_used": ultra_compact_used,
        "attempts": _shadow_attempts(response_format_used, compat_retry_used, ultra_compact_used),
        "finish_reason": None,
        "content_length_bucket": _content_length_bucket(text),
        "first_char_type": _first_char_type(text),
    }


def _shadow_json_diagnostics(raw: str, provider_diagnostics: dict[str, Any] | None = None) -> dict[str, Any]:
    text = str(raw or "").lstrip("\ufeff").strip()
    diagnostics = dict(provider_diagnostics or {})
    diagnostics.setdefault("response_format_used", None)
    diagnostics.setdefault("compat_retry_used", False)
    diagnostics.setdefault("ultra_compact_used", False)
    diagnostics["attempts"] = _safe_attempts(diagnostics.get("attempts"))
    diagnostics["last_failure"] = _safe_optional_label(diagnostics.get("last_failure"))
    diagnostics["finish_reason"] = _safe_optional_label(diagnostics.get("finish_reason"))
    diagnostics["content_length_bucket"] = _safe_content_length_bucket(
        diagnostics.get("content_length_bucket") or _content_length_bucket(text)
    )
    diagnostics["first_char_type"] = _safe_first_char_type(diagnostics.get("first_char_type") or _first_char_type(text))
    diagnostics.setdefault("json_recovery_stage", "failed")
    return diagnostics


def _shadow_attempts(response_format_used: bool, compat_retry_used: bool, ultra_compact_used: bool) -> list[str]:
    attempts = ["normal_json"]
    if compat_retry_used:
        attempts.append("compat_retry")
    if ultra_compact_used:
        attempts.append("ultra_compact")
    return attempts


def _content_length_bucket(text: str) -> str:
    length = len(str(text or "").strip())
    if length == 0:
        return "empty"
    if length <= 256:
        return "short"
    if length <= 1200:
        return "medium"
    return "long"


def _first_char_type(text: str) -> str:
    stripped = str(text or "").lstrip("\ufeff").strip()
    if not stripped:
        return "empty"
    if stripped.startswith("{"):
        return "{"
    if stripped.startswith("["):
        return "["
    if stripped.startswith("```"):
        return "markdown"
    if stripped[0].isalnum() or "\u4e00" <= stripped[0] <= "\u9fff":
        return "prose"
    return "unknown"


def _parse_llm_shadow_json(
    raw: str,
    user_message: str,
    *,
    provider_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diagnostics = _shadow_json_diagnostics(raw, provider_diagnostics)
    try:
        parsed, recovered, stage = _load_llm_shadow_json(raw)
    except ValueError as exc:
        diagnostics["json_recovery_stage"] = "failed"
        raise SemanticShadowParseError("LLM semantic extraction did not return valid JSON", diagnostics) from exc
    shadow = _normalize_llm_shadow(parsed, user_message)
    shadow["json_recovered"] = recovered
    diagnostics["json_recovery_stage"] = stage
    shadow.update(diagnostics)
    return shadow


def _load_llm_shadow_json(raw: str) -> tuple[dict[str, Any], bool, str]:
    text = str(raw or "").lstrip("\ufeff").strip()
    parsed = _loads_shadow_json_value(text)
    if isinstance(parsed, dict):
        return parsed, False, "strict"
    if isinstance(parsed, list):
        first = _first_dict(parsed)
        if first is not None:
            return first, True, "array_first"

    unfenced = _strip_json_fence(text)
    if unfenced != text:
        parsed = _loads_shadow_json_value(unfenced)
        if isinstance(parsed, dict):
            return parsed, True, "fenced"
        if isinstance(parsed, list):
            first = _first_dict(parsed)
            if first is not None:
                return first, True, "array_first"

    object_text = _extract_first_json_object(unfenced)
    if object_text:
        parsed = _loads_shadow_json_value(object_text)
        if isinstance(parsed, dict):
            return parsed, True, "object_extract"

    raise ValueError("LLM semantic extraction did not return valid JSON")


def _loads_shadow_json_value(text: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None


def _first_dict(value: list[Any]) -> dict[str, Any] | None:
    for item in value:
        if isinstance(item, dict):
            return item
    return None


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```(?:json|JSON)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    return match.group(1).strip() if match else stripped


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(text[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == "\"":
                in_string = False
            continue
        if char == "\"":
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _normalize_llm_shadow(data: dict[str, Any], user_message: str) -> dict[str, Any]:
    data = _expand_compact_llm_shadow(data)
    shadow = _empty_llm_shadow(status="succeeded", skip_reason=None)
    shadow["is_game_related"] = bool(data.get("is_game_related"))
    shadow["confidence"] = _shadow_confidence(data.get("confidence"))

    game = data.get("game")
    if isinstance(game, dict):
        shadow["game"] = {
            "operation": _shadow_operation(game.get("operation"), SHADOW_GAME_OPERATIONS),
            "value": _shadow_game_value(game.get("value")),
            "confidence": _shadow_confidence(game.get("confidence")),
        }

    boss = data.get("boss")
    if isinstance(boss, dict):
        shadow["boss"] = {
            "operation": _shadow_operation(boss.get("operation"), SHADOW_BOSS_OPERATIONS),
            "value": _shadow_boss_value(boss.get("value")),
            "surface_label": _sanitize_shadow_text(boss.get("surface_label"), user_message, 24) or None,
            "confidence": _shadow_confidence(boss.get("confidence")),
        }

    death_count = data.get("death_count")
    if isinstance(death_count, dict):
        operation = _shadow_operation(death_count.get("operation"), SHADOW_DEATH_OPERATIONS)
        shadow["death_count"] = {
            "operation": operation,
            "value": _shadow_death_count_value(death_count.get("value")) if operation in {"set", "increment"} else None,
            "confidence": _shadow_confidence(death_count.get("confidence")),
        }

    frustration = data.get("frustration")
    if isinstance(frustration, dict):
        shadow["frustration"] = {
            "operation": _shadow_operation(frustration.get("operation"), SHADOW_FRUSTRATION_OPERATIONS),
            "confidence": _shadow_confidence(frustration.get("confidence")),
        }

    boss_cleared = data.get("boss_cleared")
    if isinstance(boss_cleared, dict):
        shadow["boss_cleared"] = {
            "operation": _shadow_operation(boss_cleared.get("operation"), SHADOW_BOSS_CLEARED_OPERATIONS),
            "confidence": _shadow_confidence(boss_cleared.get("confidence")),
        }

    memory_candidate = data.get("memory_candidate")
    if isinstance(memory_candidate, dict):
        kind = str(memory_candidate.get("kind") or "none").strip()
        if kind not in SHADOW_MEMORY_KINDS:
            kind = "none"
        safe_summary = _sanitize_shadow_text(memory_candidate.get("safe_summary"), user_message, 64)
        shadow["memory_candidate"] = {
            "should_create": bool(memory_candidate.get("should_create")) and kind != "none" and bool(safe_summary),
            "kind": kind,
            "safe_summary": safe_summary or None,
            "confidence": _shadow_confidence(memory_candidate.get("confidence")),
        }

    proactive_signal = data.get("proactive_signal")
    if isinstance(proactive_signal, dict):
        signal_type = str(proactive_signal.get("type") or "none").strip()
        if signal_type not in SHADOW_PROACTIVE_TYPES:
            signal_type = "none"
        shadow["proactive_signal"] = {
            "type": signal_type,
            "confidence": _shadow_confidence(proactive_signal.get("confidence")),
            "reason": _sanitize_shadow_text(proactive_signal.get("reason"), user_message, 48),
        }

    shadow["reasoning_summary"] = _sanitize_shadow_text(data.get("reasoning_summary"), user_message, 96)
    return shadow


def _expand_compact_llm_shadow(data: dict[str, Any]) -> dict[str, Any]:
    ultra = _expand_ultra_compact_llm_shadow(data)
    if ultra is not None:
        return {**data, **ultra}
    if not any(key in data for key in ("related", "conf", "death", "cleared", "memory", "proactive", "summary")):
        return data
    expanded = {
        "is_game_related": data.get("is_game_related", data.get("related", False)),
        "confidence": data.get("confidence", data.get("conf", "low")),
        "game": _expand_compact_operation(data.get("game")),
        "boss": _expand_compact_boss(data.get("boss")),
        "death_count": _expand_compact_operation(data.get("death") or data.get("death_count")),
        "frustration": _expand_compact_operation(data.get("frustration")),
        "boss_cleared": _expand_compact_operation(data.get("cleared") or data.get("boss_cleared")),
        "memory_candidate": _expand_compact_memory(data.get("memory") or data.get("memory_candidate")),
        "proactive_signal": _expand_compact_proactive(data.get("proactive") or data.get("proactive_signal")),
        "reasoning_summary": data.get("reasoning_summary", data.get("summary", "")),
    }
    return {**data, **expanded}


def _expand_ultra_compact_llm_shadow(data: dict[str, Any]) -> dict[str, Any] | None:
    if not (
        "failure" in data
        or isinstance(data.get("game"), str)
        or isinstance(data.get("boss"), str)
        or isinstance(data.get("frustration"), str)
    ):
        return None
    confidence = data.get("confidence", data.get("conf", "low"))
    failure = _shadow_bool(data.get("failure"))
    death_value = data.get("death_count")
    death_operation = "increment" if _shadow_death_count_value(death_value) is not None else ("unknown" if failure else "none")
    return {
        "is_game_related": data.get("is_game_related", data.get("related", False)),
        "confidence": confidence,
        "game": _expand_ultra_scalar_operation(data.get("game"), confidence, SHADOW_GAME_IDS),
        "boss": _expand_ultra_boss(data.get("boss"), confidence),
        "death_count": {
            "operation": death_operation,
            "value": _shadow_death_count_value(death_value),
            "confidence": confidence,
        },
        "frustration": {
            "operation": _shadow_operation(data.get("frustration"), {"raise", "lower", "none"}),
            "confidence": confidence,
        },
        "boss_cleared": {"operation": "none", "confidence": "high"},
        "memory_candidate": {"should_create": False, "kind": "none", "safe_summary": None, "confidence": "low"},
        "proactive_signal": {"type": "none", "confidence": "low", "reason": ""},
        "reasoning_summary": data.get("reasoning_summary", data.get("summary", "")),
    }


def _expand_ultra_scalar_operation(value: Any, confidence: Any, allowed_values: set[str]) -> dict[str, Any]:
    if value is None or value == "":
        return {"operation": "none", "value": None, "confidence": confidence}
    text = str(value).strip()
    if text == "unknown":
        return {"operation": "unknown", "value": "unknown", "confidence": confidence}
    if text in allowed_values:
        return {"operation": "set", "value": text, "confidence": confidence}
    return {"operation": "unknown", "value": "unknown", "confidence": "low"}


def _expand_ultra_boss(value: Any, confidence: Any) -> dict[str, Any]:
    expanded = _expand_ultra_scalar_operation(value, confidence, SHADOW_BOSS_IDS)
    expanded["surface_label"] = None
    return expanded


def _shadow_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "yes", "1"}:
            return True
        if text in {"false", "no", "0", "none", "null", "unknown"}:
            return False
    return False


def _expand_compact_operation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "operation": value.get("operation", value.get("op", "none")),
        "value": value.get("value"),
        "confidence": value.get("confidence", value.get("conf", "low")),
    }


def _expand_compact_boss(value: Any) -> dict[str, Any]:
    expanded = _expand_compact_operation(value)
    if isinstance(value, dict):
        expanded["surface_label"] = value.get("surface_label", value.get("label"))
    return expanded


def _expand_compact_memory(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "should_create": value.get("should_create", value.get("create", False)),
        "kind": value.get("kind", "none"),
        "safe_summary": value.get("safe_summary", value.get("summary")),
        "confidence": value.get("confidence", value.get("conf", "low")),
    }


def _expand_compact_proactive(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "type": value.get("type", "none"),
        "confidence": value.get("confidence", value.get("conf", "low")),
        "reason": value.get("reason", ""),
    }


def _finalize_llm_shadow(shadow: dict[str, Any], rule_result: dict[str, Any]) -> dict[str, Any]:
    finalized = deepcopy(shadow)
    finalized["candidate_summary"] = _shadow_candidate_summary(finalized)
    if finalized.get("json_recovered") and finalized["candidate_summary"]:
        finalized["candidate_summary"] = _append_json_recovered_summary(finalized["candidate_summary"])
    finalized["diff_summary"] = _shadow_diff_summary(rule_result, finalized)
    return finalized


def _append_json_recovered_summary(summary: str) -> str:
    suffix = "JSON 已安全恢复"
    if suffix in summary:
        return summary
    combined = f"{summary} / {suffix}"
    return combined if len(combined) <= 96 else f"{summary[: max(0, 93 - len(suffix))]}… / {suffix}"


def _shadow_confidence(value: Any) -> str:
    label = str(value or "").lower().strip()
    return label if label in CONFIDENCE_LABELS else "low"


def _shadow_operation(value: Any, allowed: set[str]) -> str:
    operation = str(value or "none").lower().strip()
    return operation if operation in allowed else "unknown"


def _shadow_game_value(value: Any) -> str | None:
    if value is None or value == "":
        return None
    raw = normalize_terminology(str(value)).lower().strip()
    key = raw.replace("-", "_").replace(" ", "_")
    compact = _compact(raw)
    aliases = {
        "elden_ring": "elden_ring",
        "eldenring": "elden_ring",
        "艾尔登法环": "elden_ring",
        "艾爾登法環": "elden_ring",
        "法环": "elden_ring",
        "法環": "elden_ring",
        "hollow_knight": "hollow_knight",
        "hollowknight": "hollow_knight",
        "空洞骑士": "hollow_knight",
        "空洞騎士": "hollow_knight",
        "unknown": "unknown",
    }
    return aliases.get(key) or aliases.get(compact) or (key if key in SHADOW_GAME_IDS else "unknown")


def _shadow_boss_value(value: Any) -> str | None:
    if value is None or value == "":
        return None
    raw = normalize_terminology(str(value)).lower().strip()
    key = raw.replace("-", "_").replace(" ", "_")
    compact = _compact(raw)
    aliases = {
        "margit": "margit",
        "恶兆妖鬼": "margit",
        "惡兆妖鬼": "margit",
        "恶兆妖鬼margit": "margit",
        "玛尔基特": "margit",
        "瑪爾基特": "margit",
        "tree_sentinel": "tree_sentinel",
        "treesentinel": "tree_sentinel",
        "大树守卫": "tree_sentinel",
        "大樹守衛": "tree_sentinel",
        "树守卫": "tree_sentinel",
        "樹守衛": "tree_sentinel",
        "false_knight": "false_knight",
        "falseknight": "false_knight",
        "假骑士": "false_knight",
        "假騎士": "false_knight",
        "unknown": "unknown",
    }
    return aliases.get(key) or aliases.get(compact) or (key if key in SHADOW_BOSS_IDS else "unknown")


def _shadow_death_count_value(value: Any) -> int | None:
    try:
        return max(0, min(99, int(value)))
    except (TypeError, ValueError):
        return None


def _sanitize_shadow_text(value: Any, user_message: str, max_length: int) -> str:
    text = normalize_terminology(str(value or "")).strip()
    if not text:
        return ""
    if user_message and user_message in text:
        text = text.replace(user_message, "用户原文")
    text = re.sub(r"/(?:Users|private|tmp|var|opt|Applications|Volumes)[^\s，。；;,，)）]+", "[本地路径]", text)
    text = re.sub(r"[A-Za-z]:\\[^\s，。；;,，)）]+", "[本地路径]", text)
    text = re.sub(r"(?i)\b[\w.-]*\.env\b", "[敏感配置]", text)
    text = re.sub(r"(?i)\b\w*api[_-]?key\b[^\s，。；;,，)）]*", "[密钥]", text)
    text = re.sub(r"(?i)\b(?:authorization|bearer|sk-[a-z0-9_-]+)\b[^\s，。；;,，)）]*", "[密钥]", text)
    text = re.sub(r"(?i)raw[_\s-]*(?:prompt|json)|stdout|stderr", "[调试内容]", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= max_length else f"{text[: max_length - 1]}…"


def _shadow_candidate_summary(shadow: dict[str, Any]) -> str:
    status = str(shadow.get("status") or "skipped")
    if status == "skipped":
        return f"跳过：{shadow.get('skip_reason') or 'not_run'}"
    if status == "failed":
        return f"失败：{shadow.get('failure_reason') or 'invalid_json'}"
    if not shadow.get("is_game_related") and not _shadow_has_candidate(shadow):
        return "非游戏语义或低置信，未应用"

    parts: list[str] = []
    game = shadow.get("game") or {}
    if game.get("operation") in {"set", "keep"} and game.get("value"):
        parts.append(f"游戏候选：{_shadow_game_label(str(game.get('value')))}")

    boss = shadow.get("boss") or {}
    if boss.get("operation") in {"set", "keep", "clear", "unknown"}:
        boss_label = _shadow_boss_label(boss.get("value")) or str(boss.get("surface_label") or "")
        if boss_label:
            parts.append(f"Boss 候选：{boss_label}")

    death = shadow.get("death_count") or {}
    if death.get("operation") in {"set", "increment"}:
        value = death.get("value")
        parts.append(f"失败次数候选：{death.get('operation')}{f' {value}' if value is not None else ''}")

    frustration = shadow.get("frustration") or {}
    if frustration.get("operation") in {"raise", "lower", "clear"}:
        parts.append(f"挫败：{frustration.get('operation')}")

    cleared = shadow.get("boss_cleared") or {}
    if cleared.get("operation") in {"set_true", "set_false"}:
        parts.append(f"击败状态：{cleared.get('operation')}")

    memory = shadow.get("memory_candidate") or {}
    if memory.get("should_create"):
        parts.append(f"记忆候选：{memory.get('kind')}")

    proactive = shadow.get("proactive_signal") or {}
    if proactive.get("type") and proactive.get("type") != "none":
        parts.append(f"主动信号：{proactive.get('type')}")

    summary = " / ".join(parts) or "低置信，未应用"
    return summary if len(summary) <= 96 else f"{summary[:95]}…"


def _shadow_diff_summary(rule_result: dict[str, Any], shadow: dict[str, Any]) -> str:
    rule_updates = _applied_updates(rule_result)
    if shadow.get("status") == "skipped":
        return "LLM 影子识别未运行"
    if shadow.get("status") == "failed":
        return "LLM 影子识别失败，未应用状态"
    if not rule_updates and not _shadow_has_candidate(shadow):
        return "规则和 LLM 均无高置信更新"

    boss = shadow.get("boss") or {}
    boss_label = _shadow_boss_label(boss.get("value")) or str(boss.get("surface_label") or "")
    death = shadow.get("death_count") or {}
    if not rule_updates and boss_label:
        return f"规则未识别，LLM 认为可能是 {boss_label}"
    if "emotion_frustrated" in rule_updates and death.get("operation") in {"set", "increment"}:
        return "规则识别挫败，LLM 还识别到失败次数"

    rule_boss = ((rule_result.get("game_event") or {}).get("boss_name") or "").strip()
    if rule_boss and boss_label and normalize_terminology(rule_boss) != normalize_terminology(boss_label):
        return "规则和 LLM Boss 候选不同"
    return "规则结果保留，LLM 候选未应用"


def _shadow_has_candidate(shadow: dict[str, Any]) -> bool:
    game = shadow.get("game") or {}
    boss = shadow.get("boss") or {}
    death = shadow.get("death_count") or {}
    frustration = shadow.get("frustration") or {}
    cleared = shadow.get("boss_cleared") or {}
    memory = shadow.get("memory_candidate") or {}
    proactive = shadow.get("proactive_signal") or {}
    return bool(
        game.get("operation") in {"set", "keep"}
        or boss.get("operation") in {"set", "keep", "clear", "unknown"}
        or death.get("operation") in {"set", "increment"}
        or frustration.get("operation") in {"raise", "lower", "clear"}
        or cleared.get("operation") in {"set_true", "set_false"}
        or memory.get("should_create")
        or (proactive.get("type") and proactive.get("type") != "none")
    )


def _shadow_game_label(value: str | None) -> str:
    return {
        "elden_ring": "艾尔登法环",
        "hollow_knight": "空洞骑士",
        "unknown": "未知游戏",
    }.get(str(value or ""), "")


def _shadow_boss_label(value: Any) -> str:
    return {
        "margit": "恶兆妖鬼 Margit",
        "tree_sentinel": "大树守卫",
        "false_knight": "假骑士",
        "unknown": "未知 Boss 指代",
    }.get(str(value or ""), "")


def _extraction_trace(
    final_decision: dict[str, Any],
    rule_result: dict[str, Any],
    rule_confidence: float,
    fallback_reason: str | None,
    skip_reason: str | None,
    parse_error: str | None,
    llm_shadow: dict[str, Any],
) -> dict[str, Any]:
    final_confidence = _decision_confidence(final_decision)
    if final_confidence <= 0:
        source = "none"
    else:
        source = "rule"
    return {
        "source": source,
        "confidence": _confidence_label(max(final_confidence, rule_confidence)),
        "fallback_reason": fallback_reason,
        "skip_reason": skip_reason,
        "parse_error": parse_error,
        "applied_updates": _applied_updates(final_decision),
        "llm_shadow_status": llm_shadow.get("status"),
        "llm_shadow_confidence": llm_shadow.get("confidence"),
        "llm_shadow_summary": llm_shadow.get("candidate_summary"),
        "llm_shadow_diff": llm_shadow.get("diff_summary"),
    }


def _safe_parse_error(exc: Exception) -> str:
    if isinstance(exc, SemanticShadowAuthError):
        return "semantic_extraction_auth_failed"
    if isinstance(exc, TimeoutError):
        return "semantic_extraction_timeout"
    if isinstance(exc, (json.JSONDecodeError, ValueError)):
        return "semantic_extraction_parse_error"
    return "semantic_extraction_provider_error"


def _shadow_exception_diagnostics(
    exc: Exception,
    response_format_used: bool,
    compat_retry_used: bool,
    ultra_compact_used: bool,
) -> dict[str, Any]:
    if isinstance(exc, SemanticShadowParseError):
        diagnostics = _shadow_json_diagnostics("", exc.diagnostics)
    else:
        diagnostics = _shadow_json_diagnostics(
            "",
            {
                "response_format_used": response_format_used,
                "compat_retry_used": compat_retry_used,
                "ultra_compact_used": ultra_compact_used,
                "attempts": _shadow_attempts(response_format_used, compat_retry_used, ultra_compact_used),
                "json_recovery_stage": "failed",
            },
        )
    diagnostics["response_format_used"] = response_format_used if diagnostics.get("response_format_used") is None else diagnostics["response_format_used"]
    diagnostics["compat_retry_used"] = compat_retry_used
    diagnostics["ultra_compact_used"] = ultra_compact_used
    diagnostics["attempts"] = _shadow_attempts(response_format_used, compat_retry_used, ultra_compact_used)
    diagnostics["last_failure"] = _shadow_failure_reason(exc)
    diagnostics["json_recovery_stage"] = _safe_json_recovery_stage(diagnostics.get("json_recovery_stage"))
    return diagnostics


def _shadow_failure_reason(exc: Exception) -> str:
    if isinstance(exc, SemanticShadowAuthError):
        return "auth_failed"
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, (json.JSONDecodeError, ValueError)):
        return "invalid_json"
    return "provider_error"


def _confidence_label(value: float) -> str:
    if value >= 0.9:
        return "high"
    if value >= 0.7:
        return "medium"
    return "low"


def _applied_updates(decision: dict[str, Any]) -> list[str]:
    updates: list[str] = []
    game_event = decision.get("game_event") or {}
    event_type = str(game_event.get("type") or "none")
    if event_type in {"failed_attempt", "near_clear"}:
        updates.append("boss_failed")
    elif event_type == "boss_cleared":
        updates.append("boss_cleared")
    elif event_type == "boss_attempt":
        updates.append("boss_changed")
    elif event_type == "boss_switch":
        updates.append("boss_switched")
    if game_event.get("boss_name") and event_type != "none":
        updates.append("boss_detected")

    memory_candidate = decision.get("memory_candidate") or {}
    if memory_candidate.get("should_create_pending"):
        updates.append("memory_candidate_created")

    emotion = decision.get("emotion") or {}
    emotion_type = str(emotion.get("type") or "none")
    if emotion_type == "frustrated":
        updates.append("emotion_frustrated")
    elif emotion_type == "tired":
        updates.append("emotion_tired")
    elif emotion_type == "calm":
        updates.append("emotion_calm")
    return updates


def _safe_message_summary(message: str) -> str:
    compact = _compact(message)
    if _has_passive_death_statement(message):
        return f"被动死亡表达 / {len(message)} 字"
    if _low_confidence_game_semantic_reason(compact):
        return f"低置信游戏语义 / {len(message)} 字"
    if any(marker in compact for marker in ("记住", "記住", "记得", "記得", "帮我记", "幫我記")):
        return f"记忆偏好表达 / {len(message)} 字"
    if _has_semantic_signal(message):
        return f"游戏状态表达 / {len(message)} 字"
    return f"无明显语义信号 / {len(message)} 字"


def _pending_reason(decision: dict[str, Any]) -> str | None:
    candidate = decision.get("memory_candidate") or {}
    if not candidate.get("should_create_pending"):
        return None
    return str(candidate.get("reason") or candidate.get("type") or "semantic_candidate")


def _decision_confidence(decision: dict[str, Any]) -> float:
    game_confidence = float((decision.get("game_event") or {}).get("confidence") or 0)
    memory_confidence = float((decision.get("memory_candidate") or {}).get("confidence") or 0)
    emotion_confidence = float((decision.get("emotion") or {}).get("intensity") or 0)
    return max(game_confidence, memory_confidence, emotion_confidence)


def _brief_game_state(game_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_game": game_state.get("current_game"),
        "current_boss": _state_boss(game_state.get("current_boss")),
        "current_activity": game_state.get("current_activity"),
        "last_failed_boss": _state_boss(game_state.get("last_failed_boss")),
        "last_attempted_boss": _state_boss(game_state.get("last_attempted_boss")),
        "last_cleared_boss": _state_boss(game_state.get("last_cleared_boss")),
        "boss_history": [
            {
                "name": _state_boss(item.get("name")),
                "status": item.get("status"),
                "freshness": item.get("freshness"),
            }
            for item in (game_state.get("boss_history") or [])[-5:]
            if isinstance(item, dict)
        ],
    }


def _state_boss(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("name")
    text = normalize_terminology(str(value or "")).strip()
    return text or None


def _context_boss_for_rule(
    game_state: dict[str, Any],
    focused_boss: str | None,
    explicit_boss: str | None,
) -> str | None:
    if explicit_boss:
        return explicit_boss
    current_boss = _state_boss(game_state.get("current_boss"))
    if current_boss:
        return current_boss
    if focused_boss and _history_status(game_state, focused_boss) != "cleared":
        return focused_boss
    last_failed = _state_boss(game_state.get("last_failed_boss"))
    if last_failed and _history_status(game_state, last_failed) != "cleared":
        return last_failed
    unresolved = _latest_unresolved_boss(game_state)
    if unresolved:
        return unresolved
    last_attempted = _state_boss(game_state.get("last_attempted_boss"))
    if last_attempted and _history_status(game_state, last_attempted) != "cleared":
        return last_attempted
    return None


def _history_status(game_state: dict[str, Any], boss_name: str | None) -> str | None:
    if not boss_name:
        return None
    for item in reversed(game_state.get("boss_history") or []):
        if isinstance(item, dict) and _state_boss(item.get("name")) == boss_name:
            return str(item.get("status") or "")
    return None


def _latest_unresolved_boss(game_state: dict[str, Any]) -> str | None:
    names: list[str] = []
    for item in game_state.get("boss_history") or []:
        if not isinstance(item, dict):
            continue
        boss_name = _state_boss(item.get("name"))
        if not boss_name:
            continue
        status = str(item.get("status") or "")
        if status in {"failed", "current", "attempted", "abandoned"}:
            names = [name for name in names if name != boss_name]
            names.append(boss_name)
        elif status == "cleared":
            names = [name for name in names if name != boss_name]
    return names[-1] if names else None


def _ambiguity_reason(message: str) -> str | None:
    compact = _compact(message)
    if _has_passive_death_statement(message):
        return "passive_death_statement"
    if _near_clear_signal(compact):
        return "near_clear_phrase"
    if _unresolved_boss_reference(compact):
        return "unresolved_boss_reference"
    low_confidence_reason = _low_confidence_game_semantic_reason(compact)
    if low_confidence_reason:
        return low_confidence_reason
    return None


def _low_confidence_game_semantic_reason(compact: str) -> str | None:
    """Detect game-like semantic hints without turning them into final state.

    These markers only make the trace / Shadow Mode path observable. Boss identity,
    death counts, and progress updates still require rule evidence. LLM Shadow
    Mode can only produce non-mutating candidates for observation.
    """

    if not compact:
        return None
    has_slang_failure = any(
        marker in compact
        for marker in (
            "寄了",
            "寄咯",
            "打爆",
            "打烂",
            "打爛",
            "锤爆",
            "錘爆",
            "薄纱",
            "薄紗",
            "被薄纱",
            "被薄紗",
            "爆杀",
            "爆殺",
        )
    )
    has_game_hint = any(
        marker in compact
        for marker in (
            "空洞骑士",
            "空洞騎士",
            "hollowknight",
            "hollow knight",
            "艾尔登法环",
            "艾爾登法環",
            "eldenring",
            "elden ring",
            "boss",
            "二阶段",
            "二階段",
            "一阶段",
            "一階段",
        )
    )
    has_alias_shape = any(
        marker in compact
        for marker in (
            "那个",
            "那個",
            "大哥",
            "家伙",
            "傢伙",
            "骑马",
            "騎馬",
        )
    )
    has_combat_hint = any(
        marker in compact
        for marker in (
            "打",
            "砍",
            "锤",
            "錘",
            "杀",
            "殺",
            "死",
            "回",
            "次",
            "烦",
            "煩",
            "过",
            "過",
            "卡",
        )
    )
    if has_alias_shape and (has_slang_failure or has_game_hint or has_combat_hint):
        return "unknown_boss_alias"
    if has_slang_failure:
        return "slang_failure_expression"
    if has_game_hint and has_combat_hint:
        return "game_semantic_keywords_no_rule_update"
    return None


def _unresolved_boss_reference(compact: str) -> bool:
    return bool(
        re.search(
            r"(?:之前|前面|刚才|剛才|刚刚|剛剛).{0,8}(?:没打过|沒打過|没过|沒過|过不了|過不了|卡住|卡了).{0,8}(?:boss|那个|那個|那只|那隻)",
            compact,
        )
        or re.search(r"重新(?:挑战|挑戰|打).{0,8}(?:之前|前面).{0,8}(?:没打过|沒打過|没过|沒過|卡住)", compact)
    )


def _mentions_short_guide_preference(compact: str) -> bool:
    return bool(re.search(r"(?:喜欢|喜歡|希望|想要|尽量|盡量).{0,8}(?:简短|短一点|短點|一句|少一点|少點).{0,8}(?:攻略|提醒|回答)", compact))


def _mentions_long_guide_preference(compact: str) -> bool:
    patterns = (
        r"不(?:想|要|喜欢|喜歡).{0,8}(?:长篇|長篇|详细|攻略)",
        r"(?:别|別|不要).{0,8}(?:长篇|長篇|攻略站|详细攻略)",
        r"(?:少|少一点|少點).{0,8}(?:攻略|长篇|長篇)",
        r"不喜欢攻略站",
        r"不喜歡攻略站",
    )
    return any(re.search(pattern, compact) for pattern in patterns)


def _mentions_guide_site_preference(compact: str) -> bool:
    return bool(re.search(r"(?:别|別|不要|不喜欢|不喜歡).{0,8}攻略站", compact))


def _mentions_spirit_ashes_preference(compact: str) -> bool:
    patterns = (
        r"不(?:想|要|喜欢|喜歡|用|召).{0,8}(?:召唤|召喚|骨灰)",
        r"(?:不用|不召|别召|別召|不要召).{0,4}骨灰",
        r"不想叫骨灰",
    )
    return any(re.search(pattern, compact) for pattern in patterns)


def _mentions_persona_preference(compact: str) -> bool:
    if not any(marker in compact for marker in ("喜欢", "喜歡", "希望", "想要")):
        return False
    return any(
        topic in compact
        for topic in (
            "你经常笑",
            "你經常笑",
            "你笑",
            "说话更柔和",
            "說話更柔和",
            "更柔和",
            "温柔一点",
            "溫柔一點",
            "多回应",
            "多回應",
            "多理我",
            "多说一点",
            "多說一點",
        )
    )


def _explicit_personal_preference(compact: str) -> str | None:
    if _negative_memory_request(compact):
        return None
    if not re.search(r"(?:记住|記住|记得|記得|帮我记|幫我記)", compact):
        return None
    match = re.search(r"我(喜欢|喜歡|不喜欢|不喜歡)([^，。,.!?！？]{1,24})", compact)
    if not match:
        return None
    verb = "喜欢" if match.group(1) in {"喜欢", "喜歡"} else "不喜欢"
    value = normalize_terminology(match.group(2)).strip()
    if not value:
        return None
    return f"{verb}{value}"


def _mentions_exploration_before_boss_preference(compact: str) -> bool:
    if not re.search(r"(?:记住|記住|记得|記得|帮我记|幫我記)", compact):
        return False
    if _negative_memory_request(compact):
        return False
    has_boss_context = "boss" in compact or "打boss" in compact or "打Boss".lower() in compact
    has_exploration = any(marker in compact for marker in ("先探索", "探索地图", "探索地圖", "先跑图", "先跑圖"))
    has_hard_push_dislike = any(marker in compact for marker in ("不喜欢直接硬打", "不喜歡直接硬打", "不想直接硬打", "不要直接硬打"))
    return has_boss_context and (has_exploration or has_hard_push_dislike)


def _negative_memory_request(compact: str) -> bool:
    return any(
        marker in compact
        for marker in (
            "不用记住",
            "不用記住",
            "不要记住",
            "不要記住",
            "别记住",
            "別記住",
            "别记",
            "別記",
            "不用记",
            "不用記",
            "不需要记住",
            "不需要記住",
        )
    )


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", normalize_terminology(text).lower())


def _clamp(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 3)
    except (TypeError, ValueError):
        return 0.0
