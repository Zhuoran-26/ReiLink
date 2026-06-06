import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.modules.voice_input.audio_probe import _safe_mime_type
from app.modules.voice_input.local_asr_settings import CONVERTER_ENV, _safe_name, resolve_local_asr_settings


AUDIO_CONVERSION_TIMEOUT_SECONDS = 10

_WAV_PCM_MIME_TYPES = {
    "audio/l16",
    "audio/pcm",
    "audio/vnd.wave",
    "audio/wav",
    "audio/wave",
    "audio/x-pcm",
    "audio/x-wav",
}


@dataclass(frozen=True)
class AudioConversionResult:
    status: str
    conversion_required: bool
    prepared_path: Path | None
    converted_path: Path | None = None
    converted_mime_type: str | None = None
    converter_configured: bool = False
    safe_converter_name: str | None = None
    display_message: str = ""


def conversion_required_for_mime(mime_type: str | None) -> bool:
    safe_mime_type = _safe_mime_type(mime_type)
    if not safe_mime_type:
        return False
    return not (safe_mime_type in _WAV_PCM_MIME_TYPES or "pcm" in safe_mime_type)


def get_audio_converter_summary() -> tuple[bool, str | None]:
    resolved_path = resolve_local_asr_settings().converter_path
    if resolved_path is None:
        return False, None
    if not resolved_path.is_file() or not os.access(resolved_path, os.X_OK):
        return False, _safe_name(resolved_path)
    return True, resolved_path.name


def prepare_audio_for_asr(
    input_path: Path,
    mime_type: str | None,
    temp_dir: Path,
    timeout_seconds: int | float = AUDIO_CONVERSION_TIMEOUT_SECONDS,
) -> AudioConversionResult:
    conversion_required = conversion_required_for_mime(mime_type)
    converter_configured, safe_converter_name = get_audio_converter_summary()
    if not input_path.is_file() or input_path.stat().st_size <= 0:
        return AudioConversionResult(
            status="audio_conversion_invalid_input",
            conversion_required=conversion_required,
            prepared_path=None,
            converter_configured=converter_configured,
            safe_converter_name=safe_converter_name,
            display_message="录音临时文件无效",
        )
    if not conversion_required:
        return AudioConversionResult(
            status="audio_conversion_not_needed",
            conversion_required=False,
            prepared_path=input_path,
            converter_configured=converter_configured,
            safe_converter_name=safe_converter_name,
            display_message="当前录音格式无需转换",
        )

    converter_path = _configured_converter_path()
    if converter_path is None:
        return AudioConversionResult(
            status="audio_conversion_not_configured",
            conversion_required=True,
            prepared_path=None,
            converter_configured=False,
            safe_converter_name=safe_converter_name,
            display_message="尚未配置音频转换工具",
        )

    output_path = temp_dir / "recording-converted.wav"
    command = [str(converter_path), "-y", "-i", str(input_path), "-ar", "16000", "-ac", "1", str(output_path)]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return AudioConversionResult(
            status="audio_conversion_timed_out",
            conversion_required=True,
            prepared_path=None,
            converted_path=output_path,
            converter_configured=True,
            safe_converter_name=converter_path.name,
            display_message="音频格式转换超时",
        )
    except OSError:
        return AudioConversionResult(
            status="audio_conversion_failed",
            conversion_required=True,
            prepared_path=None,
            converted_path=output_path,
            converter_configured=True,
            safe_converter_name=converter_path.name,
            display_message="音频格式转换失败",
        )
    except Exception:
        return AudioConversionResult(
            status="audio_conversion_failed",
            conversion_required=True,
            prepared_path=None,
            converted_path=output_path,
            converter_configured=True,
            safe_converter_name=converter_path.name,
            display_message="音频格式转换失败",
        )

    if result.returncode != 0 or not output_path.is_file() or output_path.stat().st_size <= 0:
        return AudioConversionResult(
            status="audio_conversion_failed",
            conversion_required=True,
            prepared_path=None,
            converted_path=output_path,
            converter_configured=True,
            safe_converter_name=converter_path.name,
            display_message="音频格式转换失败",
        )

    return AudioConversionResult(
        status="audio_conversion_succeeded",
        conversion_required=True,
        prepared_path=output_path,
        converted_path=output_path,
        converted_mime_type="audio/wav",
        converter_configured=True,
        safe_converter_name=converter_path.name,
        display_message="音频已转换为 WAV",
    )


def _configured_converter_path() -> Path | None:
    candidate = resolve_local_asr_settings().converter_path
    if candidate is None:
        return None
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        return None
    return candidate
