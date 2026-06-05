from fastapi import APIRouter, File, Form, Request, UploadFile

from app.modules.voice_input.audio_probe import MAX_AUDIO_UPLOAD_BYTES, process_audio_probe
from app.modules.voice_input.local_asr_config import get_local_asr_status
from app.modules.voice_input.local_asr_probe import probe_local_asr_binary
from app.modules.voice_input.local_asr_transcribe import transcribe_local_asr_audio
from app.schemas.api import (
    AudioProbeResponse,
    LocalAsrProbeResponse,
    LocalAsrStatusResponse,
    LocalAsrTranscriptionResponse,
)

router = APIRouter(tags=["voice-input"])


@router.get("/voice-input/local-asr/status", response_model=LocalAsrStatusResponse)
def local_asr_status() -> LocalAsrStatusResponse:
    return get_local_asr_status()


@router.post("/voice-input/local-asr/probe", response_model=LocalAsrProbeResponse)
def local_asr_probe() -> LocalAsrProbeResponse:
    return probe_local_asr_binary()


@router.post("/voice-input/local-asr/transcribe", response_model=LocalAsrTranscriptionResponse)
async def local_asr_transcribe(
    audio: UploadFile | None = File(default=None),
    language: str | None = Form(default=None),
    duration_ms: int = Form(default=0),
    mime_type: str | None = Form(default=None),
) -> LocalAsrTranscriptionResponse:
    if audio is None:
        return transcribe_local_asr_audio(b"", mime_type, duration_ms=duration_ms, language=language)
    try:
        body = await audio.read()
    except Exception:
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_error",
            available=False,
            display_message="录音上传失败",
            duration_ms=max(0, duration_ms),
            mime_type=_safe_header(mime_type or audio.content_type),
            temporary_file_cleaned=True,
        )
    return transcribe_local_asr_audio(
        body,
        mime_type or audio.content_type,
        duration_ms=duration_ms,
        language=language,
    )


@router.post("/voice-input/audio/probe", response_model=AudioProbeResponse)
async def audio_probe(request: Request) -> AudioProbeResponse:
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_AUDIO_UPLOAD_BYTES:
        return AudioProbeResponse(
            status="audio_probe_file_too_large",
            available=False,
            display_message="录音文件过大",
            size_bytes=int(content_length),
            mime_type=_safe_header(request.headers.get("content-type")),
            temporary_file_cleaned=True,
        )
    duration_ms = _duration_header(request.headers.get("x-reilink-audio-duration-ms"))
    try:
        body = await request.body()
    except Exception:
        return AudioProbeResponse(
            status="audio_probe_upload_failed",
            available=False,
            display_message="录音上传失败",
            duration_ms=duration_ms,
            mime_type=_safe_header(request.headers.get("content-type")),
            temporary_file_cleaned=True,
        )
    return process_audio_probe(body, request.headers.get("content-type"), duration_ms=duration_ms)


def _safe_header(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(";", 1)[0].strip().lower() or None


def _duration_header(value: str | None) -> int:
    if not value:
        return 0
    try:
        return max(0, int(float(value)))
    except ValueError:
        return 0
