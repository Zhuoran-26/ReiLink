from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.config import active_model_preference, settings
from app.modules.dialogue_agent.emotion import detect_user_emotion, wants_detailed_strategy

FAST_INTENTS = {"casual_chat", "identity_question", "unclear"}
REASONING_INTENTS = {
    "elden_ring_boss_strategy",
    "elden_ring_build",
    "elden_ring_location",
    "elden_ring_general_help",
}


@dataclass(frozen=True)
class ModelRoute:
    selected_model: str
    thinking_enabled: bool
    reasoning_effort: str | None
    route: str
    model_route_mode: str
    route_reason: str
    route_intent: str
    estimated_complexity: str


def select_model_route(intent: str, user_message: str, model_preference: str | None = None) -> ModelRoute:
    preference = _normalize_preference(model_preference or active_model_preference())
    if preference == "fast":
        return _fast_route("preference_fast", intent, "low", preference)
    if preference == "pro":
        return _pro_route("preference_pro", intent, "high", preference)

    return _auto_route(intent, user_message)


def _auto_route(intent: str, user_message: str) -> ModelRoute:
    emotion = detect_user_emotion(user_message)
    detailed = wants_detailed_strategy(user_message)
    if detailed or _has_explicit_detail_marker(_compact(user_message)):
        return _pro_route("explicit_detail_request", intent, "high", "auto")
    if _needs_long_context_reasoning(user_message):
        return _pro_route("long_context_reasoning", intent, "high", "auto")
    if _is_multi_step_or_complex(user_message, intent):
        return _pro_route("multi_step_or_complex_request", intent, "high", "auto")
    if emotion.detected:
        return _fast_route(f"emotional_support:{emotion.label or 'emotion'}", intent, "low", "auto")
    if intent in FAST_INTENTS:
        return _fast_route("casual_or_short_reply", intent, "low", "auto")
    if intent in REASONING_INTENTS:
        return _fast_route("simple_game_reminder", intent, "medium", "auto")
    return _fast_route("short_reply", intent, "low", "auto")


def _fast_route(route: str, intent: str, complexity: str, mode: str) -> ModelRoute:
    model = settings.deepseek_model_fast or "deepseek-chat"
    return ModelRoute(
        selected_model=model,
        thinking_enabled=False,
        reasoning_effort=None,
        route=route,
        model_route_mode=mode,
        route_reason=route,
        route_intent=intent,
        estimated_complexity=complexity,
    )


def _pro_route(route: str, intent: str, complexity: str, mode: str) -> ModelRoute:
    return ModelRoute(
        selected_model=settings.deepseek_model_pro,
        thinking_enabled=True,
        reasoning_effort=settings.deepseek_reasoning_effort or "medium",
        route=route,
        model_route_mode=mode,
        route_reason=route,
        route_intent=intent,
        estimated_complexity=complexity,
    )


def _normalize_preference(value: str) -> str:
    preference = value.lower().strip()
    if preference in {"fast", "pro"}:
        return preference
    return "auto"


def _needs_long_context_reasoning(message: str) -> bool:
    compact = _compact(message)
    return len(compact) >= 180


def _is_multi_step_or_complex(message: str, intent: str) -> bool:
    compact = _compact(message)
    if _has_explicit_detail_marker(compact):
        return True
    if _has_multi_step_marker(compact):
        return True
    if _has_complex_analysis_marker(compact):
        return True
    if intent == "elden_ring_build" and _has_build_analysis_marker(compact):
        return True
    if intent == "elden_ring_location" and _has_route_planning_marker(compact):
        return True
    return False


def _has_explicit_detail_marker(compact: str) -> bool:
    return any(
        marker in compact
        for marker in (
            "详细讲",
            "詳細講",
            "详细说",
            "詳細說",
            "完整说",
            "完整說",
            "一步步告诉我",
            "一步步告訴我",
            "具体流程",
            "具體流程",
            "完整流程",
            "详细攻略",
            "詳細攻略",
            "完整攻略",
            "完整打法",
        )
    )


def _has_multi_step_marker(compact: str) -> bool:
    if any(marker in compact for marker in ("分步骤", "分步驟", "一步步", "先说", "先說", "然后", "然後", "再讲", "再講")):
        return True
    if compact.count("？") + compact.count("?") >= 2:
        return True
    return bool(re.search(r"先.{1,18}再", compact))


def _has_complex_analysis_marker(compact: str) -> bool:
    return any(
        marker in compact
        for marker in (
            "复杂解释",
            "複雜解釋",
            "解释一下",
            "解釋一下",
            "为什么",
            "為什麼",
            "机制",
            "機制",
            "分析",
            "优缺点",
            "優缺點",
            "对比",
            "比較",
            "比较",
            "路线规划",
            "路線規劃",
        )
    )


def _has_build_analysis_marker(compact: str) -> bool:
    return any(marker in compact for marker in ("配装分析", "配裝分析", "怎么配装", "怎麼配裝", "加点", "加點", "流派"))


def _has_route_planning_marker(compact: str) -> bool:
    return any(marker in compact for marker in ("路线", "路線", "规划", "規劃", "流程", "怎么走", "怎麼走", "先去哪"))


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())
