import time
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from app.modules.dialogue_agent.emotion import build_companion_policy
from app.modules.dialogue_agent.intent import detect_intent
from app.modules.dialogue_agent.metrics import ChatLatencyMetrics, set_last_chat_metrics
from app.modules.dialogue_agent.providers import get_provider, log_provider_state
from app.modules.dialogue_agent.providers import ProviderTimeoutError
from app.modules.dialogue_agent.repetition import (
    build_followup_progression_policy,
    build_repetition_guard,
    build_retry_repetition_guard,
    is_repetitive_reply,
)
from app.modules.dialogue_agent.segmenter import segment_reply
from app.modules.dialogue_agent.semantic_extraction import extract_semantics
from app.modules.dialogue_agent.session_focus import resolve_session_focus
from app.modules.dialogue_agent.style import apply_rei_style
from app.modules.dialogue_agent.validator import validate_or_repair
from app.modules.elden_ring_knowledge.terminology import normalize_terminology
from app.modules.app_settings.store import AppSettingsStore
from app.modules.game_context.context import GameContextResolver, game_status_from_context
from app.modules.game_detector.detector import (
    LocalGameDetector,
)
from app.modules.game_session.state import GameSessionStore
from app.modules.knowledge.retriever import GameKnowledgeRetriever
from app.modules.memory.pending import PendingMemoryQueue
from app.modules.memory.profile import PlayerMemory
from app.modules.memory.store import ConversationStore
from app.modules.persona_engine.engine import PersonaEngine
from app.schemas.api import ChatRequest, ChatResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


class DialogueError(RuntimeError):
    pass


class DialogueTimeoutError(DialogueError):
    pass


