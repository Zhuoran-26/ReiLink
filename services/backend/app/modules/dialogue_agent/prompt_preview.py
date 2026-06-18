from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import active_persona_mode
from app.modules.dialogue_agent.intent import detect_intent
from app.modules.dialogue_agent.metrics import get_last_chat_metrics
from app.modules.dialogue_agent.routing import select_model_route
from app.modules.dialogue_agent.session_focus import resolve_session_focus
from app.modules.game_context.context import GameContextResolver
from app.modules.game_session.state import GameSessionStore, _fails_current_boss
from app.modules.knowledge.retriever import GameKnowledgeRetriever, KnowledgeRetrievalResult
from app.modules.memory.profile import BOSS_FRESHNESS, PlayerMemory
from app.modules.memory.store import ConversationStore
from app.modules.persona_engine.engine import PersonaEngine

PROMPT_ORDER = [
    "base_system_safety",
    "persona_pack",
    "memory",
    "current_session_context",
    "session_focus",
    "game_state",
    "knowledge",
    "current_user_message",
]


def build_prompt_preview(session_id: str = "default") -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    store = ConversationStore()
    memory = PlayerMemory()
    game_session = GameSessionStore()

    entries = store.read_session(session_id)
    current_user_message = entries[-1].user_message if entries else None
    previous_user_messages = [entry.user_message for entry in entries[:-1]][-8:]
    session_focus = (
        resolve_session_focus(current_user_message, previous_user_messages)
        if current_user_message
        else resolve_session_focus("", previous_user_messages)
    )

    game_debug = game_session.debug_state(now=now)
    game_context = GameContextResolver(game_session=game_session).resolve(
        user_message=current_user_message or "",
        now=now,
    )
    game_prompt_summary = game_session.build_prompt_summary(now=now, session_focus_boss=session_focus.boss)
    knowledge_result = _knowledge_summary_result(current_user_message, session_focus.boss, game_debug, game_context)
    prompt_memory_block = memory.retrieve_prompt_memory(
        user_message=current_user_message or "",
        current_game=game_context.active_game_display_name or game_debug.get("current_game"),
        current_boss=session_focus.boss or ((game_debug.get("current_boss") or {}).get("name")),
        input_source="text",
        update_usage=False,
        now=now,
    )
    memory_debug_items = prompt_memory_block.as_debug_items()
    skipped_memory, memory_warnings = _skipped_memory_items(memory, memory_debug_items, game_debug, now)
    session_items = store.recent_context(session_id)
    persona_pack_summary = PersonaEngine().persona_pack_summary()

    warnings = [
        *(game_context.warnings or []),
        *memory_warnings,
        *_persona_pack_warnings(persona_pack_summary),
        *_game_state_warnings(game_debug),
        *_message_warnings(current_user_message),
    ]

    return _sanitize_preview(
        {
            "persona_mode": active_persona_mode(),
            "current_user_message": current_user_message,
            "prompt_order": PROMPT_ORDER,
            "model_route_summary": _model_route_summary(current_user_message),
            "game_context_summary": game_context.model_dump(mode="json"),
            "session_focus_summary": {
                "boss": session_focus.boss,
                "source": session_focus.source,
                "prompt_line": session_focus.as_prompt_line() if session_focus.has_boss else "",
            },
            "game_state_summary": {
                "current_game": game_debug.get("current_game"),
                "current_boss": game_debug.get("current_boss"),
                "current_activity": game_debug.get("current_activity"),
                "freshness": (game_debug.get("current_boss") or {}).get("freshness") or "none",
                "death_count": game_debug.get("death_count"),
                "frustration_count": game_debug.get("frustration_count"),
                "last_attempted_boss": game_debug.get("last_attempted_boss"),
                "last_cleared_boss": game_debug.get("last_cleared_boss"),
                "boss_history": _brief_boss_history(game_debug.get("boss_history") or []),
                "injected_summary": game_prompt_summary,
            },
            "persona_pack_summary": persona_pack_summary,
            "knowledge_summary": knowledge_result.as_debug_dict(),
            "memory_summary": {
                "injected": memory_debug_items,
                "skipped": skipped_memory,
                "active_state": memory.active_memory_state(now=now),
                "retrieval": prompt_memory_block.as_debug_dict(),
            },
            "final_context_summary": _final_context_summary(
                current_user_message=current_user_message,
                session_items=session_items,
                session_focus_line=session_focus.as_prompt_line() if session_focus.has_boss else "",
                game_prompt_summary=game_prompt_summary,
                knowledge_result=knowledge_result,
                memory_items=memory_debug_items,
                prompt_memory_block=prompt_memory_block.as_debug_dict(),
                persona_pack_summary=persona_pack_summary,
            ),
            "warnings": _dedupe(warnings),
        }
    )


