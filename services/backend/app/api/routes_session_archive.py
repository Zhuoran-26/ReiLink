from fastapi import APIRouter, HTTPException, Query

from app.modules.session_archive.store import SessionArchiveStore
from app.schemas.api import (
    SessionArchiveClearResponse,
    SessionArchiveCreateResponse,
    SessionArchiveCurrentRequest,
    SessionArchiveDeleteResponse,
    SessionArchiveDetail,
    SessionArchiveSearchResponse,
    SessionArchiveSummary,
)

router = APIRouter(tags=["session-archive"])


@router.get("/session-archives", response_model=list[SessionArchiveSummary])
def list_session_archives() -> list[dict]:
    return [_public_summary(item) for item in SessionArchiveStore().list_archives()]


@router.get("/session-archives/search", response_model=SessionArchiveSearchResponse)
def search_session_archives(
    q: str | None = Query(default=None, max_length=120),
    game: str | None = Query(default=None, max_length=80),
    boss: str | None = Query(default=None, max_length=80),
    event_type: str | None = Query(default=None, max_length=80),
    date_from: str | None = Query(default=None, max_length=40),
    date_to: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=20, ge=1, le=50),
) -> dict:
    return SessionArchiveStore().search_archives(
        q=q,
        game=game,
        boss=boss,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


@router.get("/session-archives/{archive_id}", response_model=SessionArchiveDetail)
def get_session_archive(archive_id: str) -> dict:
    try:
        return _public_detail(SessionArchiveStore().get_archive(archive_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session archive not found") from exc


@router.post("/session-archives/archive-current", response_model=SessionArchiveCreateResponse)
def archive_current_session(request: SessionArchiveCurrentRequest) -> dict:
    result = SessionArchiveStore().archive_current(
        session_id=request.session_id,
        events=[_model_dump(event) for event in request.events],
        started_at=request.started_at,
        ended_at=request.ended_at,
        game=request.game,
        area=request.area,
        boss=request.boss,
        source=request.source,
    )
    archive = result.get("archive")
    return {
        "status": result["status"],
        "archive": _public_detail(archive) if isinstance(archive, dict) else None,
        "message": result["message"],
    }


@router.delete("/session-archives/{archive_id}", response_model=SessionArchiveDeleteResponse)
def delete_session_archive(archive_id: str) -> dict:
    try:
        SessionArchiveStore().delete_archive(archive_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="session archive not found") from exc
    return {"status": "deleted", "archive_id": archive_id}


@router.post("/session-archives/clear", response_model=SessionArchiveClearResponse)
def clear_session_archives() -> dict:
    return {"status": "cleared", "deleted_count": SessionArchiveStore().clear_archives()}


def _model_dump(model: object) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()  # type: ignore[attr-defined]


def _public_summary(entry: dict) -> dict:
    return {
        key: entry.get(key)
        for key in (
            "id",
            "session_id",
            "title",
            "created_at",
            "updated_at",
            "started_at",
            "ended_at",
            "source",
            "game",
            "area",
            "boss",
            "summary",
            "event_count",
            "safe_event_summaries",
            "memory_candidate_count",
            "accepted_memory_count",
            "privacy_level",
            "retention_policy",
            "is_deleted",
            "deletion_status",
        )
    }


def _public_detail(entry: dict) -> dict:
    return {**_public_summary(entry), "events": entry.get("events", [])}
