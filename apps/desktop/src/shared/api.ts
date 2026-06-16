export type GameStatus = {
  game_id: string | null;
  game_name: string | null;
  process_name: string | null;
  status: "running" | "idle" | "unknown";
  confidence: number;
  tags: string[];
  detected_game_id?: string | null;
  display_name?: string | null;
  match_confidence?: number;
  match_source?: "process" | "window_title" | "manual" | "none";
  knowledge_game_id?: string | null;
  detected_at?: string | null;
};

export type GameDetectionResponse = {
  status: "running" | "idle" | "unknown";
  detected_game_id: string | null;
  display_name: string | null;
  process_name: string | null;
  match_confidence: number;
  match_source: "process" | "window_title" | "manual" | "none";
  knowledge_game_id: string | null;
  detected_at: string;
};

export type ManualGameOverride = {
  enabled: boolean;
  game_id: string | null;
  display_name: string | null;
  set_at: string | null;
  source: "user";
};

export type GameCatalogOption = {
  game_id: string;
  display_name: string;
  enabled: boolean;
  knowledge_available: boolean;
  support_status: "supported" | "detected_only" | "planned" | "unsupported";
  knowledge_game_id: string | null;
  manifest_path: string | null;
  knowledge_path: string | null;
};

export type GameContextResponse = {
  active_game_id: string | null;
  active_game_display_name: string | null;
  active_source: "manual" | "user_switch" | "detector" | "session" | "user_message" | "none";
  manual_override: ManualGameOverride;
  detected_game: GameDetectionResponse;
  session_game: string | null;
  previous_game: string | null;
  game_switched: boolean;
  user_message_game_id: string | null;
  user_message_game_display_name: string | null;
  support_status: "supported" | "detected_only" | "planned" | "unsupported" | null;
  knowledge_available: boolean;
  fallback_reason: string | null;
  warnings: string[];
  available_games: GameCatalogOption[];
};

export type ChatResponse = {
  reply: string;
  reply_segments: string[];
  segmenter_mode: string;
  persona_id: string;
  game_status: string;
  sources: string[];
  timestamp: string;
  request_started_at?: string | null;
  response_latency_ms?: number;
  provider_latency_ms?: number;
  model_used?: string | null;
  route_reason?: string | null;
};

export type SetupStatus = {
  backend_ready: boolean;
  provider_configured: boolean;
  provider: "deepseek" | string;
  api_key_loaded: boolean;
  base_url: string;
  model_preference: "fast" | "pro" | "auto";
  persona_mode: "minimal" | "guarded";
  memory_ready: boolean;
  knowledge_ready: boolean;
  needs_setup: boolean;
  missing_items: string[];
  fast_model: string;
  pro_model: string;
};

export type LocalDataStatus = {
  data_dir: string;
  memory_dir: string;
  session_dir: string;
  settings_dir: string;
  logs_dir: string;
  knowledge_dir: string | null;
  knowledge_source: "bundled" | "repo" | "missing";
  data_dir_exists: boolean;
  memory_files_count: number;
  session_files_count: number;
  pending_memory_count: number;
  using_bundled_knowledge: boolean;
  writable: boolean;
};

export type LocalAsrStatusValue =
  | "local_asr_not_configured"
  | "local_asr_binary_missing"
  | "local_asr_binary_not_executable"
  | "local_asr_model_missing"
  | "local_asr_ready";

export type LocalAsrSettingsSource = "user_settings" | "env" | "none";

export type LocalAsrSettings = {
  configured: boolean;
  binary_configured: boolean;
  model_configured: boolean;
  converter_configured: boolean;
  safe_binary_name: string | null;
  safe_model_name: string | null;
  safe_converter_name: string | null;
  source: LocalAsrSettingsSource;
};

export type LocalAsrSettingsUpdate = {
  local_asr_binary_path?: string | null;
  local_asr_model_path?: string | null;
  audio_converter_binary_path?: string | null;
};

