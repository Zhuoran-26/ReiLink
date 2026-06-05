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
from app.modules.voice_input.audio_conversion import (
    AUDIO_CONVERSION_TIMEOUT_SECONDS,
    AudioConversionResult,
    conversion_required_for_mime,
    get_audio_converter_summary,
    prepare_audio_for_asr,
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
_SRT_INDEX_RE = re.compile(r"^\d+$")
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
    conversion_timeout_seconds: int | float = AUDIO_CONVERSION_TIMEOUT_SECONDS,
    temp_root: str | None = None,
) -> LocalAsrTranscriptionResponse:
    config = get_local_asr_status()
    safe_mime_type = _safe_mime_type(mime_type)
    size_bytes = len(audio_bytes)
    safe_duration_ms = max(0, duration_ms)
    converter_configured, safe_converter_name = get_audio_converter_summary()
    conversion_required = conversion_required_for_mime(safe_mime_type)
    base_response = {
        "duration_ms": safe_duration_ms,
        "size_bytes": size_bytes,
        "mime_type": safe_mime_type,
        "audio_format": safe_mime_type,
        "conversion_status": "audio_conversion_needed" if conversion_required else "audio_conversion_not_needed",
        "conversion_required": conversion_required,
        "converted_mime_type": None,
        "converter_configured": converter_configured,
        "safe_converter_name": safe_converter_name,
        "binary_name": config.safe_binary_name,
        "model_name": config.safe_model_name,
    }

    if config.status != "local_asr_ready":
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_not_ready",
            available=False,
            display_message="本地语音识别配置未就绪",
            temporary_file_cleaned=True,
            temporary_input_cleaned=True,
            temporary_converted_cleaned=True,
            **base_response,
        )
    if size_bytes > MAX_AUDIO_UPLOAD_BYTES:
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_failed",
            available=False,
            display_message="录音文件过大",
            temporary_file_cleaned=True,
            temporary_input_cleaned=True,
            temporary_converted_cleaned=True,
            **base_response,
        )
    if size_bytes <= 0 or not _is_allowed_audio_type(safe_mime_type):
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_failed",
            available=False,
            display_message="录音数据无效",
            temporary_file_cleaned=True,
            temporary_input_cleaned=True,
            temporary_converted_cleaned=True,
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
            temporary_input_cleaned=True,
            temporary_converted_cleaned=True,
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
                temporary_input_cleaned=False,
                temporary_converted_cleaned=True,
                **base_response,
            )
        else:
            conversion = prepare_audio_for_asr(
                input_path=temp_path,
                mime_type=safe_mime_type,
                temp_dir=temp_dir,
                timeout_seconds=conversion_timeout_seconds,
            )
            converted_response = _with_conversion(base_response, conversion)
            if conversion.prepared_path is None:
                response = _conversion_failure_response(conversion, converted_response)
            else:
                response = _run_transcription(
                    binary_path=binary_path,
                    model_path=model_path,
                    audio_path=conversion.prepared_path,
                    temp_dir=temp_dir,
                    language=language,
                    timeout_seconds=timeout_seconds,
                    base_response=converted_response,
                )
    except Exception:
        response = LocalAsrTranscriptionResponse(
            status="local_asr_transcription_error",
            available=False,
            display_message="本地语音识别失败",
            temporary_file_cleaned=bool(temp_path is None or not temp_path.exists()),
            temporary_input_cleaned=bool(temp_path is None or not temp_path.exists()),
            temporary_converted_cleaned=True,
            **base_response,
        )

    cleanup_succeeded = _cleanup_temp_dir(temp_dir)
    if not cleanup_succeeded:
        _best_effort_cleanup(temp_dir)
        return response.model_copy(
            update={
                "status": "local_asr_transcription_cleanup_failed",
                "available": False,
                "display_message": "临时音频清理失败",
                "transcript": "",
                "transcript_char_count": 0,
                "conversion_status": "audio_conversion_cleanup_failed",
                "temporary_file_cleaned": bool(temp_dir is None or not temp_dir.exists()),
                "temporary_input_cleaned": bool(temp_dir is None or not temp_dir.exists()),
                "temporary_converted_cleaned": bool(temp_dir is None or not temp_dir.exists()),
            }
        )

    return response.model_copy(
        update={
            "temporary_file_cleaned": True,
            "temporary_input_cleaned": True,
            "temporary_converted_cleaned": True,
        }
    )


