import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.core.config import settings
from app.schemas.api import LocalAsrSettingsResponse, LocalAsrSettingsUpdate


BINARY_ENV = "REILINK_LOCAL_ASR_BINARY"
MODEL_ENV = "REILINK_LOCAL_ASR_MODEL"
CONVERTER_ENV = "REILINK_AUDIO_CONVERTER_BINARY"

LOCAL_ASR_BINARY_KEY = "local_asr_binary_path"
LOCAL_ASR_MODEL_KEY = "local_asr_model_path"
AUDIO_CONVERTER_KEY = "audio_converter_binary_path"
LOCAL_ASR_SETTINGS_FILENAME = "local_asr_settings.json"

PathSource = Literal["user_settings", "env", "none"]


@dataclass(frozen=True)
class ResolvedLocalAsrSettings:
    binary_path: Path | None
    model_path: Path | None
    converter_path: Path | None
    binary_source: PathSource = "none"
    model_source: PathSource = "none"
    converter_source: PathSource = "none"

    @property
    def source(self) -> PathSource:
        sources = {self.binary_source, self.model_source, self.converter_source}
        if "user_settings" in sources:
            return "user_settings"
        if "env" in sources:
            return "env"
        return "none"

    @property
    def safe_binary_name(self) -> str | None:
        return _safe_name(self.binary_path)

    @property
    def safe_model_name(self) -> str | None:
        return _safe_name(self.model_path)

    @property
    def safe_converter_name(self) -> str | None:
        return _safe_name(self.converter_path)


def local_asr_settings_path() -> Path:
    return settings.data_dir / LOCAL_ASR_SETTINGS_FILENAME


def get_local_asr_settings_summary() -> LocalAsrSettingsResponse:
    try:
        resolved = resolve_local_asr_settings()
    except Exception:
        resolved = ResolvedLocalAsrSettings(binary_path=None, model_path=None, converter_path=None)
    return _settings_summary(resolved)


def update_local_asr_settings(update: LocalAsrSettingsUpdate) -> LocalAsrSettingsResponse:
    data = _read_user_settings()
    payload = update.model_dump(exclude_unset=True)
    for key, value in payload.items():
        cleaned = _clean_path_value(value)
        if cleaned:
            data[key] = cleaned
        else:
            data.pop(key, None)
    _write_user_settings(data)
    return get_local_asr_settings_summary()


def clear_local_asr_settings() -> LocalAsrSettingsResponse:
    path = local_asr_settings_path()
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
    return get_local_asr_settings_summary()


def resolve_local_asr_settings() -> ResolvedLocalAsrSettings:
    user_settings = _read_user_settings()
    binary_path, binary_source = _resolve_path(user_settings, LOCAL_ASR_BINARY_KEY, BINARY_ENV)
    model_path, model_source = _resolve_path(user_settings, LOCAL_ASR_MODEL_KEY, MODEL_ENV)
    converter_path, converter_source = _resolve_path(user_settings, AUDIO_CONVERTER_KEY, CONVERTER_ENV)
    return ResolvedLocalAsrSettings(
        binary_path=binary_path,
        model_path=model_path,
        converter_path=converter_path,
        binary_source=binary_source,
        model_source=model_source,
        converter_source=converter_source,
    )


def _configured_path_for_env(env_key: str) -> Path | None:
    resolved = resolve_local_asr_settings()
    if env_key == BINARY_ENV:
        return resolved.binary_path
    if env_key == MODEL_ENV:
        return resolved.model_path
    if env_key == CONVERTER_ENV:
        return resolved.converter_path
    return _path_from_value(os.getenv(env_key, ""))


def _settings_summary(resolved: ResolvedLocalAsrSettings) -> LocalAsrSettingsResponse:
    binary_configured = resolved.binary_path is not None
    model_configured = resolved.model_path is not None
    converter_configured = resolved.converter_path is not None
    return LocalAsrSettingsResponse(
        configured=binary_configured and model_configured,
        binary_configured=binary_configured,
        model_configured=model_configured,
        converter_configured=converter_configured,
        safe_binary_name=resolved.safe_binary_name,
        safe_model_name=resolved.safe_model_name,
        safe_converter_name=resolved.safe_converter_name,
        source=resolved.source,
    )


def _resolve_path(data: dict[str, str], key: str, env_key: str) -> tuple[Path | None, PathSource]:
    user_value = _clean_path_value(data.get(key))
    if user_value:
        return Path(user_value).expanduser(), "user_settings"
    env_value = _clean_path_value(os.getenv(env_key, ""))
    if env_value:
        return Path(env_value).expanduser(), "env"
    return None, "none"


def _read_user_settings() -> dict[str, str]:
    path = local_asr_settings_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    data: dict[str, str] = {}
    for key in (LOCAL_ASR_BINARY_KEY, LOCAL_ASR_MODEL_KEY, AUDIO_CONVERTER_KEY):
        value = _clean_path_value(raw.get(key))
        if value:
            data[key] = value
    return data


def _write_user_settings(data: dict[str, str]) -> None:
    path = local_asr_settings_path()
    if not data:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {key: data[key] for key in (LOCAL_ASR_BINARY_KEY, LOCAL_ASR_MODEL_KEY, AUDIO_CONVERTER_KEY) if key in data}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _clean_path_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _path_from_value(value: str | None) -> Path | None:
    cleaned = _clean_path_value(value)
    if not cleaned:
        return None
    return Path(cleaned).expanduser()


def _safe_name(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.name or "已配置"