export type LocalAsrStatus = {
  status: LocalAsrStatusValue;
  available: boolean;
  binary_configured: boolean;
  binary_present: boolean;
  binary_executable: boolean;
  model_configured: boolean;
  model_present: boolean;
  display_message: string;
  safe_binary_name: string | null;
  safe_model_name: string | null;
  converter_configured: boolean;
  safe_converter_name: string | null;
  source: LocalAsrSettingsSource;
};

export type LocalAsrProbeStatusValue =
  | "local_asr_probe_not_ready"
  | "local_asr_probe_succeeded"
  | "local_asr_probe_failed"
  | "local_asr_probe_timed_out"
  | "local_asr_probe_error";

export type LocalAsrProbeResponse = {
  status: LocalAsrProbeStatusValue;
  available: boolean;
  display_message: string;
  binary_name: string | null;
  model_name: string | null;
  duration_ms: number;
};

export type LocalAsrTranscriptionStatusValue =
  | "local_asr_transcription_not_ready"
  | "local_asr_transcription_started"
  | "local_asr_transcription_succeeded"
  | "local_asr_transcription_failed"
  | "local_asr_transcription_timed_out"
  | "local_asr_transcription_no_text"
  | "local_asr_transcription_cleanup_failed"
  | "local_asr_transcription_error";

export type AudioConversionStatusValue =
  | "audio_conversion_not_needed"
  | "audio_conversion_needed"
  | "audio_conversion_not_configured"
  | "audio_conversion_succeeded"
  | "audio_conversion_failed"
  | "audio_conversion_timed_out"
  | "audio_conversion_invalid_input"
  | "audio_conversion_cleanup_failed";

export type LocalAsrTranscriptionResponse = {
  status: LocalAsrTranscriptionStatusValue;
  available: boolean;
  display_message: string;
  transcript: string;
  transcript_char_count: number;
  language: string;
  transcript_normalized_to_simplified: boolean;
  duration_ms: number;
  size_bytes: number;
  mime_type: string | null;
  audio_format: string | null;
  conversion_status: AudioConversionStatusValue;
  conversion_required: boolean;
  converted_mime_type: string | null;
  converter_configured: boolean;
  safe_converter_name: string | null;
  temporary_file_cleaned: boolean;
  temporary_input_cleaned: boolean;
  temporary_converted_cleaned: boolean;
  binary_name: string | null;
  model_name: string | null;
};

export type AudioProbeStatusValue =
  | "audio_probe_not_supported"
  | "audio_probe_permission_denied"
  | "audio_probe_recording_failed"
  | "audio_probe_upload_failed"
  | "audio_probe_succeeded"
  | "audio_probe_file_too_large"
  | "audio_probe_invalid_audio"
  | "audio_probe_cleanup_failed"
  | "audio_probe_error";

export type AudioProbeResponse = {
  status: AudioProbeStatusValue;
  available: boolean;
  display_message: string;
  duration_ms: number;
  size_bytes: number;
  mime_type: string | null;
  temporary_file_cleaned: boolean;
};

export type ProactiveTriggerType = "idle_silence" | "repeated_death" | "late_night" | "frustration_loop" | "none";

export type ProactiveStatusResponse = {
  enabled: boolean;
  sensitivity: "low" | "normal" | "high";
  enabled_at: string | null;
  last_user_activity_at: string | null;
  idle_for_seconds: number;
  idle_threshold_seconds: number;
  initial_grace_remaining_seconds: number;
  requires_user_activity_after_proactive: boolean;
  last_triggered_at: string | null;
  last_triggered_type: ProactiveTriggerType;
  next_possible_trigger_at: string | null;
  block_reason: string;
  active_candidate_triggers: string[];
  cooldown_remaining_seconds: number;
  last_trigger_reason: string | null;
};

export type ProactiveResetResponse = ProactiveStatusResponse & {
  status: "reset";
};

export type ProactiveCheckResponse = {
  should_send: boolean;
  trigger_type: ProactiveTriggerType;
  message: string;
  reason: string;
  cooldown_remaining_seconds: number;
  idle_for_seconds: number;
  idle_threshold_seconds: number;
  initial_grace_remaining_seconds: number;
  next_possible_trigger_at: string | null;
  enabled_at: string | null;
  last_user_activity_at: string | null;
  requires_user_activity_after_proactive: boolean;
  block_reason: string;
  active_candidate_triggers: string[];
};

