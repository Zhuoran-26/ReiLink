from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class GameStatus(BaseModel):
    game_id: str | None
    game_name: str | None
    process_name: str | None
    status: Literal["running", "idle"]
    confidence: float
    tags: list[str] = Field(default_factory=list)


class PersonaPromptRequest(BaseModel):
    persona_id: str = "rei_like"
    game_context: dict[str, Any] = Field(default_factory=dict)


class PersonaPromptResponse(BaseModel):
    system_prompt: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="default", min_length=1, max_length=80)
    mode: Literal["chat"] = "chat"


class ChatResponse(BaseModel):
    reply: str
    reply_segments: list[str] = Field(default_factory=list)
    segmenter_mode: str = "compact"
    persona_id: str
    game_status: str
    sources: list[str]
    timestamp: datetime
    request_started_at: datetime | None = None
    response_latency_ms: int = 0
    provider_latency_ms: int = 0
    model_used: str | None = None
    route_reason: str | None = None


class MemoryEntry(BaseModel):
    timestamp: str
    session_id: str
    game_id: str | None
    persona_id: str
    user_message: str
    assistant_reply: str
    assistant_reply_segments: list[str] = Field(default_factory=list)


class UserProfileMemory(BaseModel):
    user_name: str | None = None
    favorite_game: str | None = None
    preferred_tone: str | None = None
    likes_teasing: bool | None = None
    skill_level: str | None = None
    current_boss: str | None = None
    repeated_struggles: list[str] = Field(default_factory=list)
    emotional_notes: list[str] = Field(default_factory=list)
    last_seen_at: str | None = None
    memory_updated_at: dict[str, str] = Field(default_factory=dict)


class EpisodeMemory(BaseModel):
    timestamp: str
    intent: str
    boss: str | None = None
    struggle: str | None = None
    preferred_tone: str | None = None
    skill_level: str | None = None
    emotional_state: str | None = None
    topic: str | None = None
    attitude_to_rei: str | None = None
    user_name: str | None = None
    user_message_sample: str | None = None
    assistant_reply_sample: str
    summary: str | None = None


class MemoryResetResponse(BaseModel):
    status: Literal["reset"]


class PendingMemoryItem(BaseModel):
    id: str
    type: Literal["game_progress", "user_preference", "emotional_pattern", "relationship_preference", "playstyle"]
    text: str
    source: Literal["game_session", "conversation", "explicit_user_statement"]
    confidence: float
    status: Literal["pending", "accepted", "ignored"]
    created_at: str
    updated_at: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class PendingMemoryClearResponse(BaseModel):
    status: Literal["cleared"]


class AppSettings(BaseModel):
    persona_mode: Literal["minimal", "guarded"] = "guarded"
    debug_panel: Literal["show", "hide"] = "show"
    memory_enabled: bool = True
    pending_memory_mode: Literal["manual"] = "manual"
    response_length: Literal["short", "normal"] = "normal"
    model_preference: Literal["fast", "pro", "auto"] = "auto"


class AppSettingsUpdate(BaseModel):
    persona_mode: Literal["minimal", "guarded"] | None = None
    debug_panel: Literal["show", "hide"] | None = None
    memory_enabled: bool | None = None
    pending_memory_mode: Literal["manual"] | None = None
    response_length: Literal["short", "normal"] | None = None
    model_preference: Literal["fast", "pro", "auto"] | None = None


class MemoryProvenanceItem(BaseModel):
    source: Literal["profile", "episode", "current_session"]
    field: str
    text: str
    timestamp: str | None = None


class MemoryDebugResponse(BaseModel):
    prompt_order: list[str]
    memory_written: bool
    current_boss: str | None = None
    emotional_note: str | None = None
    recent_episode_count: int
    items: list[MemoryProvenanceItem]


class ChatDebugResponse(BaseModel):
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


class PromptPreviewResponse(BaseModel):
    persona_mode: str
    current_user_message: str | None = None
    prompt_order: list[str]
    model_route_summary: dict[str, Any] = Field(default_factory=dict)
    session_focus_summary: dict[str, Any] = Field(default_factory=dict)
    game_state_summary: dict[str, Any] = Field(default_factory=dict)
    memory_summary: dict[str, Any] = Field(default_factory=dict)
    final_context_summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class VoiceTranscribeResponse(BaseModel):
    text: str
    provider: str


class VoiceSpeakRequest(BaseModel):
    text: str = Field(min_length=1)


class VoiceSpeakResponse(BaseModel):
    audio_url: str | None
    provider: str
    message: str
