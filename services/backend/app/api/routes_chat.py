from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.modules.dialogue_agent.agent import DialogueAgent, DialogueError, DialogueTimeoutError
from app.schemas.api import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, background_tasks: BackgroundTasks) -> ChatResponse:
    try:
        return DialogueAgent().chat(request, background_tasks=background_tasks)
    except DialogueTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except DialogueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
