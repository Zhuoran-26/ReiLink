from fastapi import APIRouter

from app.modules.memory.profile import PlayerMemory
from app.modules.memory.store import ConversationStore
from app.schemas.api import EpisodeMemory, MemoryEntry, MemoryResetResponse, UserProfileMemory

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
    return {"status": "reset"}
