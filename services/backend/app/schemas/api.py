from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SupportStatus = Literal["supported", "detected_only", "planned", "unsupported"]


class GameStatus(BaseModel):
    game_id: str | None
    game_name: str | None
    process_name: str | None
    status: Literal["running", "idle", "unknown"]
    confidence: float
    tags: list[str] = Field(default_factory=list)
    detected_game_id: str | None = None
    display_name: str | None = None
    match_confidence: float = 0.0
    match_source: Literal["process", "window_title", "manual", "none"] = "none"
    knowledge_game_id: str | None = None
    detected_at: datetime | None = None


class GameDetectionResponse(BaseModel):
    status: Literal["running", "idle", "unknown"]
    detected_game_id: str | None = None
    display_name: str | None = None
    process_name: str | None = None
    match_confidence: float = 0.0
    match_source: Literal["process", "window_title", "manual", "none"] = "none"
    knowledge_game_id: str | None = None
    detected_at: datetime


class ManualGameOverride(BaseModel):
    enabled: bool = False
    game_id: str | None = None
    display_name: str | None = None
    set_at: datetime | None = None
    source: Literal["user"] = "user"


class GameCatalogOption(BaseModel):
    game_id: str
    display_name: str
    enabled: bool = True
    knowledge_available: bool = True
    support_status: SupportStatus = "supported"
    knowledge_game_id: str | None = None
    manifest_path: str | None = None
    knowledge_path: str | None = None


class GameContextResponse(BaseModel):
    active_game_id: str | None = None
    active_game_display_name: str | None = None
    active_source: Literal["manual", "user_switch", "detector", "session", "user_message", "none"] = "none"
    manual_override: ManualGameOverride = Field(default_factory=ManualGameOverride)
    detected_game: GameDetectionResponse
    session_game: str | None = None
    previous_game: str | None = None
    game_switched: bool = False
    user_message_game_id: str | None = None
    user_message_game_display_name: str | None = None
    support_status: SupportStatus | None = None
    knowledge_available: bool = False
    fallback_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    available_games: list[GameCatalogOption] = Field(default_factory=list)


class ManualGameContextRequest(BaseModel):
    game_id: str | None = None


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
    assistant_message_type: Literal["reply", "proactive"] = "reply"
    trigger_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    proactive_companion: Literal["on", "off"] = "off"
    proactive_sensitivity: Literal["low", "normal", "high"] = "low"
    auto_game_detection: Literal["on", "off"] = "on"
    voice_output: Literal["on", "off"] = "off"
    voice_rate: float = Field(default=1.0, ge=0.7, le=1.3)
    voice_volume: float = Field(default=1.0, ge=0.0, le=1.0)
    onboarding_completed: bool = False
    onboarding_last_seen_at: str | None = None


class AppSettingsUpdate(BaseModel):
    persona_mode: Literal["minimal", "guarded"] | None = None
    debug_panel: Literal["show", "hide"] | None = None
    memory_enabled: bool | None = None
    pending_memory_mode: Literal["manual"] | None = None
    response_length: Literal["short", "normal"] | None = None
    model_preference: Literal["fast", "pro", "auto"] | None = None
    proactive_companion: Literal["on", "off"] | None = None
    proactive_sensitivity: Literal["low", "normal", "high"] | None = None
    auto_game_detection: Literal["on", "off"] | None = None
    voice_output: Literal["on", "off"] | None = None
    voice_rate: float | None = Field(default=None, ge=0.7, le=1.3)
    voice_volume: float | None = Field(default=None, ge=0.0, le=1.0)
    onboarding_completed: bool | None = None
    onboarding_last_seen_at: str | None = None


class SetupStatusResponse(BaseModel):
    backend_ready: bool = True
    provider_configured: bool
    provider: str = "deepseek"
    api_key_loaded: bool
    base_url: str
    model_preference: Literal["fast", "pro", "auto"]
    persona_mode: Literal["minimal", "guarded"]
    memory_ready: bool
    knowledge_ready: bool
    needs_setup: bool
    missing_items: list[str] = Field(default_factory=list)
    fast_model: str
    pro_model: str


class LocalDataStatusResponse(BaseModel):
    data_dir: str
    memory_dir: str
    session_dir: str
    settings_dir: str
    logs_dir: str
    knowledge_dir: str | None = None
    knowledge_source: Literal["bundled", "repo", "missing"]
    data_dir_exists: bool
    memory_files_count: int = 0
    session_files_count: int = 0
    pending_memory_count: int = 0
    using_bundled_knowledge: bool = False
    writable: bool = False


LocalAsrStatus = Literal[
    "local_asr_not_configured",
    "local_asr_binary_missing",
    "local_asr_binary_not_executable",
    "local_asr_model_missing",
    "local_asr_ready",
]


class LocalAsrStatusResponse(BaseModel):
    status: LocalAsrStatus
    available: bool = False
    binary_configured: bool = False
    binary_present: bool = False
    binary_executable: bool = False
    model_configured: bool = False
    model_present: bool = False
    display_message: str
    safe_binary_name: str | None = None
    safe_model_name: str | None = None


