import json
from pathlib import Path

from app.core.config import settings
from app.schemas.api import AppSettings, AppSettingsUpdate


def default_app_settings() -> AppSettings:
    persona_mode = "minimal" if settings.persona_mode == "minimal" else "guarded"
    debug_panel = "show" if settings.enable_debug else "hide"
    return AppSettings(persona_mode=persona_mode, debug_panel=debug_panel)


class AppSettingsStore:
    def __init__(self, path: Path | None = None):
        self.path = path or settings.settings_path

    def load(self) -> AppSettings:
        defaults = default_app_settings().model_dump()
        if not self.path.is_file():
            return AppSettings(**defaults)
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return AppSettings(**defaults)
        if not isinstance(raw, dict):
            return AppSettings(**defaults)
        allowed = set(AppSettings.model_fields)
        persisted = {key: value for key, value in raw.items() if key in allowed}
        return AppSettings(**{**defaults, **persisted})

    def save(self, update: AppSettingsUpdate) -> AppSettings:
        merged = {
            **self.load().model_dump(),
            **update.model_dump(exclude_unset=True, exclude_none=True),
        }
        saved = AppSettings(**merged)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(saved.model_dump(), ensure_ascii=False, indent=2)
        self.path.write_text(f"{payload}\n", encoding="utf-8")
        return saved
