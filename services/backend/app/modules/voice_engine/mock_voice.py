from typing import Any

from app.core.config import settings
from app.schemas.api import VoiceSpeakResponse, VoiceTranscribeResponse


class MockVoiceEngine:
    def transcribe(self, file: Any | None = None) -> VoiceTranscribeResponse:
        return VoiceTranscribeResponse(text="[mock transcription]", provider=settings.stt_provider)

    def speak(self, text: str) -> VoiceSpeakResponse:
        return VoiceSpeakResponse(audio_url=None, provider=settings.tts_provider, message="Mock TTS completed.")