LocalAsrProbeStatus = Literal[
    "local_asr_probe_not_ready",
    "local_asr_probe_succeeded",
    "local_asr_probe_failed",
    "local_asr_probe_timed_out",
    "local_asr_probe_error",
]


class LocalAsrProbeResponse(BaseModel):
    status: LocalAsrProbeStatus
    available: bool = False
    display_message: str
    binary_name: str | None = None
    model_name: str | None = None
    duration_ms: int = 0


AudioProbeStatus = Literal[
    "audio_probe_not_supported",
    "audio_probe_permission_denied",
    "audio_probe_recording_failed",
    "audio_probe_upload_failed",
    "audio_probe_succeeded",
    "audio_probe_file_too_large",
    "audio_probe_invalid_audio",
    "audio_probe_cleanup_failed",
    "audio_probe_error",
]


class AudioProbeResponse(BaseModel):
    status: AudioProbeStatus
    available: bool = False
    display_message: str
    duration_ms: int = 0
    size_bytes: int = 0
    mime_type: str | None = None
    temporary_file_cleaned: bool = False


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
    knowledge_matched: bool = False
    knowledge_game_id: str | None = None
    knowledge_game_display_name: str | None = None
    knowledge_match_source: str | None = None
    knowledge_path: str | None = None
    manifest_path: str | None = None
    manifest_status: str = "unknown"
    knowledge_pack_version: str = "unknown"
    knowledge_pack_language: str = "unknown"
    knowledge_pack_status: str = "unknown"
    coverage: list[str] = Field(default_factory=list)
    last_updated: str = "unknown"
    knowledge_supported_games_count: int = 0
    knowledge_fallback_reason: str | None = None
    knowledge_confidence: float = 0.0
    active_game_id: str | None = None
    active_game_display_name: str | None = None
    active_source: str | None = None
    support_status: SupportStatus | None = None
    knowledge_available: bool = False
    matched_topics: list[str] = Field(default_factory=list)
    snippets_count: int = 0
    snippet_titles: list[str] = Field(default_factory=list)
    snippet_previews: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    result_scores: list[float] = Field(default_factory=list)
    knowledge_used_in_prompt: bool = False
    knowledge_retrieval_status: Literal["used", "not_found", "below_threshold", "no_pack", "not_game_related"] = "not_found"
    knowledge_not_used_reason: str | None = None
    knowledge_retrieval_min_score: float = 8.0


class PromptPreviewResponse(BaseModel):
    persona_mode: str
    current_user_message: str | None = None
    prompt_order: list[str]
    model_route_summary: dict[str, Any] = Field(default_factory=dict)
    game_context_summary: dict[str, Any] = Field(default_factory=dict)
    session_focus_summary: dict[str, Any] = Field(default_factory=dict)
    game_state_summary: dict[str, Any] = Field(default_factory=dict)
    knowledge_summary: dict[str, Any] = Field(default_factory=dict)
    memory_summary: dict[str, Any] = Field(default_factory=dict)
    final_context_summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


ProactiveTriggerType = Literal["idle_silence", "repeated_death", "late_night", "frustration_loop", "none"]


class ProactiveStatusResponse(BaseModel):
    enabled: bool
    sensitivity: Literal["low", "normal", "high"]
    enabled_at: str | None = None
    last_user_activity_at: str | None = None
    idle_for_seconds: int = 0
    idle_threshold_seconds: int = 0
    initial_grace_remaining_seconds: int = 0
    requires_user_activity_after_proactive: bool = False
    last_triggered_at: str | None = None
    last_triggered_type: ProactiveTriggerType = "none"
    next_possible_trigger_at: str | None = None
    block_reason: str = "disabled"
    active_candidate_triggers: list[str] = Field(default_factory=list)
    cooldown_remaining_seconds: int = 0
    last_trigger_reason: str | None = None


class ProactiveCheckRequest(BaseModel):
    session_id: str = Field(default="default", min_length=1, max_length=80)
    connected: bool = True
    is_user_typing: bool = False


class ProactiveCheckResponse(BaseModel):
    should_send: bool
    trigger_type: ProactiveTriggerType = "none"
    message: str = ""
    reason: str = ""
    cooldown_remaining_seconds: int = 0
    idle_for_seconds: int = 0
    idle_threshold_seconds: int = 0
    initial_grace_remaining_seconds: int = 0
    next_possible_trigger_at: str | None = None
    enabled_at: str | None = None
    last_user_activity_at: str | None = None
    requires_user_activity_after_proactive: bool = False
    block_reason: str = "disabled"
    active_candidate_triggers: list[str] = Field(default_factory=list)


class ProactiveSettingsRequest(BaseModel):
    enabled: bool | None = None
    sensitivity: Literal["low", "normal", "high"] | None = None


class ProactiveResetResponse(ProactiveStatusResponse):
    status: Literal["reset"]


class VoiceTranscribeResponse(BaseModel):
    text: str
    provider: str


class VoiceSpeakRequest(BaseModel):
    text: str = Field(min_length=1)


class VoiceSpeakResponse(BaseModel):
    audio_url: str | None
    provider: str
    message: str
