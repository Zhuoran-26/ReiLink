export type GameStatus = {
  game_id: string | null;
  game_name: string | null;
  process_name: string | null;
  status: "running" | "idle";
  confidence: number;
  tags: string[];
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
  session_focus_summary: Record<string, unknown>;
  game_state_summary: Record<string, unknown>;
  memory_summary: Record<string, unknown>;
  final_context_summary: Record<string, unknown>;
  warnings: string[];
};

export type SemanticExtractionDebugResponse = {
  latest_user_message: string | null;
  rule_result: Record<string, unknown> | null;
  rule_confidence: number;
  llm_called: boolean;
  semantic_extraction_model: string | null;
  semantic_extraction_latency_ms: number;
  provider_latency_ms: number;
  llm_result: Record<string, unknown> | null;
  final_decision: Record<string, unknown> | null;
  skip_reason: string | null;
  latency_ms: number;
  parse_error: string | null;
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
};

export type AppSettingsUpdate = Partial<AppSettings>;

const API_BASE = import.meta.env.VITE_REILINK_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),
  settings: () => request<AppSettings>("/api/settings"),
  updateSettings: (settings: AppSettingsUpdate) =>
    request<AppSettings>("/api/settings", {
      method: "POST",
      body: JSON.stringify(settings)
    }),
  gameStatus: () => request<GameStatus>("/api/game/status"),
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
  gameSessionDebug: () => request<GameSessionDebugResponse>("/api/debug/game-session"),
  semanticExtractionDebug: () => request<SemanticExtractionDebugResponse>("/api/debug/semantic-extraction/latest"),
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
