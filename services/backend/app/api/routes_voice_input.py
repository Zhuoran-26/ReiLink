from fastapi import APIRouter

from app.modules.voice_input.local_asr_config import get_local_asr_status
from app.modules.voice_input.local_asr_probe import probe_local_asr_binary
from app.schemas.api import LocalAsrProbeResponse, LocalAsrStatusResponse

router = APIRouter(tags=["voice-input"])


@router.get("/voice-input/local-asr/status", response_model=LocalAsrStatusResponse)
def local_asr_status() -> LocalAsrStatusResponse:
    return get_local_asr_status()


@router.post("/voice-input/local-asr/probe", response_model=LocalAsrProbeResponse)
def local_asr_probe() -> LocalAsrProbeResponse:
    return probe_local_asr_binary()
