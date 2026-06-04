import os
from pathlib import Path

from app.schemas.api import LocalAsrStatusResponse


BINARY_ENV = "REILINK_LOCAL_ASR_BINARY"
MODEL_ENV = "REILINK_LOCAL_ASR_MODEL"


def _configured_path(env_key: str) -> Path | None:
    value = os.getenv(env_key, "").strip()
    if not value:
        return None
    return Path(value).expanduser()


def _safe_name(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.name or "已配置"


def get_local_asr_status() -> LocalAsrStatusResponse:
    try:
        return _detect_local_asr_status()
    except Exception:
        return LocalAsrStatusResponse(
            status="local_asr_not_configured",
            available=False,
            display_message="本地语音识别配置读取失败",
        )


def _detect_local_asr_status() -> LocalAsrStatusResponse:
    binary_path = _configured_path(BINARY_ENV)
    model_path = _configured_path(MODEL_ENV)
    binary_configured = binary_path is not None
    model_configured = model_path is not None
    safe_binary_name = _safe_name(binary_path)
    safe_model_name = _safe_name(model_path)

    if not binary_configured and not model_configured:
        return LocalAsrStatusResponse(
            status="local_asr_not_configured",
            display_message="本地语音识别未配置",
        )

    binary_present = bool(binary_path and binary_path.is_file())
    if binary_configured and not binary_present:
        return LocalAsrStatusResponse(
            status="local_asr_binary_missing",
            binary_configured=True,
            binary_present=False,
            model_configured=model_configured,
            model_present=bool(model_path and model_path.is_file()),
            display_message="缺少本地识别程序",
            safe_binary_name=safe_binary_name,
            safe_model_name=safe_model_name,
        )

    binary_executable = bool(binary_path and os.access(binary_path, os.X_OK))
    if binary_configured and binary_present and not binary_executable:
        return LocalAsrStatusResponse(
            status="local_asr_binary_not_executable",
            binary_configured=True,
            binary_present=True,
            binary_executable=False,
            model_configured=model_configured,
            model_present=bool(model_path and model_path.is_file()),
            display_message="本地识别程序不可执行",
            safe_binary_name=safe_binary_name,
            safe_model_name=safe_model_name,
        )

    if not model_configured:
        return LocalAsrStatusResponse(
            status="local_asr_not_configured",
            binary_configured=binary_configured,
            binary_present=binary_present,
            binary_executable=binary_executable,
            display_message="本地语音识别模型未配置",
            safe_binary_name=safe_binary_name,
        )

    model_present = bool(model_path and model_path.is_file())
    if not model_present:
        return LocalAsrStatusResponse(
            status="local_asr_model_missing",
            binary_configured=binary_configured,
            binary_present=binary_present,
            binary_executable=binary_executable,
            model_configured=True,
            model_present=False,
            display_message="缺少本地语音模型",
            safe_binary_name=safe_binary_name,
            safe_model_name=safe_model_name,
        )

    return LocalAsrStatusResponse(
        status="local_asr_ready",
        available=True,
        binary_configured=True,
        binary_present=True,
        binary_executable=True,
        model_configured=True,
        model_present=True,
        display_message="本地语音识别配置已就绪",
        safe_binary_name=safe_binary_name,
        safe_model_name=safe_model_name,
    )
