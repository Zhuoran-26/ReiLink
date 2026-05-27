from fastapi import APIRouter

from app.modules.persona_engine.engine import PersonaEngine
from app.schemas.api import PersonaPromptRequest, PersonaPromptResponse

router = APIRouter(tags=["persona"])


@router.post("/persona/prompt", response_model=PersonaPromptResponse)
def persona_prompt(request: PersonaPromptRequest) -> PersonaPromptResponse:
    prompt = PersonaEngine().build_prompt(request.persona_id, request.game_context)
    return PersonaPromptResponse(system_prompt=prompt)

