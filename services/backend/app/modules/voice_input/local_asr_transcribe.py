import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.modules.voice_input.audio_probe import (
    MAX_AUDIO_UPLOAD_BYTES,
    _extension_for_mime,
    _is_allowed_audio_type,
    _safe_mime_type,
)
from app.modules.voice_input.local_asr_config import BINARY_ENV, MODEL_ENV, _configured_path, get_local_asr_status
from app.schemas.api import LocalAsrTranscriptionResponse


TRANSCRIPTION_TIMEOUT_SECONDS = 30
MAX_TRANSCRIPT_CHARS = 500

_TIMESTAMP_PREFIX_RE = re.compile(
    r"^\s*(?:\[[^\]]*?-->\s*[^\]]*?\]|\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?\s*-->\s*\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\s*"
)
_WHITESPACE_RE = re.compile(r"\s+")
_SAFE_LANGUAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,15}$")
_LOG_PREFIXES = (
    "whisper_",
    "ggml_",
    "main:",
    "system_info:",
    "load_model:",
    "whisper_init",
    "whisper_full",
    "sampling:",
    "processing",
    "encode time",
    "decode time",
    "total time",
    "mel time",
    "fallbacks:",
    "grammar:",
    "n_threads",
    "detected language:",
)
_SENSITIVE_TERMS = (
    ".env",
    "authorization",
    "api_key",
    "bearer ",
    "traceback",
    "exception",
)


def transcribe_local_asr_audio(
    audio_bytes: bytes,
    mime_type: str | None,
    duration_ms: int = 0,
    language: str | None = None,
    timeout_seconds: int | float = TRANSCRIPTION_TIMEOUT_SECONDS,
    temp_root: str | None = None,
) -> LocalAsrTranscriptionResponse:
    config = get_local_asr_status()
    safe_mime_type = _safe_mime_type(mime_type)
    size_bytes = len(audio_bytes)
    safe_duration_ms = max(0, duration_ms)
    base_response = {
        "duration_ms": safe_duration_ms,
        "size_bytes": size_bytes,
        "mime_type": safe_mime_type,
        "binary_name": config.safe_binary_name,
        "model_name": config.safe_model_name,
    }

    if config.status != "local_asr_ready":
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_not_ready",
            available=False,
            display_message="本地语音识别配置未就绪",
            temporary_file_cleaned=True,
            **base_response,
        )
    if size_bytes > MAX_AUDIO_UPLOAD_BYTES:
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_failed",
            available=False,
            display_message="录音文件过大",
            temporary_file_cleaned=True,
            **base_response,
        )
    if size_bytes <= 0 or not _is_allowed_audio_type(safe_mime_type):
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_failed",
            available=False,
            display_message="录音数据无效",
            temporary_file_cleaned=True,
            **base_response,
        )

    binary_path = _configured_path(BINARY_ENV)
    model_path = _configured_path(MODEL_ENV)
    if binary_path is None or model_path is None:
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_not_ready",
            available=False,
            display_message="本地语音识别配置未就绪",
            temporary_file_cleaned=True,
            **base_response,
        )

    temp_dir: Path | None = None
    temp_path: Path | None = None
    response: LocalAsrTranscriptionResponse
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix="reilink-local-asr-", dir=temp_root))
        temp_path = temp_dir / f"recording{_extension_for_mime(safe_mime_type)}"
        temp_path.write_bytes(audio_bytes)
        if not temp_path.is_file() or temp_path.stat().st_size != size_bytes:
            response = LocalAsrTranscriptionResponse(
                status="local_asr_transcription_failed",
                available=False,
                display_message="录音临时文件写入失败",
                temporary_file_cleaned=False,
                **base_response,
            )
        else:
            response = _run_transcription(
                binary_path=binary_path,
                model_path=model_path,
                audio_path=temp_path,
                temp_dir=temp_dir,
                language=language,
                timeout_seconds=timeout_seconds,
                base_response=base_response,
            )
    except Exception:
        response = LocalAsrTranscriptionResponse(
            status="local_asr_transcription_error",
            available=False,
            display_message="本地语音识别失败",
            temporary_file_cleaned=bool(temp_path is None or not temp_path.exists()),
            **base_response,
        )

    cleanup_succeeded = _cleanup_temp_dir(temp_dir)
    if not cleanup_succeeded:
        _best_effort_cleanup(temp_dir)
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_cleanup_failed",
            available=False,
            display_message="临时音频清理失败",
            temporary_file_cleaned=bool(temp_dir is None or not temp_dir.exists()),
            **base_response,
        )

    return response.model_copy(update={"temporary_file_cleaned": True})


