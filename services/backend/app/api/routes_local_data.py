from fastapi import APIRouter

from app.modules.local_data.status import build_local_data_status
from app.schemas.api import LocalDataStatusResponse

router = APIRouter(tags=["local-data"])


@router.get("/local-data/status", response_model=LocalDataStatusResponse)
def local_data_status() -> dict[str, object]:
    return build_local_data_status()