def _final_context_summary(
    current_user_message: str | None,
    session_items: list[dict[str, str]],
    session_focus_line: str,
    game_prompt_summary: str,
    knowledge_result: KnowledgeRetrievalResult,
    memory_items: list[dict[str, str]],
    prompt_memory_block: dict[str, Any],
    persona_pack_summary: dict[str, Any],
) -> dict[str, Any]:
    blocks = [
        {
            "name": "base_system_safety",
            "present": True,
            "summary": "ReiLink identity, safety, privacy, memory, knowledge, and proactive boundaries enabled.",
        },
        {
            "name": "persona_pack",
            "present": bool(persona_pack_summary.get("enabled")),
            "summary": (
                f"{persona_pack_summary.get('name') or 'Rei'} "
                f"v{persona_pack_summary.get('version') or 'unknown'} / "
                f"{persona_pack_summary.get('status') or 'unknown'}"
            ),
            "loaded_sections": persona_pack_summary.get("loaded_sections") or [],
            "injected_sections": persona_pack_summary.get("injected_sections") or [],
            "missing_sections": persona_pack_summary.get("missing_sections") or [],
            "omitted_sections": persona_pack_summary.get("omitted_sections") or [],
            "fallback_used": bool(persona_pack_summary.get("fallback_used")),
            "persona_section_truncated": bool(persona_pack_summary.get("persona_section_truncated")),
            "truncated_sections": persona_pack_summary.get("truncated_sections") or [],
            "prompt_char_count": persona_pack_summary.get("prompt_char_count"),
            "prompt_char_budget": persona_pack_summary.get("prompt_char_budget"),
            "raw_content_omitted": True,
            "path_omitted": True,
        },
        {
            "name": "current_user_message",
            "present": bool(current_user_message),
            "summary": _truncate(current_user_message or ""),
        },
        {
            "name": "current_session_context",
            "present": bool(session_items),
            "items": [_truncate(item["text"]) for item in session_items],
        },
        {
            "name": "session_focus",
            "present": bool(session_focus_line),
            "summary": _truncate(session_focus_line),
        },
        {
            "name": "game_state",
            "present": bool(game_prompt_summary),
            "summary": _truncate(game_prompt_summary, limit=180),
        },
        {
            "name": "knowledge",
            "present": knowledge_result.matched,
            "items": [_truncate(f"{snippet.title}: {snippet.content}", limit=160) for snippet in knowledge_result.snippets],
        },
        {
            "name": "memory",
            "present": bool(memory_items),
            "items": [_truncate(item["text"]) for item in memory_items],
            "retrieved_count": prompt_memory_block.get("retrieved_count", 0),
            "omitted_count": prompt_memory_block.get("omitted_count", 0),
            "token_estimate": prompt_memory_block.get("token_estimate", 0),
            "safety_notes": prompt_memory_block.get("safety_notes") or [],
        },
    ]
    return {
        "blocks": blocks,
        "raw_prompt_omitted": True,
        "memory_injected_count": len(memory_items),
    }


def _knowledge_summary_result(
    current_user_message: str | None,
    session_focus_boss: str | None,
    game_debug: dict[str, Any],
    game_context: Any,
) -> KnowledgeRetrievalResult:
    if not current_user_message:
        return GameKnowledgeRetriever().empty_result()
    intent_result = detect_intent(current_user_message)
    current_boss = session_focus_boss or ((game_debug.get("current_boss") or {}).get("name"))
    detected_game = (
        game_context.detected_game.model_dump()
        if game_context.active_source == "detector"
        else None
    )
    manual_override = (
        game_context.manual_override.model_dump()
        if game_context.manual_override.enabled
        else None
    )
    return GameKnowledgeRetriever().retrieve(
        current_game=game_context.active_game_display_name or game_debug.get("current_game"),
        user_message=current_user_message,
        current_boss=current_boss,
        game_session_state=game_debug,
        detected_game=detected_game,
        manual_override=manual_override,
        intent=intent_result.intent,
    )


def _model_route_summary(current_user_message: str | None) -> dict[str, Any]:
    metrics = get_last_chat_metrics().as_dict()
    if current_user_message:
        intent = detect_intent(current_user_message).intent
        route = select_model_route(intent, current_user_message)
        return {
            "selected_model": route.selected_model,
            "model_route_mode": route.model_route_mode,
            "route_reason": route.route_reason,
            "route_intent": route.route_intent,
            "estimated_complexity": route.estimated_complexity,
            "provider_latency_ms": metrics.get("provider_latency_ms", 0),
            "semantic_extraction_model": metrics.get("semantic_extraction_model"),
            "main_reply_model": metrics.get("main_reply_model") or metrics.get("selected_model"),
        }
    return {
        "selected_model": metrics.get("selected_model"),
        "model_route_mode": metrics.get("model_route_mode"),
        "route_reason": metrics.get("route_reason"),
        "route_intent": metrics.get("route_intent") or metrics.get("intent"),
        "estimated_complexity": metrics.get("estimated_complexity"),
        "provider_latency_ms": metrics.get("provider_latency_ms", 0),
        "semantic_extraction_model": metrics.get("semantic_extraction_model"),
        "main_reply_model": metrics.get("main_reply_model") or metrics.get("selected_model"),
    }