def _with_conversion(base_response: dict[str, object], conversion: AudioConversionResult) -> dict[str, object]:
    return {
        **base_response,
        "conversion_status": conversion.status,
        "conversion_required": conversion.conversion_required,
        "converted_mime_type": conversion.converted_mime_type,
        "converter_configured": conversion.converter_configured,
        "safe_converter_name": conversion.safe_converter_name,
    }


def _conversion_failure_response(
    conversion: AudioConversionResult,
    base_response: dict[str, object],
) -> LocalAsrTranscriptionResponse:
    status = (
        "local_asr_transcription_timed_out"
        if conversion.status == "audio_conversion_timed_out"
        else "local_asr_transcription_failed"
    )
    return LocalAsrTranscriptionResponse(
        status=status,
        available=False,
        display_message=conversion.display_message or "音频格式转换失败",
        temporary_file_cleaned=False,
        temporary_input_cleaned=False,
        temporary_converted_cleaned=bool(conversion.converted_path is None or not conversion.converted_path.exists()),
        **base_response,
    )


def _response_field(base_response: dict[str, object], key: str) -> str | None:
    value = base_response.get(key)
    return value if isinstance(value, str) else None


def _response_bool(base_response: dict[str, object], key: str) -> bool:
    return bool(base_response.get(key))


def _response_int(base_response: dict[str, object], key: str) -> int:
    value = base_response.get(key)
    return int(value) if isinstance(value, int) else 0


def _temporary_converted_cleaned_before_cleanup(base_response: dict[str, object]) -> bool:
    return _response_field(base_response, "converted_mime_type") is None


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
            temporary_input_cleaned=False,
            temporary_converted_cleaned=_temporary_converted_cleaned_before_cleanup(base_response),
            **base_response,
        )
    except OSError:
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_error",
            available=False,
            display_message="本地语音识别程序无法启动",
            temporary_file_cleaned=False,
            temporary_input_cleaned=False,
            temporary_converted_cleaned=_temporary_converted_cleaned_before_cleanup(base_response),
            **base_response,
        )
    except Exception:
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_error",
            available=False,
            display_message="本地语音识别失败",
            temporary_file_cleaned=False,
            temporary_input_cleaned=False,
            temporary_converted_cleaned=_temporary_converted_cleaned_before_cleanup(base_response),
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
            temporary_input_cleaned=False,
            temporary_converted_cleaned=_temporary_converted_cleaned_before_cleanup(base_response),
            **base_response,
        )
    if not transcript:
        return LocalAsrTranscriptionResponse(
            status="local_asr_transcription_no_text",
            available=False,
            display_message="没有识别到文本",
            temporary_file_cleaned=False,
            temporary_input_cleaned=False,
            temporary_converted_cleaned=_temporary_converted_cleaned_before_cleanup(base_response),
            **base_response,
        )
    return LocalAsrTranscriptionResponse(
        status="local_asr_transcription_succeeded",
        available=True,
        display_message="本地语音识别完成",
        transcript=transcript,
        transcript_char_count=len(transcript),
        duration_ms=_response_int(base_response, "duration_ms"),
        size_bytes=_response_int(base_response, "size_bytes"),
        mime_type=_response_field(base_response, "mime_type"),
        audio_format=_response_field(base_response, "audio_format"),
        conversion_status=_response_field(base_response, "conversion_status") or "audio_conversion_not_needed",
        conversion_required=_response_bool(base_response, "conversion_required"),
        converted_mime_type=_response_field(base_response, "converted_mime_type"),
        converter_configured=_response_bool(base_response, "converter_configured"),
        safe_converter_name=_response_field(base_response, "safe_converter_name"),
        temporary_file_cleaned=False,
        temporary_input_cleaned=False,
        temporary_converted_cleaned=_temporary_converted_cleaned_before_cleanup(base_response),
        binary_name=_response_field(base_response, "binary_name"),
        model_name=_response_field(base_response, "model_name"),
    )


def _build_command(binary_path: Path, model_path: Path, audio_path: Path, language: str | None) -> list[str]:
    # v1.1 assumes a whisper.cpp-like CLI: model path, input file path, and no-timestamps output.
    # Real binary compatibility still needs the manual QA checklist because flags and audio formats vary.
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
    if normalized == "webvtt" or _SRT_INDEX_RE.match(normalized):
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
