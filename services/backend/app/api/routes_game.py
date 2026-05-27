from fastapi import APIRouter

from app.modules.game_detector.detector import EldenRingDetector
from app.schemas.api import GameStatus

router = APIRouter(tags=["game"])


@router.get("/game/status", response_model=GameStatus)
def game_status() -> GameStatus:
    return EldenRingDetector().get_status()

