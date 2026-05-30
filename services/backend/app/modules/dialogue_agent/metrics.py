from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class ChatLatencyMetrics:
    intent: str | None = None
    selected_model: str | None = None
    model_used: str | None = None
    main_reply_model: str | None = None
    model_route_mode: str | None = None
    route_reason: str | None = None
    route_intent: str | None = None
    estimated_complexity: str | None = None
    fallback_reason: str | None = None
    thinking_enabled: bool = False
    reasoning_effort: str | None = None
    prompt_tokens_estimate: int = 0
    llm_latency_ms: int = 0
    provider_latency_ms: int = 0
    memory_latency_ms: int = 0
    total_latency_ms: int = 0
    response_latency_ms: int = 0
    request_started_at: str | None = None
    reply_segments_count: int = 0
    segmenter_mode: str | None = None
    semantic_extraction_called: bool = False
    semantic_extraction_model: str | None = None
    semantic_extraction_latency_ms: int = 0
    semantic_extraction_parse_error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


_last_chat_metrics = ChatLatencyMetrics()


def set_last_chat_metrics(metrics: ChatLatencyMetrics) -> None:
    global _last_chat_metrics
    _last_chat_metrics = metrics


def get_last_chat_metrics() -> ChatLatencyMetrics:
    return _last_chat_metrics