class DialogueAgent:
    persona_id = "rei_like"

    def __init__(self) -> None:
        self.detector = LocalGameDetector()
        self.persona = PersonaEngine()
        self.knowledge = GameKnowledgeRetriever()
        self.store = ConversationStore()
        self.memory = PlayerMemory()
        self.game_session = GameSessionStore()
        self.provider = get_provider()

    def chat(self, request: ChatRequest, background_tasks: Any | None = None) -> ChatResponse:
        total_start = time.perf_counter()
        request_started_at = datetime.now(timezone.utc)
        log_provider_state("chat")
        app_settings = AppSettingsStore().load()
        detection = self.detector.detect(now=request_started_at)
        game_context = GameContextResolver(detector=self.detector, game_session=self.game_session).resolve(
            user_message=request.message,
            detected_game=detection,
            now=request_started_at,
            sync_session=True,
        )
        game_status = game_status_from_context(game_context)
        detected_game = detection.model_dump() if app_settings.auto_game_detection == "on" else None
        manual_override = (
            game_context.manual_override.model_dump()
            if game_context.manual_override.enabled
            else None
        )
        intent_result = detect_intent(request.message)
        memory_context = self.memory.build_prompt_context_with_provenance()
        recent_user_messages = self.store.recent_user_messages(request.session_id)
        recent_assistant_replies = self.store.recent_assistant_replies(request.session_id)
        session_focus = resolve_session_focus(request.message, recent_user_messages)
        now = request_started_at
        semantic_game_state = self.game_session.debug_state(now=now)
        defer_semantic_shadow = background_tasks is not None
        semantic_extraction = extract_semantics(
            request.message,
            intent_result.intent,
            semantic_game_state,
            session_focus_boss=session_focus.boss,
            run_llm_shadow=not defer_semantic_shadow,
        )
        self.game_session.update_from_user_message(
            request.message,
            intent_result.intent,
            game_status.model_dump(),
            now,
            session_focus_boss=session_focus.boss,
            semantic_game_event=(semantic_extraction.get("final_decision") or {}).get("game_event"),
        )
        game_session_debug = self.game_session.debug_state(now=now)
        game_session_summary = self.game_session.build_prompt_summary(now=now, session_focus_boss=session_focus.boss)
        session_context_items = [item["text"] for item in self.store.recent_context(request.session_id)]
        if session_focus.has_boss:
            session_context_items.insert(0, session_focus.as_prompt_line())
        if game_session_summary:
            insert_at = 1 if session_focus.has_boss else 0
            session_context_items.insert(insert_at, game_session_summary)
        session_context = "\n".join(f"- {text}" for text in session_context_items)
        repetition_guard = "\n".join(
            item
            for item in (
                build_repetition_guard(recent_assistant_replies),
                build_followup_progression_policy(request.message, recent_user_messages),
            )
            if item
        )
        companion_policy = build_companion_policy(request.message, intent_result.intent)
        system_prompt = self.persona.build_prompt(
            self.persona_id,
            game_status.model_dump(),
            intent_result.intent,
            memory_context=memory_context.as_prompt_text(),
            session_context=session_context,
            companion_policy=companion_policy,
            repetition_guard=repetition_guard,
        )
        knowledge_result = self.knowledge.retrieve(
            current_game=game_context.active_game_display_name or game_status.game_name or game_session_debug.get("current_game"),
            user_message=request.message,
            current_boss=session_focus.boss or ((game_session_debug.get("current_boss") or {}).get("name")),
            game_session_state=game_session_debug,
            detected_game=detected_game,
            manual_override=manual_override,
            intent=intent_result.intent,
        )
        snippets = knowledge_result.snippets
        try:
            llm_result = self.provider.generate_with_metrics(system_prompt, request.message, snippets, intent_result.intent)
        except RuntimeError as exc:
            if isinstance(exc, ProviderTimeoutError):
                raise DialogueTimeoutError(str(exc)) from exc
            raise DialogueError(str(exc)) from exc
        reply = self._finalize_reply(llm_result.reply, intent_result.intent, request.session_id, request.message)
        if is_repetitive_reply(reply, recent_assistant_replies):
            retry_prompt = f"{system_prompt}\n{build_retry_repetition_guard(reply)}"
            try:
                retry_result = self.provider.generate_with_metrics(retry_prompt, request.message, snippets, intent_result.intent)
            except RuntimeError:
                logger.exception("repetition retry failed")
            else:
                reply = self._finalize_reply(retry_result.reply, intent_result.intent, request.session_id, request.message)
                llm_result = replace(
                    retry_result,
                    llm_latency_ms=llm_result.llm_latency_ms + retry_result.llm_latency_ms,
                    provider_latency_ms=int(llm_result.provider_latency_ms or llm_result.llm_latency_ms)
                    + int(retry_result.provider_latency_ms or retry_result.llm_latency_ms),
                    fallback_reason=retry_result.fallback_reason or llm_result.fallback_reason,
                )
        reply_segments = segment_reply(reply, intent_result.intent, request.message)
        self.store.append(
            session_id=request.session_id,
            game_id=game_status.game_id,
            persona_id=self.persona_id,
            user_message=request.message,
            assistant_reply=reply,
            timestamp=now,
            assistant_reply_segments=reply_segments.segments,
        )
        memory_start = time.perf_counter()
        if background_tasks is not None:
            background_tasks.add_task(
                self._safe_memory_update,
                request.message,
                reply,
                intent_result.intent,
                now,
                semantic_extraction,
            )
            if (semantic_extraction.get("llm_shadow") or {}).get("skip_reason") == "shadow_deferred":
                background_tasks.add_task(
                    extract_semantics,
                    request.message,
                    intent_result.intent,
                    semantic_game_state,
                    session_focus_boss=session_focus.boss,
                )
        else:
            self._safe_memory_update(request.message, reply, intent_result.intent, now, semantic_extraction)
        memory_latency_ms = int((time.perf_counter() - memory_start) * 1000)
        total_latency_ms = int((time.perf_counter() - total_start) * 1000)
        provider_latency_ms = int(llm_result.provider_latency_ms or llm_result.llm_latency_ms)
        metrics = ChatLatencyMetrics(
            intent=intent_result.intent,
            selected_model=llm_result.selected_model,
            model_used=llm_result.selected_model,
            main_reply_model=llm_result.selected_model,
            model_route_mode=llm_result.model_route_mode,
            route_reason=llm_result.route_reason,
            route_intent=llm_result.route_intent or intent_result.intent,
            estimated_complexity=llm_result.estimated_complexity,
            fallback_reason=llm_result.fallback_reason,
            thinking_enabled=llm_result.thinking_enabled,
            reasoning_effort=llm_result.reasoning_effort,
            prompt_tokens_estimate=llm_result.prompt_tokens_estimate,
            llm_latency_ms=llm_result.llm_latency_ms,
            provider_latency_ms=provider_latency_ms,
            memory_latency_ms=memory_latency_ms,
            total_latency_ms=total_latency_ms,
            response_latency_ms=total_latency_ms,
            request_started_at=request_started_at.isoformat(),
            reply_segments_count=len(reply_segments.segments),
            segmenter_mode=reply_segments.mode,
            semantic_extraction_called=bool(semantic_extraction.get("llm_called")),
            semantic_extraction_model=semantic_extraction.get("semantic_extraction_model"),
            semantic_extraction_latency_ms=int(semantic_extraction.get("semantic_extraction_latency_ms") or 0),
            semantic_extraction_parse_error=semantic_extraction.get("parse_error"),
            knowledge_matched=knowledge_result.matched,
            knowledge_game_id=knowledge_result.game_id,
            knowledge_game_display_name=knowledge_result.game_display_name,
            knowledge_match_source=knowledge_result.match_source,
            knowledge_path=knowledge_result.knowledge_path,
            manifest_path=knowledge_result.manifest_path,
            manifest_status=knowledge_result.manifest_status,
            knowledge_pack_version=knowledge_result.knowledge_pack_version,
            knowledge_pack_language=knowledge_result.knowledge_pack_language,
            knowledge_pack_status=knowledge_result.knowledge_pack_status,
            coverage=knowledge_result.coverage,
            last_updated=knowledge_result.last_updated,
            knowledge_supported_games_count=knowledge_result.supported_games_count,
            knowledge_fallback_reason=knowledge_result.fallback_reason,
            knowledge_confidence=knowledge_result.confidence,
            active_game_id=knowledge_result.game_id,
            active_game_display_name=knowledge_result.game_display_name,
            active_source=knowledge_result.active_source,
            support_status=knowledge_result.support_status,
            knowledge_available=knowledge_result.knowledge_available,
            matched_topics=knowledge_result.topics,
            snippets_count=len(snippets),
            snippet_titles=[snippet.title for snippet in snippets],
            snippet_previews=[snippet.content for snippet in snippets],
            matched_terms=[term for snippet in snippets for term in snippet.matched_terms],
            result_scores=[snippet.score for snippet in snippets],
            knowledge_used_in_prompt=bool(snippets),
            knowledge_retrieval_status=knowledge_result.retrieval_status,
            knowledge_not_used_reason=knowledge_result.not_used_reason,
            knowledge_retrieval_min_score=knowledge_result.retrieval_min_score,
        )
        set_last_chat_metrics(metrics)
        logger.info(
            "chat latency intent=%s selected_model=%s route_mode=%s route_reason=%s "
            "thinking_enabled=%s reasoning_effort=%s prompt_tokens_estimate=%s "
            "llm_latency_ms=%s provider_latency_ms=%s memory_latency_ms=%s total_latency_ms=%s fallback_reason=%s",
            metrics.intent,
            metrics.selected_model,
            metrics.model_route_mode,
            metrics.route_reason,
            metrics.thinking_enabled,
            metrics.reasoning_effort,
            metrics.prompt_tokens_estimate,
            metrics.llm_latency_ms,
            metrics.provider_latency_ms,
            metrics.memory_latency_ms,
            metrics.total_latency_ms,
            metrics.fallback_reason,
        )
        return ChatResponse(
            reply=reply,
            reply_segments=reply_segments.segments,
            segmenter_mode=reply_segments.mode,
            persona_id=self.persona_id,
            game_status=game_status.status,
            sources=sorted({snippet.source for snippet in snippets}),
            timestamp=now,
            request_started_at=request_started_at,
            response_latency_ms=total_latency_ms,
            provider_latency_ms=provider_latency_ms,
            model_used=llm_result.selected_model,
            route_reason=llm_result.route_reason,
        )

    def _safe_memory_update(
        self,
        user_message: str,
        reply: str,
        intent: str,
        timestamp: datetime,
        semantic_extraction: dict[str, Any] | None = None,
    ) -> None:
        start = time.perf_counter()
        try:
            pending = PendingMemoryQueue().generate_and_enqueue(
                user_message,
                reply,
                intent,
                timestamp,
                self.game_session.debug_state(now=timestamp),
                semantic_extraction=semantic_extraction,
            )
        except Exception:
            logger.exception("memory update error")
        else:
            logger.info(
                "memory update completed pending_count=%s memory_latency_ms=%s",
                len(pending),
                int((time.perf_counter() - start) * 1000),
            )

    def _finalize_reply(self, raw_reply: str, intent: str, session_id: str, user_message: str) -> str:
        reply = apply_rei_style(validate_or_repair(raw_reply, intent), seed=f"{session_id}:{user_message}")
        return normalize_terminology(reply)
