from fastapi import APIRouter, HTTPException

from app.modules.memory.pending import PendingMemoryQueue
from app.modules.memory.profile import PlayerMemory
from app.modules.memory.store import ConversationStore
from app.modules.proactive.trigger import ProactiveCompanion
from app.schemas.api import (
    EpisodeMemory,
    LongTermMemoryItem,
    MemoryEntry,
    MemoryResetResponse,
    PendingMemoryClearResponse,
    PendingMemoryItem,
    UserProfileMemory,
)

router = APIRouter(tags=["memory"])


@router.get("/memory/sessions", response_model=list[str])
def sessions() -> list[str]:
    return ConversationStore().list_sessions()


@router.get("/memory/session/{session_id}", response_model=list[MemoryEntry])
def session(session_id: str) -> list[MemoryEntry]:
    return ConversationStore().read_session(session_id)


@router.get("/memory/profile", response_model=UserProfileMemory)
def profile() -> dict:
    return PlayerMemory().load_profile().as_dict()


@router.get("/memory/episodes", response_model=list[EpisodeMemory])
def episodes() -> list[dict]:
    return PlayerMemory().recent_episodes(limit=50)


@router.post("/memory/reset", response_model=MemoryResetResponse)
def reset() -> dict[str, str]:
    PlayerMemory().reset()
    PendingMemoryQueue().clear_all()
    ProactiveCompanion().suppress_after_system_action("reset_memory")
    return {"status": "reset"}


@router.get("/memory/pending", response_model=list[PendingMemoryItem])
def pending_memories() -> list[dict]:
    return [_public_pending_item(item) for item in PendingMemoryQueue().list()]


@router.post("/memory/long-term/{memory_id}/undo", response_model=LongTermMemoryItem)
def undo_long_term_memory(memory_id: str) -> dict:
    try:
        return PlayerMemory().deactivate_long_term_memory(memory_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="long-term memory not found") from exc


@router.post("/memory/pending/{memory_id}/accept", response_model=PendingMemoryItem)
def accept_pending_memory(memory_id: str) -> dict:
    try:
        return _public_pending_item(PendingMemoryQueue().accept(memory_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="pending memory not found") from exc


@router.post("/memory/pending/{memory_id}/ignore", response_model=PendingMemoryItem)
def ignore_pending_memory(memory_id: str) -> dict:
    try:
        return _public_pending_item(PendingMemoryQueue().ignore(memory_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="pending memory not found") from exc


@router.post("/memory/pending/clear", response_model=PendingMemoryClearResponse)
def clear_pending_memories() -> dict[str, str]:
    PendingMemoryQueue().clear()
    ProactiveCompanion().suppress_after_system_action("clear_pending_memories")
    return {"status": "cleared"}


def _public_pending_item(item: dict) -> dict:
    return {key: value for key, value in item.items() if key != "payload"}
