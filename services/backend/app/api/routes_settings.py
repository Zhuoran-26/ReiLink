from fastapi import APIRouter

from app.modules.app_settings.store import AppSettingsStore
from app.schemas.api import AppSettings, AppSettingsUpdate

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=AppSettings)
def get_settings() -> AppSettings:
    return AppSettingsStore().load()


@router.post("/settings", response_model=AppSettings)
def update_settings(payload: AppSettingsUpdate) -> AppSettings:
    return AppSettingsStore().save(payload)
