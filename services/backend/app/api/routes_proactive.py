from fastapi import APIRouter

from app.modules.proactive.trigger import ProactiveCompanion
from app.schemas.api import (
    ProactiveCheckRequest,
    ProactiveCheckResponse,
    ProactiveResetResponse,
    ProactiveSettingsRequest,
    ProactiveStatusResponse,
)

router = APIRouter(tags=["proactive"])


@router.get("/proactive/status", response_model=ProactiveStatusResponse)
def proactive_status(session_id: str = "default") -> dict:
    return ProactiveCompanion().status(session_id=session_id)


@router.post("/proactive/check", response_model=ProactiveCheckResponse)
def proactive_check(payload: ProactiveCheckRequest) -> dict:
    return ProactiveCompanion().check(
        session_id=payload.session_id,
        connected=payload.connected,
        is_user_typing=payload.is_user_typing,
    )


@router.post("/proactive/settings", response_model=ProactiveStatusResponse)
def proactive_settings(payload: ProactiveSettingsRequest) -> dict:
    return ProactiveCompanion().update_settings(enabled=payload.enabled, sensitivity=payload.sensitivity)


@router.post("/proactive/reset", response_model=ProactiveResetResponse)
def proactive_reset() -> dict:
    return ProactiveCompanion().reset_runtime_state()
