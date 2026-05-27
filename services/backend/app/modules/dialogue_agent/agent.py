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
from app.modules.dialogue_agent.session_focus import resolve_session_focus
from app.modules.dialogue_agent.style import apply_rei_style
from app.modules.dialogue_agent.validator import validate_or_repair
from app.modules.elden_ring_knowledge.knowledge import EldenRingKnowledge, KnowledgeError
from app.modules.elden_ring_knowledge.terminology import normalize_terminology
from app.modules.game_detector.detector import EldenRingDetector
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
        self.detector = EldenRingDetector()
        self.persona = PersonaEngine()
        self.knowledge = EldenRingKnowledge()
        self.store = ConversationStore()
        self.memory = PlayerMemory()
        self.provider = get_provider()

    def chat(self, request: ChatRequest, background_tasks: Any | None = None) -> ChatResponse:
        total_start = time.perf_counter()
        log_provider_state("chat")
        game_status = self.detector.get_status()
        intent_result = detect_intent(request.message)
        memory_context = self.memory.build_prompt_context_with_provenance()
        recent_user_messages = self.store.recent_user_messages(request.session_id)
        recent_assistant_replies = self.store.recent_assistant_replies(request.session_id)
        session_focus = resolve_session_focus(request.message, recent_user_messages)
        session_context_items = [item["text"] for item in self.store.recent_context(request.session_id)]
        if session_focus.has_boss:
            session_context_items.insert(0, session_focus.as_prompt_line())
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
        snippets = []
        if intent_result.should_retrieve_knowledge:
            try:
                snippets = self.knowledge.search(request.message, intent_result.intent)
            except KnowledgeError as exc:
                raise DialogueError(str(exc)) from exc
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
                )
        reply_segments = segment_reply(reply, intent_result.intent, request.message)
        now = datetime.now(timezone.utc)
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
            background_tasks.add_task(self._safe_memory_update, request.message, reply, intent_result.intent, now)
        else:
            self._safe_memory_update(request.message, reply, intent_result.intent, now)
        memory_latency_ms = int((time.perf_counter() - memory_start) * 1000)
        total_latency_ms = int((time.perf_counter() - total_start) * 1000)
        metrics = ChatLatencyMetrics(
            intent=intent_result.intent,
            selected_model=llm_result.selected_model,
            thinking_enabled=llm_result.thinking_enabled,
            reasoning_effort=llm_result.reasoning_effort,
            prompt_tokens_estimate=llm_result.prompt_tokens_estimate,
            llm_latency_ms=llm_result.llm_latency_ms,
            memory_latency_ms=memory_latency_ms,
            total_latency_ms=total_latency_ms,
            reply_segments_count=len(reply_segments.segments),
            segmenter_mode=reply_segments.mode,
        )
        set_last_chat_metrics(metrics)
        logger.info(
            "chat latency intent=%s selected_model=%s thinking_enabled=%s reasoning_effort=%s "
            "prompt_tokens_estimate=%s llm_latency_ms=%s memory_latency_ms=%s total_latency_ms=%s",
            metrics.intent,
            metrics.selected_model,
            metrics.thinking_enabled,
            metrics.reasoning_effort,
            metrics.prompt_tokens_estimate,
            metrics.llm_latency_ms,
            metrics.memory_latency_ms,
            metrics.total_latency_ms,
        )
        return ChatResponse(
            reply=reply,
            reply_segments=reply_segments.segments,
            segmenter_mode=reply_segments.mode,
            persona_id=self.persona_id,
            game_status=game_status.status,
            sources=sorted({snippet.source for snippet in snippets}),
            timestamp=now,
        )

    def _safe_memory_update(self, user_message: str, reply: str, intent: str, timestamp: datetime) -> None:
        start = time.perf_counter()
        try:
            self.memory.extract_and_update(user_message, reply, intent, timestamp)
        except Exception:
            logger.exception("memory update error")
        else:
            logger.info("memory update completed memory_latency_ms=%s", int((time.perf_counter() - start) * 1000))

    def _finalize_reply(self, raw_reply: str, intent: str, session_id: str, user_message: str) -> str:
        reply = apply_rei_style(validate_or_repair(raw_reply, intent), seed=f"{session_id}:{user_message}")
        return normalize_terminology(reply)
