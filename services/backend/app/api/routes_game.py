from fastapi import APIRouter, HTTPException

from app.modules.app_settings.store import AppSettingsStore
from app.modules.game_context.context import (
    GameContextResolver,
    UnknownGameOverrideError,
    game_status_from_context,
)
from app.modules.game_detector.detector import (
    LocalGameDetector,
    detection_to_game_status,
    idle_game_status,
    sync_game_session_from_detection,
)
from app.schemas.api import GameContextResponse, GameDetectionResponse, GameStatus, ManualGameContextRequest

router = APIRouter(tags=["game"])


@router.get("/game/status", response_model=GameStatus)
def game_status() -> GameStatus:
    app_settings = AppSettingsStore().load()
    context = GameContextResolver().resolve(sync_session=True)
    if context.manual_override.enabled:
        return game_status_from_context(context)
    if app_settings.auto_game_detection == "off":
        return idle_game_status()
    detection = LocalGameDetector().detect()
    sync_game_session_from_detection(detection, auto_game_detection=app_settings.auto_game_detection)
    return detection_to_game_status(detection)


@router.get("/game/detected", response_model=GameDetectionResponse)
def game_detected() -> GameDetectionResponse:
    detection = LocalGameDetector().detect()
    app_settings = AppSettingsStore().load()
    context = GameContextResolver().resolve(detected_game=detection)
    if not context.manual_override.enabled:
        sync_game_session_from_detection(detection, auto_game_detection=app_settings.auto_game_detection)
    return detection


@router.get("/game/context", response_model=GameContextResponse)
def game_context() -> GameContextResponse:
    return GameContextResolver().resolve(sync_session=True)


@router.post("/game/context/manual", response_model=GameContextResponse)
def set_manual_game_context(request: ManualGameContextRequest) -> GameContextResponse:
    resolver = GameContextResolver()
    try:
        resolver.set_manual_override(request.game_id)
    except UnknownGameOverrideError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return resolver.resolve(sync_session=True)
