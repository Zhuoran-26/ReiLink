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
  thinking_enabled: boolean;
  reasoning_effort: string | null;
  prompt_tokens_estimate: number;
  llm_latency_ms: number;
  memory_latency_ms: number;
  total_latency_ms: number;
  reply_segments_count: number;
  segmenter_mode: string | null;
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
  session_focus_summary: Record<string, unknown>;
  game_state_summary: Record<string, unknown>;
  memory_summary: Record<string, unknown>;
  final_context_summary: Record<string, unknown>;
  warnings: string[];
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
  gameStatus: () => request<GameStatus>("/api/game/status"),
  memoryProfile: () => request<UserProfileMemory>("/api/memory/profile"),
  memoryEpisodes: () => request<EpisodeMemory[]>("/api/memory/episodes"),
  memoryDebug: (sessionId = "default") => request<MemoryDebugResponse>(`/api/debug/memory?session_id=${encodeURIComponent(sessionId)}`),
  chatDebug: () => request<ChatDebugResponse>("/api/debug/chat"),
  gameSessionDebug: () => request<GameSessionDebugResponse>("/api/debug/game-session"),
  promptPreview: (sessionId = "default") => request<PromptPreviewResponse>(`/api/debug/prompt-preview?session_id=${encodeURIComponent(sessionId)}`),
  pendingMemories: () => request<PendingMemory[]>("/api/memory/pending"),
  acceptPendingMemory: (id: string) => request<PendingMemory>(`/api/memory/pending/${encodeURIComponent(id)}/accept`, { method: "POST" }),
  ignorePendingMemory: (id: string) => request<PendingMemory>(`/api/memory/pending/${encodeURIComponent(id)}/ignore`, { method: "POST" }),
  clearPendingMemories: () => request<{ status: "cleared" }>("/api/memory/pending/clear", { method: "POST" }),
  resetMemory: () => request<{ status: "reset" }>("/api/memory/reset", { method: "POST" }),
  chat: (message: string, sessionId = "default") =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_id: sessionId, mode: "chat" })
    })
};
