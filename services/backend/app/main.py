from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.api.routes_debug import router as debug_router
from app.api.routes_game import router as game_router
from app.api.routes_health import router as health_router
from app.api.routes_local_data import router as local_data_router
from app.api.routes_memory import router as memory_router
from app.api.routes_persona import router as persona_router
from app.api.routes_proactive import router as proactive_router
from app.api.routes_setup import router as setup_router
from app.api.routes_settings import router as settings_router
from app.api.routes_voice import router as voice_router
from app.api.routes_voice_input import router as voice_input_router
from app.core.config import settings
from app.modules.dialogue_agent.providers import log_provider_state


def create_app() -> FastAPI:
    app = FastAPI(title="ReiLink Backend", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    log_provider_state("startup")
    app.include_router(health_router, prefix="/api")
    app.include_router(debug_router, prefix="/api")
    app.include_router(game_router, prefix="/api")
    app.include_router(persona_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(memory_router, prefix="/api")
    app.include_router(local_data_router, prefix="/api")
    app.include_router(proactive_router, prefix="/api")
    app.include_router(setup_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    app.include_router(voice_router, prefix="/api")
    app.include_router(voice_input_router, prefix="/api")
    return app


app = create_app()