def _run_transcription(
    binary_path: Path,
    model_path: Path,
    audio_path: Path,
    temp_dir: Path,
    language: str | None,
    timeout_seconds: int | float,
    base_response: dict[str, object],
) -> LocalAsrTranscriptionResponse:
    command = _build_command(binary_path, model_path, audio_path, language)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_timed_out",
            available=False,
            display_message="本地语音识别超时",
            temporary_file_cleaned=False,
            **base_response,
        )
    except OSError:
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_error",
            available=False,
            display_message="本地语音识别程序无法启动",
            temporary_file_cleaned=False,
            **base_response,
        )
    except Exception:
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_error",
            available=False,
            display_message="本地语音识别失败",
            temporary_file_cleaned=False,
            **base_response,
        )

    transcript = _extract_transcript(
        stdout=result.stdout,
        output_dir=temp_dir,
        sensitive_paths=(binary_path, model_path, audio_path, temp_dir),
    )
    if result.returncode != 0:
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_failed",
            available=False,
            display_message="本地语音识别失败",
            temporary_file_cleaned=False,
            **base_response,
        )
    if not transcript:
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_no_text",
            available=False,
            display_message="没有识别到文本",
            temporary_file_cleaned=False,
            **base_response,
        )
    return LocalAsrTranscriptionResponse(
        status="local_asr_transcription_succeeded",
        available=True,
        display_message="本地语音识别完成",
        transcript=transcript,
        transcript_char_count=len(transcript),
        duration_ms=int(base_response["duration_ms"]),
        size_bytes=int(base_response["size_bytes"]),
        mime_type=base_response["mime_type"] if isinstance(base_response["mime_type"], str) else None,
        temporary_file_cleaned=False,
        binary_name=base_response["binary_name"] if isinstance(base_response["binary_name"], str) else None,
        model_name=base_response["model_name"] if isinstance(base_response["model_name"], str) else None,
    )


def _build_command(binary_path: Path, model_path: Path, audio_path: Path, language: str | None) -> list[str]:
    command = [str(binary_path), "-m", str(model_path), "-f", str(audio_path), "-nt"]
    safe_language = _safe_language(language)
    if safe_language:
        command.extend(["-l", safe_language])
    return command


def _safe_language(language: str | None) -> str | None:
    if not language:
        return None
    value = language.strip()
    if not _SAFE_LANGUAGE_RE.match(value):
        return None
    return value


def _extract_transcript(stdout: str | None, output_dir: Path, sensitive_paths: tuple[Path, ...]) -> str:
    candidates: list[str] = []
    if stdout:
        candidates.append(stdout)
    candidates.extend(_read_output_text_files(output_dir))
    sensitive_values = tuple(str(path) for path in sensitive_paths)
    lines: list[str] = []
    for candidate in candidates:
        lines.extend(_clean_transcript_line(line, sensitive_values) for line in candidate.splitlines())
    transcript = _WHITESPACE_RE.sub(" ", " ".join(line for line in lines if line).strip())
    return transcript[:MAX_TRANSCRIPT_CHARS]


def _read_output_text_files(output_dir: Path) -> list[str]:
    texts: list[str] = []
    try:
        output_files = sorted(
            path
            for path in output_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".txt", ".srt", ".vtt"}
        )
    except Exception:
        return texts
    for path in output_files:
        try:
            texts.append(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
    return texts


def _clean_transcript_line(line: str, sensitive_values: tuple[str, ...]) -> str:
    text = _TIMESTAMP_PREFIX_RE.sub("", line).strip()
    if not text:
        return ""
    normalized = text.lower()
    if any(value and value in text for value in sensitive_values):
        return ""
    if any(term in normalized for term in _SENSITIVE_TERMS):
        return ""
    if normalized.startswith(_LOG_PREFIXES):
        return ""
    if _looks_like_path_line(text):
        return ""
    return text


def _looks_like_path_line(text: str) -> bool:
    normalized = text.lower()
    if "://" in normalized:
        return True
    if re.search(r"(?:^|\s)/(?:users|tmp|var|private|applications|volumes)/", normalized):
        return True
    if re.search(r"[a-z]:\\", text, flags=re.IGNORECASE):
        return True
    return False


def _cleanup_temp_dir(temp_dir: Path | None) -> bool:
    if temp_dir is None:
        return True
    try:
        _delete_temp_tree(temp_dir)
    except FileNotFoundError:
        return True
    except Exception:
        return False
    return not temp_dir.exists()


def _delete_temp_tree(path: Path) -> None:
    shutil.rmtree(path)


def _best_effort_cleanup(temp_dir: Path | None) -> None:
    if temp_dir is None:
        return
    try:
        shutil.rmtree(temp_dir)
    except FileNotFoundError:
        pass
    except Exception:
        pass
