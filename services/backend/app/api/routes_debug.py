from fastapi import APIRouter

from app.modules.dialogue_agent.metrics import get_last_chat_metrics
from app.modules.dialogue_agent.prompt_preview import build_prompt_preview
from app.modules.dialogue_agent.providers import get_provider_info
from app.modules.dialogue_agent.semantic_extraction import (
    get_latest_semantic_extraction_debug,
    get_semantic_shadow_events,
)
from app.modules.game_session.state import GameSessionStore
from app.modules.memory.profile import PlayerMemory
from app.modules.memory.store import ConversationStore
from app.modules.proactive.trigger import ProactiveCompanion
from app.schemas.api import ChatDebugResponse, MemoryDebugResponse, PromptPreviewResponse

router = APIRouter(tags=["debug"])


@router.get("/debug/provider")
def debug_provider() -> dict:
    data = get_provider_info().as_dict()
    metrics = get_last_chat_metrics().as_dict()
    data.update(
        {
            "selected_model": metrics.get("selected_model"),
            "main_reply_model": metrics.get("main_reply_model") or metrics.get("selected_model"),
            "route_reason": metrics.get("route_reason"),
            "route_intent": metrics.get("route_intent") or metrics.get("intent"),
            "estimated_complexity": metrics.get("estimated_complexity"),
            "provider_latency_ms": metrics.get("provider_latency_ms", 0),
            "semantic_extraction_model": metrics.get("semantic_extraction_model"),
            "fallback_reason": metrics.get("fallback_reason"),
        }
    )
    return data


@router.get("/debug/memory", response_model=MemoryDebugResponse)
def debug_memory(session_id: str = "default") -> dict:
    memory = PlayerMemory()
    active_state = memory.active_memory_state()
    memory_items = memory.build_prompt_context_with_provenance().as_debug_items()
    session_items = ConversationStore().recent_context(session_id)
    return {
        "prompt_order": ["persona", "memory", "current_session", "game_state", "current_user_message"],
        "memory_written": active_state["memory_written"],
        "current_boss": active_state["current_boss"],
        "emotional_note": active_state["emotional_note"],
        "recent_episode_count": active_state["recent_episode_count"],
        "items": session_items + memory_items,
    }


@router.get("/debug/chat", response_model=ChatDebugResponse)
def debug_chat() -> dict:
    return get_last_chat_metrics().as_dict()


@router.get("/debug/prompt-preview", response_model=PromptPreviewResponse)
def debug_prompt_preview(session_id: str = "default") -> dict:
    return build_prompt_preview(session_id=session_id)


@router.get("/debug/game-session")
def debug_game_session() -> dict:
    return GameSessionStore().debug_state()


@router.post("/debug/game-session/reset")
def reset_game_session() -> dict:
    GameSessionStore().reset()
    ProactiveCompanion().suppress_after_system_action("reset_game_session")
    return {"status": "reset"}


@router.get("/debug/semantic-extraction/latest")
def debug_semantic_extraction_latest() -> dict:
    return get_latest_semantic_extraction_debug()


@router.get("/debug/semantic-shadow/events")
def debug_semantic_shadow_events(since_id: int = 0, limit: int = 50) -> dict:
    return get_semantic_shadow_events(since_id=since_id, limit=limit)