export type UserProfileMemory = {
  user_name: string | null;
  favorite_game: string | null;
  preferred_tone: string | null;
  likes_teasing: boolean | null;
  skill_level: string | null;
  current_boss: string | null;
  repeated_struggles: string[];
  emotional_notes: string[];
  last_seen_at: string | null;
  memory_updated_at: Record<string, string>;
};

export type EpisodeMemory = {
  timestamp: string;
  intent: string;
  boss: string | null;
  struggle: string | null;
  preferred_tone: string | null;
  skill_level: string | null;
  emotional_state: string | null;
  topic: string | null;
  attitude_to_rei: string | null;
  user_name: string | null;
  user_message_sample: string | null;
  assistant_reply_sample: string;
  summary: string | null;
};

export type MemoryProvenanceItem = {
  source: "profile" | "episode" | "current_session";
  field: string;
  text: string;
  timestamp?: string | null;
};

export type MemoryDebugResponse = {
  prompt_order: string[];
  memory_written: boolean;
  current_boss: string | null;
  emotional_note: string | null;
  recent_episode_count: number;
  items: MemoryProvenanceItem[];
};

export type ChatDebugResponse = {
  intent: string | null;
  selected_model: string | null;
  model_used: string | null;
  main_reply_model: string | null;
  model_route_mode: "auto" | "fast" | "pro" | "mock" | "single" | null;
  route_reason: string | null;
  route_intent: string | null;
  estimated_complexity: "low" | "medium" | "high" | string | null;
  fallback_reason: string | null;
  thinking_enabled: boolean;
  reasoning_effort: string | null;
  prompt_tokens_estimate: number;
  llm_latency_ms: number;
  provider_latency_ms: number;
  memory_latency_ms: number;
  total_latency_ms: number;
  response_latency_ms: number;
  request_started_at: string | null;
  reply_segments_count: number;
  segmenter_mode: string | null;
  semantic_extraction_called: boolean;
  semantic_extraction_model: string | null;
  semantic_extraction_latency_ms: number;
  semantic_extraction_parse_error: string | null;
  knowledge_matched: boolean;
  knowledge_game_id: string | null;
  knowledge_game_display_name: string | null;
  knowledge_match_source: string | null;
  knowledge_path: string | null;
  manifest_path: string | null;
  manifest_status: string;
  knowledge_pack_version: string;
  knowledge_pack_language: string;
  knowledge_pack_status: string;
  coverage: string[];
  last_updated: string;
  knowledge_supported_games_count: number;
  knowledge_fallback_reason: string | null;
  knowledge_confidence: number;
  active_game_id: string | null;
  active_game_display_name: string | null;
  active_source: string | null;
  support_status: "supported" | "detected_only" | "planned" | "unsupported" | null;
  knowledge_available: boolean;
  matched_topics: string[];
  snippets_count: number;
  snippet_titles: string[];
  snippet_previews: string[];
  matched_terms: string[];
  result_scores: number[];
  knowledge_used_in_prompt: boolean;
  knowledge_retrieval_status: "used" | "not_found" | "below_threshold" | "no_pack" | "not_game_related";
  knowledge_not_used_reason: string | null;
  knowledge_retrieval_min_score: number;
};

export type GameSessionDebugResponse = {
  current_game: string | null;
  current_boss: {
    name: string;
    updated_at: string;
    confidence: number;
    source: string;
    mention_count: number;
    age_hours: number | null;
    is_fresh: boolean;
    freshness: string;
  } | null;
  last_boss: string | null;
  last_attempted_boss: string | null;
  last_cleared_boss: string | null;
  current_activity: string | null;
  recent_game_topics: string[];
  boss_history: Array<{
    name: string;
    status: string;
    updated_at: string;
    confidence: number;
    source: string;
    mention_count: number;
    last_activity: string | null;
    age_hours: number | null;
    freshness: string;
  }>;
  frustration_count: number;
  death_count: number;
  last_user_intent: string | null;
  last_game_intent: string | null;
  last_updated_at: string | null;
};

