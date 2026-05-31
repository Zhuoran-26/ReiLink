from fastapi import APIRouter

from app.core.config import active_model_preference, active_persona_mode, settings
from app.schemas.api import SetupStatusResponse

router = APIRouter(tags=["setup"])


def build_setup_status() -> SetupStatusResponse:
    configured_provider = settings.llm_provider.lower().strip()
    api_key_loaded = bool(settings.deepseek_api_key)
    provider_selected = configured_provider == "deepseek"
    missing_items: list[str] = []
    if not provider_selected:
        missing_items.append("LLM_PROVIDER")
    if not api_key_loaded:
        missing_items.append("DEEPSEEK_API_KEY")
    provider_configured = provider_selected and api_key_loaded

    return SetupStatusResponse(
        backend_ready=True,
        provider_configured=provider_configured,
        provider="deepseek",
        api_key_loaded=api_key_loaded,
        base_url=settings.deepseek_base_url,
        model_preference=active_model_preference(),
        persona_mode=active_persona_mode(),
        memory_ready=settings.data_dir.is_dir(),
        knowledge_ready=(settings.knowledge_games_dir / "catalog.json").is_file(),
        needs_setup=not provider_configured,
        missing_items=missing_items,
        fast_model=settings.deepseek_model_fast,
        pro_model=settings.deepseek_model_pro,
    )


@router.get("/setup/status", response_model=SetupStatusResponse)
def setup_status() -> SetupStatusResponse:
    return build_setup_status()
