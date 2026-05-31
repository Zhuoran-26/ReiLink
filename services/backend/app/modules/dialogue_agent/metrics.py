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
    knowledge_matched: bool = False
    knowledge_game_id: str | None = None
    knowledge_game_display_name: str | None = None
    knowledge_match_source: str | None = None
    knowledge_path: str | None = None
    knowledge_supported_games_count: int = 0
    knowledge_fallback_reason: str | None = None
    knowledge_confidence: float = 0.0
    active_game_id: str | None = None
    active_game_display_name: str | None = None
    active_source: str | None = None
    support_status: str | None = None
    knowledge_available: bool = False
    matched_topics: list[str] | None = None
    snippets_count: int = 0
    snippet_titles: list[str] | None = None
    knowledge_used_in_prompt: bool = False

    def as_dict(self) -> dict:
        data = asdict(self)
        data["matched_topics"] = data.get("matched_topics") or []
        data["snippet_titles"] = data.get("snippet_titles") or []
        return data


_last_chat_metrics = ChatLatencyMetrics()


def set_last_chat_metrics(metrics: ChatLatencyMetrics) -> None:
    global _last_chat_metrics
    _last_chat_metrics = metrics


def get_last_chat_metrics() -> ChatLatencyMetrics:
    return _last_chat_metrics
