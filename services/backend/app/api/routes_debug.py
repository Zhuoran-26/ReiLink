from fastapi import APIRouter

from app.modules.dialogue_agent.providers import get_provider_info
from app.modules.dialogue_agent.metrics import get_last_chat_metrics
from app.modules.memory.profile import PlayerMemory
from app.modules.memory.store import ConversationStore
from app.schemas.api import ChatDebugResponse, MemoryDebugResponse

router = APIRouter(tags=["debug"])


@router.get("/debug/provider")
def debug_provider() -> dict[str, str | bool | None]:
    return get_provider_info().as_dict()


@router.get("/debug/memory", response_model=MemoryDebugResponse)
def debug_memory(session_id: str = "default") -> dict:
    memory = PlayerMemory()
    active_state = memory.active_memory_state()
    memory_items = memory.build_prompt_context_with_provenance().as_debug_items()
    session_items = ConversationStore().recent_context(session_id)
    return {
        "prompt_order": ["current_user_message", "current_session", "memory", "persona"],
        "memory_written": active_state["memory_written"],
        "current_boss": active_state["current_boss"],
        "emotional_note": active_state["emotional_note"],
        "recent_episode_count": active_state["recent_episode_count"],
        "items": session_items + memory_items,
    }


@router.get("/debug/chat", response_model=ChatDebugResponse)
def debug_chat() -> dict:
    return get_last_chat_metrics().as_dict()