export type PromptPreviewResponse = {
  persona_mode: string;
  current_user_message: string | null;
  prompt_order: string[];
  model_route_summary: Record<string, unknown>;
  game_context_summary: Record<string, unknown>;
  session_focus_summary: Record<string, unknown>;
  game_state_summary: Record<string, unknown>;
  persona_pack_summary: Record<string, unknown>;
  knowledge_summary: Record<string, unknown>;
  memory_summary: Record<string, unknown>;
  final_context_summary: Record<string, unknown>;
  warnings: string[];
};

export type SemanticExtractionDebugResponse = {
  latest_user_message: string | null;
  rule_result: Record<string, unknown> | null;
  rule_confidence: number;
  raw_rule_confidence?: number;
  ambiguity_detected?: boolean;
  fallback_reason?: string | null;
  source?: "rule" | "llm_fallback" | "mixed" | "none";
  confidence?: "high" | "medium" | "low";
  applied_updates?: string[];
  extraction_trace?: {
    source: "rule" | "llm_fallback" | "mixed" | "none";
    confidence: "high" | "medium" | "low";
    fallback_reason: string | null;
    skip_reason?: string | null;
    parse_error?: string | null;
    applied_updates: string[];
    llm_shadow_status?: "skipped" | "succeeded" | "failed";
    llm_shadow_confidence?: "high" | "medium" | "low";
    llm_shadow_summary?: string | null;
    llm_shadow_diff?: string | null;
  };
  llm_called: boolean;
  semantic_extraction_model: string | null;
  semantic_extraction_latency_ms: number;
  provider_latency_ms: number;
  llm_result: Record<string, unknown> | null;
  llm_shadow?: Record<string, unknown> | null;
  llm_shadow_status?: "skipped" | "succeeded" | "failed";
  llm_shadow_confidence?: "high" | "medium" | "low";
  llm_shadow_summary?: string | null;
  llm_shadow_diff?: string | null;
  final_decision: Record<string, unknown> | null;
  skip_reason: string | null;
  latency_ms: number;
  parse_error: string | null;
};

export type SemanticShadowEvent = {
  id: number;
  trace_id: string;
  timestamp: string;
  phase: "scheduled" | "final";
  status:
    | "shadow_deferred"
    | "shadow_succeeded"
    | "shadow_timeout"
    | "shadow_invalid_json"
    | "shadow_auth_failed"
    | "shadow_provider_unavailable"
    | "shadow_provider_error"
    | "shadow_cancelled"
    | "shadow_expired";
  source?: "rule" | "llm_fallback" | "mixed" | "none";
  confidence?: "high" | "medium" | "low";
  fallback_reason?: string | null;
  skip_reason?: string | null;
  parse_error?: string | null;
  applied_updates?: string[];
  llm_shadow_status?: "skipped" | "succeeded" | "failed";
  llm_shadow_confidence?: "high" | "medium" | "low";
  llm_shadow_summary?: string | null;
  llm_shadow_diff?: string | null;
  semantic_extraction_model?: string | null;
  semantic_extraction_latency_ms?: number;
};

export type SemanticShadowEventsResponse = {
  events: SemanticShadowEvent[];
  latest_id: number;
};

export type ProviderDebugResponse = {
  provider: string;
  model: string | null;
  base_url: string | null;
  api_key_loaded: boolean;
  configured_provider: string;
  fallback_to_mock: boolean;
  env_file_loaded: boolean;
  env_file_path: string;
  persona_mode: string;
  model_route_mode: string;
  deepseek_model_fast: string;
  deepseek_model_pro: string;
  selected_model: string | null;
  main_reply_model: string | null;
  route_reason: string | null;
  route_intent: string | null;
  estimated_complexity: string | null;
  provider_latency_ms: number;
  semantic_extraction_model: string | null;
  fallback_reason: string | null;
};

export type PendingMemory = {
  id: string;
  type: "game_progress" | "user_preference" | "emotional_pattern" | "relationship_preference" | "playstyle";
  text: string;
  source: "game_session" | "conversation" | "explicit_user_statement";
  confidence: number;
  status: "pending" | "accepted" | "ignored";
  created_at: string;
  updated_at: string;
  evidence: Record<string, unknown>;
};

