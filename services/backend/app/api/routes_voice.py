from fastapi import APIRouter, UploadFile

from app.modules.voice_engine.mock_voice import MockVoiceEngine
from app.schemas.api import VoiceSpeakRequest, VoiceSpeakResponse, VoiceTranscribeResponse

router = APIRouter(tags=["voice"])


@router.post("/voice/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe(file: UploadFile | None = None) -> VoiceTranscribeResponse:
    return MockVoiceEngine().transcribe(file)


@router.post("/voice/speak", response_model=VoiceSpeakResponse)
def speak(request: VoiceSpeakRequest) -> VoiceSpeakResponse:
    return MockVoiceEngine().speak(request.text)

