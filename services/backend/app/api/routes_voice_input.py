from fastapi import APIRouter

from app.modules.voice_input.local_asr_config import get_local_asr_status
from app.schemas.api import LocalAsrStatusResponse

router = APIRouter(tags=["voice-input"])


@router.get("/voice-input/local-asr/status", response_model=LocalAsrStatusResponse)
def local_asr_status() -> LocalAsrStatusResponse:
    return get_local_asr_status()