export type AppSettings = {
  persona_mode: "minimal" | "guarded";
  debug_panel: "show" | "hide";
  memory_enabled: boolean;
  pending_memory_mode: "manual";
  response_length: "short" | "normal";
  model_preference: "fast" | "pro" | "auto";
  proactive_companion: "on" | "off";
  proactive_sensitivity: "low" | "normal" | "high";
  auto_game_detection: "on" | "off";
  overlay_enabled: "on" | "off";
  overlay_position: "top-right" | "middle-right" | "bottom-right" | "top-left" | "middle-left" | "bottom-left";
  overlay_opacity: number;
  overlay_message_count: number;
  voice_interaction_mode: "confirm_send" | "direct_conversation";
  voice_output: "on" | "off";
  voice_rate: number;
  voice_volume: number;
  onboarding_completed: boolean;
  onboarding_last_seen_at: string | null;
};

export type AppSettingsUpdate = Partial<AppSettings>;

const API_BASE = import.meta.env.VITE_REILINK_API_BASE ?? "http://127.0.0.1:8000";

export class ApiRequestError extends Error {
  status: number;
  rawBody: string;
  path: string;

  constructor(message: string, status: number, rawBody: string, path: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.rawBody = rawBody;
    this.path = path;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init
  });
  if (!response.ok) {
    const text = await response.text();
    let message = text || `Request failed: ${response.status}`;
    try {
      const parsed = JSON.parse(text) as { detail?: unknown };
      if (typeof parsed.detail === "string") {
        message = parsed.detail;
      }
    } catch {
      // Keep the raw text as the safe diagnostic message.
    }
    throw new ApiRequestError(message, response.status, text, path);
  }
  return response.json() as Promise<T>;
}

async function requestMultipart<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    body
  });
  if (!response.ok) {
    const text = await response.text();
    let message = text || `Request failed: ${response.status}`;
    try {
      const parsed = JSON.parse(text) as { detail?: unknown };
      if (typeof parsed.detail === "string") {
        message = parsed.detail;
      }
    } catch {
      // Keep the raw text as the safe diagnostic message.
    }
    throw new ApiRequestError(message, response.status, text, path);
  }
  return response.json() as Promise<T>;
}

const audioFileName = (mimeType: string) => {
  const labels: Record<string, string> = {
    "audio/webm": "recording.webm",
    "video/webm": "recording.webm",
    "audio/ogg": "recording.ogg",
    "audio/wav": "recording.wav",
    "audio/wave": "recording.wav",
    "audio/x-wav": "recording.wav",
    "audio/mpeg": "recording.mp3",
    "audio/mp4": "recording.m4a",
    "audio/aac": "recording.aac",
    "audio/flac": "recording.flac"
  };
  return labels[mimeType] ?? "recording.audio";
};

