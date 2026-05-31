from fastapi import APIRouter

from app.modules.app_settings.store import AppSettingsStore
from app.modules.game_detector.detector import (
    LocalGameDetector,
    detection_to_game_status,
    idle_game_status,
    sync_game_session_from_detection,
)
from app.schemas.api import GameDetectionResponse, GameStatus

router = APIRouter(tags=["game"])


@router.get("/game/status", response_model=GameStatus)
def game_status() -> GameStatus:
    app_settings = AppSettingsStore().load()
    if app_settings.auto_game_detection == "off":
        return idle_game_status()
    detection = LocalGameDetector().detect()
    sync_game_session_from_detection(detection, auto_game_detection=app_settings.auto_game_detection)
    return detection_to_game_status(detection)


@router.get("/game/detected", response_model=GameDetectionResponse)
def game_detected() -> GameDetectionResponse:
    detection = LocalGameDetector().detect()
    app_settings = AppSettingsStore().load()
    sync_game_session_from_detection(detection, auto_game_detection=app_settings.auto_game_detection)
    return detection
