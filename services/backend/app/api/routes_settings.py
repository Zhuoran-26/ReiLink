from fastapi import APIRouter

from app.modules.app_settings.store import AppSettingsStore
from app.modules.proactive.trigger import ProactiveCompanion
from app.schemas.api import AppSettings, AppSettingsUpdate

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=AppSettings)
def get_settings() -> AppSettings:
    return AppSettingsStore().load()


@router.post("/settings", response_model=AppSettings)
def update_settings(payload: AppSettingsUpdate) -> AppSettings:
    store = AppSettingsStore()
    previous = store.load()
    saved = store.save(payload)
    if payload.proactive_companion is not None or payload.proactive_sensitivity is not None:
        ProactiveCompanion().sync_settings(previous, saved)
    ProactiveCompanion().suppress_after_system_action("settings_saved")
    return saved