export const api = {
  health: () => request<{ status: string }>("/api/health"),
  setupStatus: () => request<SetupStatus>("/api/setup/status"),
  settings: () => request<AppSettings>("/api/settings"),
  localDataStatus: () => request<LocalDataStatus>("/api/local-data/status"),
  localAsrStatus: () => request<LocalAsrStatus>("/api/voice-input/local-asr/status"),
  localAsrSettings: () => request<LocalAsrSettings>("/api/voice-input/local-asr/settings"),
  updateLocalAsrSettings: (settings: LocalAsrSettingsUpdate) =>
    request<LocalAsrSettings>("/api/voice-input/local-asr/settings", {
      method: "PUT",
      body: JSON.stringify(settings)
    }),
  clearLocalAsrSettings: () =>
    request<LocalAsrSettings>("/api/voice-input/local-asr/settings", {
      method: "DELETE"
    }),
  probeLocalAsr: () => request<LocalAsrProbeResponse>("/api/voice-input/local-asr/probe", { method: "POST" }),
  transcribeLocalAsr: (blob: Blob, durationMs: number, language = "zh-CN") => {
    const mimeType = blob.type || "application/octet-stream";
    const body = new FormData();
    body.append("audio", blob, audioFileName(mimeType));
    body.append("duration_ms", String(Math.max(0, Math.round(durationMs))));
    body.append("mime_type", mimeType);
    if (language.trim()) body.append("language", language.trim());
    return requestMultipart<LocalAsrTranscriptionResponse>("/api/voice-input/local-asr/transcribe", body);
  },
  probeAudio: (blob: Blob, durationMs: number) =>
    request<AudioProbeResponse>("/api/voice-input/audio/probe", {
      method: "POST",
      headers: {
        "Content-Type": blob.type || "application/octet-stream",
        "X-ReiLink-Audio-Duration-Ms": String(Math.max(0, Math.round(durationMs)))
      },
      body: blob
    }),
  updateSettings: (settings: AppSettingsUpdate) =>
    request<AppSettings>("/api/settings", {
      method: "POST",
      body: JSON.stringify(settings)
    }),
  gameStatus: () => request<GameStatus>("/api/game/status"),
  gameDetected: () => request<GameDetectionResponse>("/api/game/detected"),
  gameContext: () => request<GameContextResponse>("/api/game/context"),
  setManualGameContext: (gameId: string | null) =>
    request<GameContextResponse>("/api/game/context/manual", {
      method: "POST",
      body: JSON.stringify({ game_id: gameId })
    }),
  memoryProfile: () => request<UserProfileMemory>("/api/memory/profile"),
  memoryEpisodes: () => request<EpisodeMemory[]>("/api/memory/episodes"),
  memoryDebug: (sessionId = "default") => request<MemoryDebugResponse>(`/api/debug/memory?session_id=${encodeURIComponent(sessionId)}`),
  chatDebug: () => request<ChatDebugResponse>("/api/debug/chat"),
  providerDebug: () => request<ProviderDebugResponse>("/api/debug/provider"),
  proactiveStatus: (sessionId = "default") => request<ProactiveStatusResponse>(`/api/proactive/status?session_id=${encodeURIComponent(sessionId)}`),
  checkProactive: (sessionId = "default", isUserTyping = false, connected = true) =>
    request<ProactiveCheckResponse>("/api/proactive/check", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, is_user_typing: isUserTyping, connected })
    }),
  updateProactiveSettings: (enabled?: boolean, sensitivity?: AppSettings["proactive_sensitivity"]) =>
    request<ProactiveStatusResponse>("/api/proactive/settings", {
      method: "POST",
      body: JSON.stringify({ enabled, sensitivity })
    }),
  resetProactive: () => request<ProactiveResetResponse>("/api/proactive/reset", { method: "POST" }),
  gameSessionDebug: () => request<GameSessionDebugResponse>("/api/debug/game-session"),
  semanticExtractionDebug: () => request<SemanticExtractionDebugResponse>("/api/debug/semantic-extraction/latest"),
  semanticShadowEvents: (sinceId = 0) =>
    request<SemanticShadowEventsResponse>(`/api/debug/semantic-shadow/events?since_id=${Math.max(0, Math.floor(sinceId))}`),
  promptPreview: (sessionId = "default") => request<PromptPreviewResponse>(`/api/debug/prompt-preview?session_id=${encodeURIComponent(sessionId)}`),
  pendingMemories: () => request<PendingMemory[]>("/api/memory/pending"),
  acceptPendingMemory: (id: string) => request<PendingMemory>(`/api/memory/pending/${encodeURIComponent(id)}/accept`, { method: "POST" }),
  ignorePendingMemory: (id: string) => request<PendingMemory>(`/api/memory/pending/${encodeURIComponent(id)}/ignore`, { method: "POST" }),
  clearPendingMemories: () => request<{ status: "cleared" }>("/api/memory/pending/clear", { method: "POST" }),
  resetGameSession: () => request<{ status: string }>("/api/debug/game-session/reset", { method: "POST" }),
  resetMemory: () => request<{ status: "reset" }>("/api/memory/reset", { method: "POST" }),
  chat: (message: string, sessionId = "default") =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId, mode: "chat" })
    })
};
