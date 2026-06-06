import os
import tempfile
from pathlib import Path

from app.schemas.api import AudioProbeResponse


MAX_AUDIO_UPLOAD_BYTES = 2 * 1024 * 1024
ALLOWED_AUDIO_MIME_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp4",
    "audio/aac",
    "audio/flac",
    "application/octet-stream",
    "video/webm",
}


def process_audio_probe(
    audio_bytes: bytes,
    mime_type: str | None,
    duration_ms: int = 0,
    temp_root: str | None = None,
) -> AudioProbeResponse:
    safe_mime_type = _safe_mime_type(mime_type)
    size_bytes = len(audio_bytes)
    if size_bytes > MAX_AUDIO_UPLOAD_BYTES:
        return AudioProbeResponse(
            status="audio_probe_file_too_large",
            available=False,
            display_message="录音文件过大",
            duration_ms=max(0, duration_ms),
            size_bytes=size_bytes,
            mime_type=safe_mime_type,
            temporary_file_cleaned=True,
        )
    if size_bytes <= 0 or not _is_allowed_audio_type(safe_mime_type):
        return AudioProbeResponse(
            status="audio_probe_invalid_audio",
            available=False,
            display_message="录音数据无效",
            duration_ms=max(0, duration_ms),
            size_bytes=size_bytes,
            mime_type=safe_mime_type,
            temporary_file_cleaned=True,
        )

    temp_dir: Path | None = None
    temp_path: Path | None = None
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix="reilink-audio-probe-", dir=temp_root))
        temp_path = temp_dir / f"probe{_extension_for_mime(safe_mime_type)}"
        temp_path.write_bytes(audio_bytes)
        if not temp_path.is_file() or temp_path.stat().st_size != size_bytes:
            _cleanup_temp_path(temp_path, temp_dir)
            return AudioProbeResponse(
                status="audio_probe_recording_failed",
                available=False,
                display_message="录音临时文件写入失败",
                duration_ms=max(0, duration_ms),
                size_bytes=size_bytes,
                mime_type=safe_mime_type,
                temporary_file_cleaned=not temp_path.exists(),
            )
        try:
            _delete_temp_file(temp_path)
            _delete_temp_dir(temp_dir)
        except Exception:
            _cleanup_temp_path(temp_path, temp_dir)
            return AudioProbeResponse(
                status="audio_probe_cleanup_failed",
                available=False,
                display_message="临时音频清理失败",
                duration_ms=max(0, duration_ms),
                size_bytes=size_bytes,
                mime_type=safe_mime_type,
                temporary_file_cleaned=not temp_path.exists(),
            )
        return AudioProbeResponse(
            status="audio_probe_succeeded",
            available=True,
            display_message="录音测试完成，临时音频已清理",
            duration_ms=max(0, duration_ms),
            size_bytes=size_bytes,
            mime_type=safe_mime_type,
            temporary_file_cleaned=True,
        )
    except Exception:
        if temp_path or temp_dir:
            _cleanup_temp_path(temp_path, temp_dir)
        return AudioProbeResponse(
            status="audio_probe_error",
            available=False,
            display_message="录音测试失败",
            duration_ms=max(0, duration_ms),
            size_bytes=size_bytes,
            mime_type=safe_mime_type,
            temporary_file_cleaned=bool(temp_path is None or not temp_path.exists()),
        )


def _safe_mime_type(mime_type: str | None) -> str | None:
    if not mime_type:
        return None
    return mime_type.split(";", 1)[0].strip().lower() or None


def _is_allowed_audio_type(mime_type: str | None) -> bool:
    if not mime_type:
        return False
    return mime_type.startswith("audio/") or mime_type in ALLOWED_AUDIO_MIME_TYPES


def _extension_for_mime(mime_type: str | None) -> str:
    labels = {
        "audio/webm": ".webm",
        "video/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/wave": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/aac": ".aac",
        "audio/flac": ".flac",
    }
    return labels.get(mime_type or "", ".audio")


def _delete_temp_file(path: Path) -> None:
    path.unlink()


def _delete_temp_dir(path: Path) -> None:
    path.rmdir()


def _cleanup_temp_path(temp_path: Path | None, temp_dir: Path | None) -> None:
    if temp_path is not None:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        except Exception:
            pass
    if temp_dir is not None:
        try:
            os.rmdir(temp_dir)
        except FileNotFoundError:
            pass
        except Exception:
            pass