def _brief_boss_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": item.get("name"),
            "status": item.get("status"),
            "freshness": item.get("freshness"),
            "age_hours": item.get("age_hours"),
            "last_activity": item.get("last_activity"),
            "source": item.get("source"),
        }
        for item in history[-6:]
    ]


def _skipped_memory_items(
    memory: PlayerMemory,
    injected: list[dict[str, str]],
    game_debug: dict[str, Any],
    now: datetime,
) -> tuple[list[dict[str, Any]], list[str]]:
    profile = memory.load_profile()
    injected_fields = {(item.get("source"), item.get("field"), item.get("text")) for item in injected}
    skipped: list[dict[str, Any]] = []
    warnings: list[str] = []

    game_boss = (game_debug.get("current_boss") or {}).get("name")
    game_freshness = (game_debug.get("current_boss") or {}).get("freshness")
    profile_boss_text = f"玩家当前卡点：{profile.current_boss}" if profile.current_boss else None

    if profile.current_boss and ("profile", "current_boss", profile_boss_text) not in injected_fields:
        reason = "not_selected"
        if game_boss and game_freshness == "fresh" and profile.current_boss != game_boss:
            reason = "conflict_with_fresh_game_state"
            warnings.append("memory boss conflicts with fresh game state")
        elif _age_exceeds(profile.memory_updated_at.get("current_boss"), now, BOSS_FRESHNESS):
            warnings.append("stale boss memory skipped")
        skipped.append(
            {
                "source": "profile",
                "field": "current_boss",
                "text": profile_boss_text,
                "timestamp": profile.memory_updated_at.get("current_boss"),
                "reason": reason,
            }
        )

    for episode in memory.recent_episodes(limit=5):
        summary = episode.get("summary")
        if not summary:
            continue
        episode_text = str(summary)
        if any(item.get("text") == episode_text for item in injected):
            continue
        reason = "not_selected"
        if _age_exceeds(episode.get("timestamp"), now, BOSS_FRESHNESS):
            reason = "stale"
        skipped.append(
            {
                "source": "episode",
                "field": "summary",
                "text": episode_text,
                "timestamp": episode.get("timestamp"),
                "reason": reason,
            }
        )
    return skipped[:5], warnings


def _game_state_warnings(game_debug: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not game_debug.get("current_boss") and game_debug.get("last_attempted_boss"):
        warnings.append("current_boss is null but last_attempted_boss exists")
    for item in game_debug.get("boss_history") or []:
        if item.get("freshness") == "stale" and item.get("status") in {"current", "attempted", "failed"}:
            warnings.append("stale boss memory skipped")
            break
    return warnings


def _message_warnings(message: str | None) -> list[str]:
    if not message:
        return []
    compact = re.sub(r"\s+", "", message.lower())
    clear_markers = ("打过", "打過", "过", "過", "赢", "贏")
    if _fails_current_boss(message) and any(marker in compact for marker in clear_markers):
        return ["current user message contains negated clear phrase"]
    return []


def _persona_pack_warnings(summary: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    status = summary.get("status")
    if status and status != "loaded":
        warnings.append(f"persona_pack_{status}")
    if summary.get("persona_section_truncated"):
        warnings.append("persona_section_truncated")
    for error in summary.get("errors") or []:
        warnings.append(str(error))
    return warnings


def _age_exceeds(timestamp: str | None, now: datetime, ttl: timedelta) -> bool:
    parsed = _parse_timestamp(timestamp)
    return bool(parsed and now - parsed > ttl)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _truncate(text: str, limit: int = 120) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def _sanitize_preview(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_preview(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_preview(item) for item in value]
    if isinstance(value, str):
        sanitized = re.sub(
            r"(?i)(api[_-]?key|deepseek[_-]?api[_-]?key|authorization)\s*[:=]\s*\S+",
            "credential=<redacted>",
            value,
        )
        sanitized = re.sub(r"/Users/[^\s`'\"\]\),]+", "<local-path>", sanitized)
        sanitized = re.sub(r"[A-Za-z]:\\[^\s`'\"\]\),]+", "<local-path>", sanitized)
        sanitized = sanitized.replace("`.env`", "environment files")
        sanitized = sanitized.replace(".env", "environment files")
        sanitized = re.sub(r"(?i)\braw\s+json\b", "raw diagnostics", sanitized)
        sanitized = re.sub(r"(?i)\braw\s+std(out|err)\b", "runtime logs", sanitized)
        return sanitized
    return value
