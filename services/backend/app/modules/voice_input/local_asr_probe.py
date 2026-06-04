import subprocess
import time

from app.modules.voice_input.local_asr_config import BINARY_ENV, MODEL_ENV, _configured_path, get_local_asr_status
from app.schemas.api import LocalAsrProbeResponse


PROBE_TIMEOUT_SECONDS = 3
HELP_LIKE_TERMS = ("usage", "help", "options", "version", "whisper")


def probe_local_asr_binary(timeout_seconds: int = PROBE_TIMEOUT_SECONDS) -> LocalAsrProbeResponse:
    started_at = time.monotonic()
    config = get_local_asr_status()
    if config.status != "local_asr_ready":
        return LocalAsrProbeResponse(
            status="local_asr_probe_not_ready",
            available=False,
            display_message="本地语音识别配置未就绪，未执行检查",
            binary_name=config.safe_binary_name,
            model_name=config.safe_model_name,
            duration_ms=_elapsed_ms(started_at),
        )

    binary_path = _configured_path(BINARY_ENV)
    if binary_path is None:
        return LocalAsrProbeResponse(
            status="local_asr_probe_not_ready",
            available=False,
            display_message="本地语音识别配置未就绪，未执行检查",
            binary_name=config.safe_binary_name,
            model_name=config.safe_model_name,
            duration_ms=_elapsed_ms(started_at),
        )

    # This only proves the binary can be launched. It does not validate model
    # compatibility and never performs transcription.
    attempts = (("--help",), ("-h",))
    try:
        for args in attempts:
            result = subprocess.run(
                [str(binary_path), *args],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            if _is_probe_success(result):
                return LocalAsrProbeResponse(
                    status="local_asr_probe_succeeded",
                    available=True,
                    display_message="本地语音识别程序可以启动",
                    binary_name=config.safe_binary_name,
                    model_name=config.safe_model_name,
                    duration_ms=_elapsed_ms(started_at),
                )
    except subprocess.TimeoutExpired:
        return LocalAsrProbeResponse(
            status="local_asr_probe_timed_out",
            available=False,
            display_message="本地语音识别程序启动超时",
            binary_name=config.safe_binary_name,
            model_name=config.safe_model_name,
            duration_ms=_elapsed_ms(started_at),
        )
    except OSError:
        return LocalAsrProbeResponse(
            status="local_asr_probe_error",
            available=False,
            display_message="本地语音识别程序无法启动",
            binary_name=config.safe_binary_name,
            model_name=config.safe_model_name,
            duration_ms=_elapsed_ms(started_at),
        )
    except Exception:
        return LocalAsrProbeResponse(
            status="local_asr_probe_error",
            available=False,
            display_message="本地语音识别检查失败",
            binary_name=config.safe_binary_name,
            model_name=config.safe_model_name,
            duration_ms=_elapsed_ms(started_at),
        )

    return LocalAsrProbeResponse(
        status="local_asr_probe_failed",
        available=False,
        display_message="本地语音识别程序启动失败",
        binary_name=config.safe_binary_name,
        model_name=config.safe_model_name,
        duration_ms=_elapsed_ms(started_at),
    )


def _elapsed_ms(started_at: float) -> int:
    return max(0, round((time.monotonic() - started_at) * 1000))


def _is_probe_success(result: subprocess.CompletedProcess[str]) -> bool:
    if result.returncode == 0:
        return True
    return _looks_like_help(result.stdout) or _looks_like_help(result.stderr)


def _looks_like_help(text: str | None) -> bool:
    if not text:
        return False
    normalized = text.lower()
    return any(term in normalized for term in HELP_LIKE_TERMS)
