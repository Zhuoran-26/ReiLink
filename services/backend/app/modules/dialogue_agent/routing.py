from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
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


def select_model_route(intent: str, user_message: str) -> ModelRoute:
    emotion = detect_user_emotion(user_message)
    detailed = wants_detailed_strategy(user_message)
    if detailed:
        return _reasoning_route("detailed_guide")
    if emotion.detected:
        return _fast_route(emotion.label or "emotion")
    if intent in FAST_INTENTS:
        return _fast_route(intent)
    if intent in REASONING_INTENTS:
        return _reasoning_route(intent)
    return _fast_route("short_reply")


def _fast_route(route: str) -> ModelRoute:
    model = settings.deepseek_model_fast or "deepseek-chat"
    return ModelRoute(selected_model=model, thinking_enabled=False, reasoning_effort=None, route=route)


def _reasoning_route(route: str) -> ModelRoute:
    return ModelRoute(
        selected_model=settings.deepseek_model_reasoning,
        thinking_enabled=True,
        reasoning_effort=settings.deepseek_reasoning_effort or "medium",
        route=route,
    )
