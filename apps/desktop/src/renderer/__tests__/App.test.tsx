import { act } from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App, INTERIM_PLACEHOLDERS } from "../App";
import type {
  GameContextResponse,
  GameDetectionResponse,
  ProactiveCheckResponse,
  ProactiveStatusResponse
} from "../../shared/api";

const runningStatus = {
  game_id: "elden_ring",
  game_name: "Elden Ring",
  process_name: "eldenring.exe",
  status: "running",
  confidence: 1,
  tags: ["soulslike"],
  detected_game_id: "elden_ring",
  display_name: "艾尔登法环",
  match_confidence: 1,
  match_source: "process",
  knowledge_game_id: "elden_ring",
  detected_at: new Date().toISOString()
};

const gameDetection: GameDetectionResponse = {
  status: "running",
  detected_game_id: "elden_ring",
  display_name: "艾尔登法环",
  process_name: "eldenring.exe",
  match_confidence: 1,
  match_source: "process",
  knowledge_game_id: "elden_ring",
  detected_at: new Date().toISOString()
};

const idleGameDetection: GameDetectionResponse = {
  ...gameDetection,
  status: "idle",
  detected_game_id: null,
  display_name: null,
  process_name: null,
  match_confidence: 0,
  match_source: "none",
  knowledge_game_id: null
};

const gameContext: GameContextResponse = {
  active_game_id: "elden_ring",
  active_game_display_name: "艾尔登法环",
  active_source: "detector",
  manual_override: {
    enabled: false,
    game_id: null,
    display_name: null,
    set_at: null,
    source: "user"
  },
  detected_game: gameDetection,
  session_game: "Elden Ring",
  previous_game: null,
  game_switched: false,
  user_message_game_id: null,
  user_message_game_display_name: null,
  support_status: "supported",
  knowledge_available: true,
  fallback_reason: null,
  warnings: [],
  available_games: [
    {
      game_id: "elden_ring",
      display_name: "艾尔登法环",
      enabled: true,
      knowledge_available: true,
      support_status: "supported",
      knowledge_game_id: "elden_ring",
      manifest_path: "data/knowledge/games/elden_ring/manifest.json",
      knowledge_path: "data/knowledge/games/elden_ring/snippets.json"
    },
    {
      game_id: "hollow_knight",
      display_name: "空洞骑士",
      enabled: true,
      knowledge_available: true,
      support_status: "supported",
      knowledge_game_id: "hollow_knight",
      manifest_path: "data/knowledge/games/hollow_knight/manifest.json",
      knowledge_path: "data/knowledge/games/hollow_knight/snippets.json"
    },
    {
      game_id: "sekiro",
      display_name: "只狼",
      enabled: true,
      knowledge_available: false,
      support_status: "planned",
      knowledge_game_id: "sekiro",
      manifest_path: null,
      knowledge_path: null
    }
  ]
};

const idleGameContext: GameContextResponse = {
  ...gameContext,
  active_game_id: null,
  active_game_display_name: null,
  active_source: "none",
  detected_game: idleGameDetection,
  session_game: null,
  support_status: null,
  knowledge_available: false,
  fallback_reason: "no_game_detected"
};

const unsupportedGameContext: GameContextResponse = {
  ...gameContext,
  active_game_id: "sekiro",
  active_game_display_name: "只狼",
  active_source: "user_switch",
  previous_game: "艾尔登法环",
  game_switched: true,
  user_message_game_id: "sekiro",
  user_message_game_display_name: "只狼",
  support_status: "planned",
  knowledge_available: false,
  fallback_reason: "no_supported_knowledge"
};

const hollowKnightGameContext: GameContextResponse = {
  ...gameContext,
  active_game_id: "hollow_knight",
  active_game_display_name: "空洞骑士",
  active_source: "user_switch",
  previous_game: "艾尔登法环",
  game_switched: true,
  user_message_game_id: "hollow_knight",
  user_message_game_display_name: "空洞骑士",
  support_status: "supported",
  knowledge_available: true,
  fallback_reason: null
};

const unknownGameContext: GameContextResponse = {
  ...gameContext,
  active_game_id: null,
  active_game_display_name: "星之门遗迹",
  active_source: "user_switch",
  previous_game: "艾尔登法环",
  game_switched: true,
  user_message_game_id: null,
  user_message_game_display_name: "星之门遗迹",
  support_status: "unsupported",
  knowledge_available: false,
  fallback_reason: "unknown_game"
};

const manualConflictGameContext: GameContextResponse = {
  ...gameContext,
  active_game_id: "elden_ring",
  active_game_display_name: "艾尔登法环",
  active_source: "manual",
  previous_game: "艾尔登法环",
  game_switched: false,
  manual_override: {
    enabled: true,
    game_id: "elden_ring",
    display_name: "艾尔登法环",
    set_at: new Date().toISOString(),
    source: "user"
  },
  user_message_game_id: "hollow_knight",
  user_message_game_display_name: "空洞骑士",
  warnings: ["user_message_game_conflicts_with_manual_override"]
};

const memoryProfile = {
  user_name: null,
  favorite_game: "Elden Ring",
  preferred_tone: "轻微吐槽",
  likes_teasing: true,
  skill_level: null,
  current_boss: "恶兆妖鬼 Margit",
  repeated_struggles: ["恶兆妖鬼 Margit死亡循环"],
  emotional_notes: ["玩家在死亡循环里有点急"],
  last_seen_at: new Date().toISOString(),
  memory_updated_at: {}
};

const memoryDebug = {
  prompt_order: ["current_user_message", "current_session", "memory", "persona"],
  memory_written: true,
  current_boss: "恶兆妖鬼 Margit",
  emotional_note: "frustrated",
  recent_episode_count: 2,
  items: [
    { source: "profile", field: "current_boss", text: "玩家当前卡点：恶兆妖鬼 Margit" },
    { source: "episode", field: "summary", text: "玩家最近卡在恶兆妖鬼 Margit，问题像是恶兆妖鬼 Margit死亡循环" }
  ]
};

const chatDebug = {
  intent: "casual_chat",
  selected_model: "deepseek-v4-flash",
  model_used: "deepseek-v4-flash",
  main_reply_model: "deepseek-v4-flash",
  model_route_mode: "auto",
  route_reason: "casual_or_short_reply",
  route_intent: "casual_chat",
  estimated_complexity: "low",
  fallback_reason: null,
  thinking_enabled: false,
  reasoning_effort: null,
  prompt_tokens_estimate: 120,
  llm_latency_ms: 300,
  provider_latency_ms: 300,
  memory_latency_ms: 0,
  total_latency_ms: 320,
  response_latency_ms: 320,
  request_started_at: new Date().toISOString(),
  reply_segments_count: 1,
  segmenter_mode: "compact",
  semantic_extraction_called: true,
  semantic_extraction_model: "deepseek-v4-flash",
  semantic_extraction_latency_ms: 42,
  semantic_extraction_parse_error: null,
  knowledge_matched: true,
  knowledge_game_id: "elden_ring",
  knowledge_game_display_name: "艾尔登法环",
  knowledge_match_source: "current_game",
  knowledge_path: "data/knowledge/games/elden_ring/snippets.json",
  manifest_path: "data/knowledge/games/elden_ring/manifest.json",
  manifest_status: "loaded",
  knowledge_pack_version: "0.1.0",
  knowledge_pack_language: "zh-CN",
  knowledge_pack_status: "sample",
  coverage: ["boss", "mechanic", "beginner_tip"],
  last_updated: "2026-06-01",
  knowledge_supported_games_count: 2,
  knowledge_fallback_reason: null,
  knowledge_confidence: 0.83,
  active_game_id: "elden_ring",
  active_game_display_name: "艾尔登法环",
  active_source: "session",
  support_status: "supported",
  knowledge_available: true,
  matched_topics: ["margit", "boss_strategy"],
  snippets_count: 2,
  snippet_titles: ["恶兆妖鬼 Margit：延迟攻击", "恶兆妖鬼 Margit：战前准备"],
  knowledge_used_in_prompt: true
};

const unsupportedChatDebug = {
  ...chatDebug,
  knowledge_matched: false,
  knowledge_game_id: "sekiro",
  knowledge_game_display_name: "只狼",
  knowledge_match_source: "alias",
  knowledge_path: null,
  manifest_path: null,
  manifest_status: "manifest_missing",
  knowledge_pack_version: "unknown",
  knowledge_pack_language: "unknown",
  knowledge_pack_status: "unknown",
  coverage: [],
  last_updated: "unknown",
  knowledge_fallback_reason: "no_supported_knowledge",
  knowledge_confidence: 0,
  active_game_id: "sekiro",
  active_game_display_name: "只狼",
  active_source: "user_switch",
  support_status: "planned",
  knowledge_available: false,
  matched_topics: [],
  snippets_count: 0,
  snippet_titles: [],
  knowledge_used_in_prompt: false
};

const hollowKnightChatDebug = {
  ...chatDebug,
  knowledge_matched: true,
  knowledge_game_id: "hollow_knight",
  knowledge_game_display_name: "空洞骑士",
  knowledge_match_source: "user_switch",
  knowledge_path: "data/knowledge/games/hollow_knight/snippets.json",
  manifest_path: "data/knowledge/games/hollow_knight/manifest.json",
  manifest_status: "loaded",
  knowledge_pack_version: "0.1.0",
  knowledge_pack_language: "zh-CN",
  knowledge_pack_status: "sample",
  coverage: ["boss", "mechanic", "beginner_tip"],
  last_updated: "2026-06-01",
  knowledge_supported_games_count: 2,
  knowledge_fallback_reason: null,
  knowledge_confidence: 0.83,
  active_game_id: "hollow_knight",
  active_game_display_name: "空洞骑士",
  active_source: "user_switch",
  support_status: "supported",
  knowledge_available: true,
  matched_topics: ["螳螂领主", "boss_strategy"],
  snippets_count: 1,
  snippet_titles: ["螳螂领主：节奏观察"],
  knowledge_used_in_prompt: true
};

const unknownChatDebug = {
  ...unsupportedChatDebug,
  knowledge_game_id: null,
  knowledge_game_display_name: "星之门遗迹",
  knowledge_fallback_reason: "unknown_game",
  active_game_id: null,
  active_game_display_name: "星之门遗迹",
  support_status: "unsupported",
  manifest_status: "unknown"
};

const gameSessionDebug = {
  current_game: "Elden Ring",
  current_boss: {
    name: "恶兆妖鬼 Margit",
    updated_at: new Date().toISOString(),
    confidence: 0.95,
    source: "current_message",
    mention_count: 2,
    age_hours: 0.1,
    is_fresh: true,
    freshness: "fresh"
  },
  last_boss: "恶兆妖鬼 Margit",
  last_attempted_boss: "恶兆妖鬼 Margit",
  last_cleared_boss: null,
  current_activity: "boss_attempt",
  recent_game_topics: ["恶兆妖鬼 Margit"],
  boss_history: [
    {
      name: "恶兆妖鬼 Margit",
      status: "current",
      updated_at: new Date().toISOString(),
      confidence: 0.95,
      source: "current_message",
      mention_count: 2,
      last_activity: "boss_attempt",
      age_hours: 0.1,
      freshness: "fresh"
    }
  ],
  frustration_count: 1,
  death_count: 1,
  last_user_intent: "casual_chat",
  last_game_intent: "casual_chat",
  last_updated_at: new Date().toISOString()
};

const promptPreview = {
  persona_mode: "minimal",
  current_user_message: "Margit 怎么打？",
  prompt_order: ["current_user_message", "current_session_context", "session_focus", "game_state", "knowledge", "memory", "persona"],
  model_route_summary: {
    selected_model: "deepseek-v4-flash",
    model_route_mode: "auto",
    route_reason: "simple_game_reminder",
    route_intent: "elden_ring_boss_strategy",
    estimated_complexity: "medium",
    provider_latency_ms: 300,
    semantic_extraction_model: "deepseek-v4-flash",
    main_reply_model: "deepseek-v4-flash"
  },
  game_context_summary: gameContext,
  session_focus_summary: { boss: "恶兆妖鬼 Margit", source: "current_message", prompt_line: "当前短期焦点：恶兆妖鬼 Margit" },
  game_state_summary: {
    current_game: "Elden Ring",
    current_boss: gameSessionDebug.current_boss,
    current_activity: "boss_attempt",
    freshness: "fresh",
    death_count: 1,
    frustration_count: 1,
    last_attempted_boss: "恶兆妖鬼 Margit",
    last_cleared_boss: null,
    boss_history: gameSessionDebug.boss_history
  },
  knowledge_summary: {
    knowledge_matched: true,
    game_id: "elden_ring",
    active_game_id: "elden_ring",
    active_game_display_name: "艾尔登法环",
    active_source: "session",
    support_status: "supported",
    knowledge_available: true,
    matched_game_id: "elden_ring",
    matched_game_display_name: "艾尔登法环",
    match_source: "current_game",
    knowledge_path: "data/knowledge/games/elden_ring/snippets.json",
    manifest_path: "data/knowledge/games/elden_ring/manifest.json",
    manifest_status: "loaded",
    knowledge_pack_version: "0.1.0",
    knowledge_pack_language: "zh-CN",
    knowledge_pack_status: "sample",
    coverage: ["boss", "mechanic", "beginner_tip"],
    last_updated: "2026-06-01",
    supported_games_count: 2,
    matched_topics: ["margit", "boss_strategy"],
    snippets_count: 2,
    snippet_titles: ["恶兆妖鬼 Margit：延迟攻击", "恶兆妖鬼 Margit：战前准备"],
    knowledge_used_in_prompt: true,
    confidence: 0.83,
    fallback_reason: null
  },
  memory_summary: {
    injected: memoryDebug.items,
    skipped: [{ source: "profile", field: "current_boss", reason: "conflict_with_fresh_game_state", text: "玩家当前卡点：大树守卫" }]
  },
  final_context_summary: { raw_prompt_omitted: true, memory_injected_count: 2 },
  warnings: ["memory boss conflicts with fresh game state"]
};

const unsupportedPromptPreview = {
  ...promptPreview,
  game_context_summary: unsupportedGameContext,
  knowledge_summary: {
    ...promptPreview.knowledge_summary,
    knowledge_matched: false,
    game_id: "sekiro",
    active_game_id: "sekiro",
    active_game_display_name: "只狼",
    active_source: "user_switch",
    support_status: "planned",
    knowledge_available: false,
    matched_game_id: "sekiro",
    matched_game_display_name: "只狼",
    match_source: "alias",
    knowledge_path: null,
    manifest_path: null,
    manifest_status: "manifest_missing",
    knowledge_pack_version: "unknown",
    knowledge_pack_language: "unknown",
    knowledge_pack_status: "unknown",
    coverage: [],
    last_updated: "unknown",
    matched_topics: [],
    snippets_count: 0,
    snippet_titles: [],
    knowledge_used_in_prompt: false,
    confidence: 0,
    fallback_reason: "no_supported_knowledge"
  }
};

const hollowKnightPromptPreview = {
  ...promptPreview,
  game_context_summary: hollowKnightGameContext,
  knowledge_summary: {
    ...promptPreview.knowledge_summary,
    knowledge_matched: true,
    game_id: "hollow_knight",
    active_game_id: "hollow_knight",
    active_game_display_name: "空洞骑士",
    active_source: "user_switch",
    support_status: "supported",
    knowledge_available: true,
    matched_game_id: "hollow_knight",
    matched_game_display_name: "空洞骑士",
    match_source: "user_switch",
    knowledge_path: "data/knowledge/games/hollow_knight/snippets.json",
    manifest_path: "data/knowledge/games/hollow_knight/manifest.json",
    manifest_status: "loaded",
    knowledge_pack_version: "0.1.0",
    knowledge_pack_language: "zh-CN",
    knowledge_pack_status: "sample",
    coverage: ["boss", "mechanic", "beginner_tip"],
    last_updated: "2026-06-01",
    supported_games_count: 2,
    matched_topics: ["螳螂领主", "boss_strategy"],
    snippets_count: 1,
    snippet_titles: ["螳螂领主：节奏观察"],
    knowledge_used_in_prompt: true,
    confidence: 0.83,
    fallback_reason: null
  }
};

const unknownPromptPreview = {
  ...unsupportedPromptPreview,
  game_context_summary: unknownGameContext,
  knowledge_summary: {
    ...unsupportedPromptPreview.knowledge_summary,
    game_id: null,
    active_game_id: null,
    active_game_display_name: "星之门遗迹",
    matched_game_id: null,
    matched_game_display_name: "星之门遗迹",
    support_status: "unsupported",
    manifest_path: null,
    manifest_status: "unknown",
    knowledge_pack_version: "unknown",
    knowledge_pack_language: "unknown",
    knowledge_pack_status: "unknown",
    coverage: [],
    last_updated: "unknown",
    fallback_reason: "unknown_game"
  }
};

const semanticExtractionDebug = {
  latest_user_message: "我喜欢简短的游戏攻略",
  rule_result: { game_event: { type: "none" }, memory_candidate: { type: "guide_preference" } },
  rule_confidence: 0.65,
  llm_called: true,
  semantic_extraction_model: "deepseek-v4-flash",
  semantic_extraction_latency_ms: 42,
  provider_latency_ms: 42,
  llm_result: {
    game_event: { type: "none" },
    memory_candidate: { type: "guide_preference" }
  },
  final_decision: {
    game_event: { type: "none" },
    memory_candidate: { type: "guide_preference" }
  },
  skip_reason: null,
  latency_ms: 42,
  parse_error: null
};

const providerDebug = {
  provider: "deepseek",
  model: "deepseek-v4-pro",
  base_url: "https://api.deepseek.com",
  api_key_loaded: true,
  configured_provider: "deepseek",
  fallback_to_mock: false,
  env_file_loaded: true,
  env_file_path: "/Users/aragoto/Desktop/ReiLink/services/backend/.env",
  persona_mode: "minimal",
  model_route_mode: "auto",
  deepseek_model_fast: "deepseek-v4-flash",
  deepseek_model_pro: "deepseek-v4-pro",
  selected_model: "deepseek-v4-flash",
  main_reply_model: "deepseek-v4-flash",
  route_reason: "casual_or_short_reply",
  route_intent: "casual_chat",
  estimated_complexity: "low",
  provider_latency_ms: 300,
  semantic_extraction_model: "deepseek-v4-flash",
  fallback_reason: null
};

const proactiveStatus: ProactiveStatusResponse = {
  enabled: false,
  sensitivity: "low",
  enabled_at: null,
  last_user_activity_at: null,
  idle_for_seconds: 0,
  idle_threshold_seconds: 600,
  initial_grace_remaining_seconds: 0,
  requires_user_activity_after_proactive: false,
  last_triggered_at: null,
  last_triggered_type: "none",
  next_possible_trigger_at: null,
  block_reason: "disabled",
  active_candidate_triggers: [] as string[],
  cooldown_remaining_seconds: 0,
  last_trigger_reason: null
};

let proactiveStatusStore: ProactiveStatusResponse = { ...proactiveStatus };
let proactiveCheckStore: ProactiveCheckResponse = {
  should_send: false,
  trigger_type: "none",
  message: "",
  reason: "disabled",
  cooldown_remaining_seconds: 0,
  idle_for_seconds: 0,
  idle_threshold_seconds: 600,
  initial_grace_remaining_seconds: 0,
  next_possible_trigger_at: null,
  enabled_at: null,
  last_user_activity_at: null,
  requires_user_activity_after_proactive: false,
  block_reason: "disabled",
  active_candidate_triggers: [] as string[]
};

const pendingMemories = [
  {
    id: "pending-1",
    type: "user_preference",
    text: "玩家不喜欢长篇攻略",
    source: "explicit_user_statement",
    confidence: 0.95,
    status: "pending",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    evidence: {
      user_message: "我不喜欢长篇攻略",
      game_state_summary: "current_boss=none"
    }
  }
];

const appSettings = {
  persona_mode: "minimal",
  debug_panel: "show",
  memory_enabled: true,
  pending_memory_mode: "manual",
  response_length: "normal",
  model_preference: "auto",
  proactive_companion: "off",
  proactive_sensitivity: "low",
  auto_game_detection: "on"
};

let appSettingsStore = { ...appSettings };
let gameContextStore = { ...gameContext };

const resetSettingsResponse = () => {
  appSettingsStore = { ...appSettings };
  gameContextStore = { ...gameContext };
  proactiveStatusStore = { ...proactiveStatus };
  proactiveCheckStore = {
    should_send: false,
    trigger_type: "none",
    message: "",
    reason: "disabled",
    cooldown_remaining_seconds: 0,
    idle_for_seconds: 0,
    idle_threshold_seconds: 600,
    initial_grace_remaining_seconds: 0,
    next_possible_trigger_at: null,
    enabled_at: null,
    last_user_activity_at: null,
    requires_user_activity_after_proactive: false,
    block_reason: "disabled",
    active_candidate_triggers: [] as string[]
  };
};

const gameContextResponse = (url: string, init?: RequestInit) => {
  if (url.endsWith("/api/game/context/manual") && init?.method === "POST") {
    const body = JSON.parse(String(init.body ?? "{}")) as { game_id?: string | null };
    gameContextStore = body.game_id
      ? {
          ...gameContext,
          active_source: "manual",
          manual_override: {
            enabled: true,
            game_id: body.game_id,
            display_name: "艾尔登法环",
            set_at: new Date().toISOString(),
            source: "user"
          }
        }
      : { ...gameContext, active_source: "detector", manual_override: gameContext.manual_override };
    return Response.json(gameContextStore);
  }
  if (url.endsWith("/api/game/context")) return Response.json(gameContextStore);
  return null;
};

const settingsResponse = (url: string, init?: RequestInit) => {
  if (url.endsWith("/api/settings") && init?.method === "POST") {
    appSettingsStore = { ...appSettingsStore, ...JSON.parse(String(init.body ?? "{}")) };
    return Response.json(appSettingsStore);
  }
  if (url.endsWith("/api/settings")) return Response.json(appSettingsStore);
  return null;
};

const proactiveResponse = (url: string, init?: RequestInit) => {
  if (url.includes("/api/proactive/status")) return Response.json(proactiveStatusStore);
  if (url.endsWith("/api/proactive/check") && init?.method === "POST") {
    return Response.json(proactiveCheckStore);
  }
  if (url.endsWith("/api/proactive/settings") && init?.method === "POST") {
    return Response.json(proactiveStatusStore);
  }
  return null;
};

const pendingMemoryResponse = (url: string, init?: RequestInit) => {
  if (url.endsWith("/api/memory/pending")) return Response.json(pendingMemories);
  if (url.endsWith("/api/memory/pending/clear") && init?.method === "POST") {
    return Response.json({ status: "cleared" });
  }
  if (url.includes("/api/memory/pending/pending-1/accept") && init?.method === "POST") {
    return Response.json({ ...pendingMemories[0], status: "accepted" });
  }
  if (url.includes("/api/memory/pending/pending-1/ignore") && init?.method === "POST") {
    return Response.json({ ...pendingMemories[0], status: "ignored" });
  }
  return null;
};

const debugActionResponse = (url: string, init?: RequestInit) => {
  if (url.endsWith("/api/debug/game-session/reset") && init?.method === "POST") {
    return Response.json({ status: "reset" });
  }
  if (url.endsWith("/api/memory/reset") && init?.method === "POST") {
    return Response.json({ status: "reset" });
  }
  return null;
};

const chatResponse = {
  reply: "别急着翻滚。先看动作。再试一次。",
  reply_segments: ["别急着翻滚。先看动作。再试一次。"],
  segmenter_mode: "compact",
  persona_id: "rei_like",
  game_status: "running",
  sources: ["data/elden_ring/bosses.json"],
  timestamp: new Date().toISOString()
};

describe("App", () => {
  beforeEach(() => {
    let uuid = 0;
    resetSettingsResponse();
    vi.stubGlobal("crypto", { randomUUID: () => `test-id-${uuid++}` });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return debugAction;
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return pendingResponse;
        const settings = settingsResponse(url, init);
        if (settings) return settings;
        const gameContextResponseValue = gameContextResponse(url, init);
        if (gameContextResponseValue) return gameContextResponseValue;
        const proactive = proactiveResponse(url, init);
        if (proactive) return proactive;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json(runningStatus);
        if (url.endsWith("/api/game/detected")) return Response.json(gameDetection);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(chatDebug);
        if (url.endsWith("/api/debug/provider")) return Response.json(providerDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json(gameSessionDebug);
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Response.json(semanticExtractionDebug);
        if (url.includes("/api/debug/prompt-preview")) return Response.json(promptPreview);
        if (url.endsWith("/api/chat") && init?.method === "POST") {
          return Response.json(chatResponse);
        }
        return new Response("missing", { status: 404 });
      })
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders the app", async () => {
    render(<App />);
    expect(screen.getByText("ReiLink")).toBeInTheDocument();
    await screen.findByText("已连接");
  });

  it("renders the polished companion layout sections", async () => {
    render(<App />);

    await screen.findByText("已连接");
    const navigation = screen.getByRole("navigation", { name: "应用导航" });
    expect(navigation).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "主聊天界面" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "信息侧栏" })).toBeInTheDocument();
    expect(within(navigation).getByText("聊天")).toBeInTheDocument();
    expect(within(navigation).getByText("记忆")).toBeInTheDocument();
    expect(within(navigation).getByText("游戏")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "设置" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "待确认记忆" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "游戏状态" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /调试面板/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /回复上下文预览/i })).toBeInTheDocument();
    expect(screen.getByText("语义识别")).toBeInTheDocument();
  });

  it("shows running game status", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getAllByText("Elden Ring").length).toBeGreaterThan(0));
    expect(screen.getAllByText("恶兆妖鬼 Margit").length).toBeGreaterThan(0);
    expect(screen.getAllByText("挑战中").length).toBeGreaterThan(0);
    expect(screen.getAllByText("当前游戏").length).toBeGreaterThan(0);
    expect(screen.getByText("当前 Boss")).toBeInTheDocument();
    expect(screen.getByText("死亡次数")).toBeInTheDocument();
  });

  it("renders settings panel values", async () => {
    render(<App />);

    expect(await screen.findByLabelText("人格模式")).toHaveValue("minimal");
    expect(screen.getByRole("combobox", { name: "调试面板" })).toHaveValue("show");
    expect(screen.getByLabelText("记忆")).toHaveValue("enabled");
    expect(screen.getByLabelText("待确认记忆模式")).toHaveValue("manual");
    expect(screen.getByLabelText("回复长度")).toHaveValue("normal");
    expect(screen.getByLabelText("模型偏好")).toHaveValue("auto");
    expect(screen.getByLabelText("自动游戏检测")).toHaveValue("on");
    expect(screen.getByLabelText("当前游戏")).toHaveValue("");
    expect(screen.getByRole("option", { name: "艾尔登法环（已支持）" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "空洞骑士（已支持）" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "只狼（暂未支持）" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "清除手动选择" })).toBeInTheDocument();
    expect(screen.getByLabelText("已支持游戏")).toHaveTextContent("艾尔登法环");
    expect(screen.getByLabelText("已支持游戏")).toHaveTextContent("空洞骑士");
    expect(screen.getByLabelText("主动陪伴")).toHaveValue("off");
    expect(screen.getByLabelText("主动灵敏度")).toHaveValue("low");
    expect(screen.getByText(/自动游戏检测当前为开启/)).toBeInTheDocument();
  });

  it("updates settings through the API", async () => {
    render(<App />);

    await userEvent.selectOptions(await screen.findByLabelText("人格模式"), "guarded");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ persona_mode: "guarded" }) })
      )
    );

    await userEvent.selectOptions(screen.getByLabelText("记忆"), "disabled");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ memory_enabled: false }) })
      )
    );

    await userEvent.selectOptions(screen.getByLabelText("模型偏好"), "pro");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ model_preference: "pro" }) })
      )
    );

    await userEvent.selectOptions(screen.getByLabelText("自动游戏检测"), "off");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ auto_game_detection: "off" }) })
      )
    );

    await userEvent.selectOptions(screen.getByLabelText("当前游戏"), "elden_ring");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/game/context/manual"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ game_id: "elden_ring" }) })
      )
    );

    await userEvent.click(screen.getByRole("button", { name: "清除手动选择" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/game/context/manual"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ game_id: null }) })
      )
    );

    await userEvent.selectOptions(screen.getByLabelText("主动陪伴"), "on");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ proactive_companion: "on" }) })
      )
    );
  });

  it("hides debug panel through settings", async () => {
    render(<App />);

    await screen.findByRole("button", { name: /调试面板/i });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "调试面板" }), "hide");

    await waitFor(() => expect(screen.queryByRole("button", { name: /调试面板/i })).not.toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /回复上下文预览/i })).not.toBeInTheDocument();
  });

  it("shows and expands debug panel when settings switch from hidden to visible", async () => {
    appSettingsStore = { ...appSettingsStore, debug_panel: "hide" };
    render(<App />);

    await screen.findByRole("combobox", { name: "调试面板" });
    expect(screen.queryByRole("button", { name: /调试面板/i })).not.toBeInTheDocument();

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "调试面板" }), "show");

    await waitFor(() => expect(screen.getByRole("button", { name: /调试面板/i })).toHaveAttribute("aria-expanded", "true"));
    expect(screen.getByText("语义识别")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /回复上下文预览/i })).toBeInTheDocument();
  });

  it("sends chat and renders user plus assistant messages", async () => {
    render(<App />);
    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    expect(screen.getByText("Margit 怎么打？")).toBeInTheDocument();
    await screen.findByText("别急着翻滚。先看动作。再试一次。");
    expect(screen.getAllByText(/今天 \d{2}:\d{2}/).length).toBeGreaterThan(0);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/chat"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("renders proactive message as a normal Rei message with metadata", async () => {
    vi.useFakeTimers();
    appSettingsStore = { ...appSettings, proactive_companion: "on" };
    proactiveStatusStore = {
      ...proactiveStatus,
      enabled: true,
      sensitivity: "low",
      active_candidate_triggers: ["repeated_death"]
    };
    proactiveCheckStore = {
      should_send: true,
      trigger_type: "repeated_death",
      message: "你开始急了。",
      reason: "death_delta=2",
      cooldown_remaining_seconds: 0,
      idle_for_seconds: 120,
      idle_threshold_seconds: 600,
      initial_grace_remaining_seconds: 0,
      next_possible_trigger_at: null,
      enabled_at: new Date().toISOString(),
      last_user_activity_at: new Date().toISOString(),
      requires_user_activity_after_proactive: false,
      block_reason: "eligible",
      active_candidate_triggers: ["repeated_death"]
    };

    render(<App />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText("已连接")).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });

    const proactiveMessage = screen.getByText("你开始急了。");
    const bubble = proactiveMessage.closest("article");
    expect(screen.getByText(/主动 · 反复死亡/)).toBeInTheDocument();
    expect(bubble).toHaveClass("messageBubble", "assistant", "proactive");
    expect(bubble).not.toHaveClass("system");
  });

  it("does not poll proactive check while proactive companion is off", async () => {
    vi.useFakeTimers();
    render(<App />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText("已连接")).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });

    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/proactive/check"),
      expect.anything()
    );
  });

  it("does not show an interim placeholder before three seconds", async () => {
    vi.useFakeTimers();
    let resolveChat: (value: Response) => void = () => {};
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return Promise.resolve(debugAction);
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return Promise.resolve(pendingResponse);
        const settings = settingsResponse(url, init);
        if (settings) return Promise.resolve(settings);
        const gameContextResponseValue = gameContextResponse(url, init);
        if (gameContextResponseValue) return Promise.resolve(gameContextResponseValue);
        const proactive = proactiveResponse(url, init);
        if (proactive) return Promise.resolve(proactive);
        if (url.endsWith("/api/health")) return Promise.resolve(Response.json({ status: "ok" }));
        if (url.endsWith("/api/game/status")) return Promise.resolve(Response.json(runningStatus));
        if (url.endsWith("/api/game/detected")) return Promise.resolve(Response.json(gameDetection));
        if (url.endsWith("/api/memory/profile")) return Promise.resolve(Response.json(memoryProfile));
        if (url.includes("/api/debug/memory")) return Promise.resolve(Response.json(memoryDebug));
        if (url.endsWith("/api/debug/chat")) return Promise.resolve(Response.json(chatDebug));
        if (url.endsWith("/api/debug/provider")) return Promise.resolve(Response.json(providerDebug));
        if (url.endsWith("/api/debug/game-session")) return Promise.resolve(Response.json(gameSessionDebug));
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Promise.resolve(Response.json(semanticExtractionDebug));
        if (url.includes("/api/debug/prompt-preview")) return Promise.resolve(Response.json(promptPreview));
        if (url.endsWith("/api/chat") && init?.method === "POST") {
          return new Promise<Response>((resolve) => {
            resolveChat = resolve;
          });
        }
        return Promise.resolve(new Response("missing", { status: 404 }));
      })
    );
    render(<App />);
    fireEvent.change(screen.getByLabelText("聊天输入"), { target: { value: "你好" } });
    fireEvent.click(screen.getByRole("button", { name: /发送/i }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2999);
    });
    expect(screen.queryByText("……")).not.toBeInTheDocument();
    await act(async () => {
      resolveChat(
        Response.json({
          reply: "我在。",
          reply_segments: ["我在。"],
          segmenter_mode: "compact",
          persona_id: "rei_like",
          game_status: "running",
          sources: [],
          timestamp: new Date().toISOString()
        })
      );
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText("我在。")).toBeInTheDocument();
  });

  it("shows an interim placeholder after three seconds and removes it after the official reply", async () => {
    vi.useFakeTimers();
    vi.spyOn(Math, "random").mockReturnValue(0);
    let resolveChat: (value: Response) => void = () => {};
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return Promise.resolve(debugAction);
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return Promise.resolve(pendingResponse);
        const settings = settingsResponse(url, init);
        if (settings) return Promise.resolve(settings);
        const gameContextResponseValue = gameContextResponse(url, init);
        if (gameContextResponseValue) return Promise.resolve(gameContextResponseValue);
        const proactive = proactiveResponse(url, init);
        if (proactive) return Promise.resolve(proactive);
        if (url.endsWith("/api/health")) return Promise.resolve(Response.json({ status: "ok" }));
        if (url.endsWith("/api/game/status")) return Promise.resolve(Response.json(runningStatus));
        if (url.endsWith("/api/game/detected")) return Promise.resolve(Response.json(gameDetection));
        if (url.endsWith("/api/memory/profile")) return Promise.resolve(Response.json(memoryProfile));
        if (url.includes("/api/debug/memory")) return Promise.resolve(Response.json(memoryDebug));
        if (url.endsWith("/api/debug/chat")) return Promise.resolve(Response.json(chatDebug));
        if (url.endsWith("/api/debug/provider")) return Promise.resolve(Response.json(providerDebug));
        if (url.endsWith("/api/debug/game-session")) return Promise.resolve(Response.json(gameSessionDebug));
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Promise.resolve(Response.json(semanticExtractionDebug));
        if (url.includes("/api/debug/prompt-preview")) return Promise.resolve(Response.json(promptPreview));
        if (url.endsWith("/api/chat") && init?.method === "POST") {
          return new Promise<Response>((resolve) => {
            resolveChat = resolve;
          });
        }
        return Promise.resolve(new Response("missing", { status: 404 }));
      })
    );
    render(<App />);
    fireEvent.change(screen.getByLabelText("聊天输入"), { target: { value: "你好" } });
    fireEvent.click(screen.getByRole("button", { name: /发送/i }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(screen.getByText("……")).toBeInTheDocument();
    await act(async () => {
      resolveChat(
        Response.json({
          reply: "我在。",
          reply_segments: ["我在。"],
          segmenter_mode: "compact",
          persona_id: "rei_like",
          game_status: "running",
          sources: [],
          timestamp: new Date().toISOString()
        })
      );
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText("我在。")).toBeInTheDocument();
    expect(screen.queryByText("……")).not.toBeInTheDocument();
  });

  it("uses only neutral low-semantic interim placeholders", () => {
    expect(INTERIM_PLACEHOLDERS).toEqual(["……", "……嗯", "嗯……"]);
    expect(INTERIM_PLACEHOLDERS).not.toContain("我听见了。");
    expect(INTERIM_PLACEHOLDERS).not.toContain("等一下。");
    expect(INTERIM_PLACEHOLDERS).not.toContain("别急。");
  });

  it("renders reply segments with staggered timing", async () => {
    vi.useFakeTimers();
    vi.spyOn(Math, "random").mockReturnValue(0);
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return Promise.resolve(debugAction);
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return Promise.resolve(pendingResponse);
        const settings = settingsResponse(url, init);
        if (settings) return Promise.resolve(settings);
        const gameContextResponseValue = gameContextResponse(url, init);
        if (gameContextResponseValue) return Promise.resolve(gameContextResponseValue);
        const proactive = proactiveResponse(url, init);
        if (proactive) return Promise.resolve(proactive);
        if (url.endsWith("/api/health")) return Promise.resolve(Response.json({ status: "ok" }));
        if (url.endsWith("/api/game/status")) return Promise.resolve(Response.json(runningStatus));
        if (url.endsWith("/api/game/detected")) return Promise.resolve(Response.json(gameDetection));
        if (url.endsWith("/api/memory/profile")) return Promise.resolve(Response.json(memoryProfile));
        if (url.includes("/api/debug/memory")) return Promise.resolve(Response.json(memoryDebug));
        if (url.endsWith("/api/debug/chat")) return Promise.resolve(Response.json({ ...chatDebug, reply_segments_count: 3, segmenter_mode: "strategy" }));
        if (url.endsWith("/api/debug/provider")) return Promise.resolve(Response.json(providerDebug));
        if (url.endsWith("/api/debug/game-session")) return Promise.resolve(Response.json(gameSessionDebug));
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Promise.resolve(Response.json(semanticExtractionDebug));
        if (url.includes("/api/debug/prompt-preview")) return Promise.resolve(Response.json(promptPreview));
        if (url.endsWith("/api/chat") && init?.method === "POST") {
          return Promise.resolve(
            Response.json({
              reply: "别急。少打一刀。先活下来。",
              reply_segments: ["别急。", "少打一刀。", "先活下来。"],
              segmenter_mode: "strategy",
              persona_id: "rei_like",
              game_status: "running",
              sources: [],
              timestamp: new Date().toISOString()
            })
          );
        }
        return Promise.resolve(new Response("missing", { status: 404 }));
      })
    );
    render(<App />);
    fireEvent.change(screen.getByLabelText("聊天输入"), { target: { value: "Margit 怎么打" } });
    fireEvent.click(screen.getByRole("button", { name: /发送/i }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText("别急。")).toBeInTheDocument();
    expect(screen.queryByText("少打一刀。")).not.toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(screen.getByText("少打一刀。")).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(screen.getByText("先活下来。")).toBeInTheDocument();
  });

  it("shows disconnected state when backend fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("offline", { status: 500 })));
    render(<App />);
    await screen.findByText("未连接");
  });

  it("toggles debug panel", async () => {
    render(<App />);

    await screen.findByText("游戏状态");
    expect(screen.getAllByText("当前游戏").length).toBeGreaterThan(0);
    expect(screen.getByText("当前 Boss")).toBeInTheDocument();
    expect(screen.getByText("状态新鲜度")).toBeInTheDocument();
    expect(screen.getByText("最近挑战")).toBeInTheDocument();
    expect(screen.getByText("最近通过")).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText("语义识别")).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "游戏上下文" })).toBeInTheDocument();
    expect(screen.getAllByText("当前来源").length).toBeGreaterThan(0);
    expect(screen.getAllByText("上一个游戏").length).toBeGreaterThan(0);
    expect(screen.getAllByText("发生游戏切换").length).toBeGreaterThan(0);
    expect(screen.getAllByText("手动选择").length).toBeGreaterThan(0);
    expect(screen.getAllByText("自动检测结果").length).toBeGreaterThan(0);
    expect(screen.getByText("对话识别结果")).toBeInTheDocument();
    expect(screen.getAllByText("知识库状态").length).toBeGreaterThan(0);
    expect(screen.getAllByText("已支持").length).toBeGreaterThan(0);
    expect(screen.getAllByText("使用知识库").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "游戏检测" })).toBeInTheDocument();
    expect(screen.getAllByText("自动游戏检测").length).toBeGreaterThan(0);
    expect(screen.getByText("检测状态")).toBeInTheDocument();
    expect(screen.getByText("检测到的游戏")).toBeInTheDocument();
    expect(screen.getByText("进程名")).toBeInTheDocument();
    expect(screen.getByText("匹配置信度")).toBeInTheDocument();
    expect(screen.getByText("知识库游戏 ID")).toBeInTheDocument();
    expect(screen.getByText("检测时间")).toBeInTheDocument();
    expect(screen.getAllByText("艾尔登法环").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "主动陪伴" })).toBeInTheDocument();
    expect(screen.getAllByText("是否开启").length).toBeGreaterThan(0);
    expect(screen.getByText("开启时间")).toBeInTheDocument();
    expect(screen.getByText("最近用户活动")).toBeInTheDocument();
    expect(screen.getByText("已空闲时间")).toBeInTheDocument();
    expect(screen.getByText("空闲触发阈值")).toBeInTheDocument();
    expect(screen.getByText("初始等待剩余")).toBeInTheDocument();
    expect(screen.getByText("等待用户回应")).toBeInTheDocument();
    expect(screen.getByText("下次可能触发")).toBeInTheDocument();
    expect(screen.getByText("阻断原因")).toBeInTheDocument();
    expect(screen.getByText("冷却剩余")).toBeInTheDocument();
    expect(screen.getByText("上次触发类型")).toBeInTheDocument();
    expect(screen.getByText("上次触发时间")).toBeInTheDocument();
    expect(screen.getByText("候选触发器")).toBeInTheDocument();
    expect(screen.getByText("上次触发原因")).toBeInTheDocument();
    expect(screen.getByText("模型路由")).toBeInTheDocument();
    expect(screen.getAllByText("选用模型").length).toBeGreaterThan(0);
    expect(screen.getByText("路由模式")).toBeInTheDocument();
    expect(screen.getAllByText("路由原因").length).toBeGreaterThan(0);
    expect(screen.getByText("模型耗时")).toBeInTheDocument();
    expect(screen.getByText("游戏知识")).toBeInTheDocument();
    expect(screen.getAllByText("当前游戏 ID").length).toBeGreaterThan(0);
    expect(screen.getAllByText("当前来源").length).toBeGreaterThan(0);
    expect(screen.getAllByText("知识库状态").length).toBeGreaterThan(0);
    expect(screen.getAllByText("知识命中").length).toBeGreaterThan(0);
    expect(screen.getAllByText("相关主题").length).toBeGreaterThan(0);
    expect(screen.getAllByText("命中知识条数").length).toBeGreaterThan(0);
    expect(screen.getAllByText("命中的知识标题").length).toBeGreaterThan(0);
    expect(screen.getAllByText("已注入回复上下文").length).toBeGreaterThan(0);
    expect(screen.getAllByText("匹配来源").length).toBeGreaterThan(0);
    expect(screen.getAllByText("知识文件").length).toBeGreaterThan(0);
    expect(screen.getAllByText("知识包清单").length).toBeGreaterThan(0);
    expect(screen.getAllByText("知识包版本").length).toBeGreaterThan(0);
    expect(screen.getAllByText("语言").length).toBeGreaterThan(0);
    expect(screen.getAllByText("知识包状态").length).toBeGreaterThan(0);
    expect(screen.getAllByText("覆盖范围").length).toBeGreaterThan(0);
    expect(screen.getAllByText("最后更新").length).toBeGreaterThan(0);
    expect(screen.getAllByText("0.1.0").length).toBeGreaterThan(0);
    expect(screen.getAllByText("zh-CN").length).toBeGreaterThan(0);
    expect(screen.getAllByText("样例").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/恶兆妖鬼 Margit：延迟攻击/).length).toBeGreaterThan(0);
    expect(screen.getByText("语义识别")).toBeInTheDocument();
    expect(screen.getByText("是否调用 LLM")).toBeInTheDocument();
    expect(screen.getAllByText(/攻略偏好/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /回复上下文预览/i })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /回复上下文预览/i }));
    await waitFor(() => expect(screen.getAllByText("人格模式").length).toBeGreaterThan(1));
    expect(screen.getByText("上下文顺序")).toBeInTheDocument();
    expect(screen.getAllByText("选用模型").length).toBeGreaterThan(0);
    expect(screen.getAllByText("路由原因").length).toBeGreaterThan(0);
    expect(screen.getByText("当前用户消息")).toBeInTheDocument();
    expect(screen.getByText("会话焦点")).toBeInTheDocument();
    expect(screen.getByText("游戏状态摘要")).toBeInTheDocument();
    expect(screen.getAllByText("知识命中").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Elden Ring").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Boss 攻略").length).toBeGreaterThan(0);
    expect(screen.getByText("记忆摘要")).toBeInTheDocument();
    expect(screen.getByText("注入记忆")).toBeInTheDocument();
    expect(screen.getByText("跳过记忆")).toBeInTheDocument();
    expect(screen.getByText("待确认记忆")).toBeInTheDocument();
    expect(screen.getByText("玩家不喜欢长篇攻略")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "忽略" })).toBeInTheDocument();
    expect(screen.getByText("警告")).toBeInTheDocument();
    expect(screen.getByText("原始 JSON")).toBeInTheDocument();
    expect(screen.getByText("原始 JSON").closest("details")).not.toHaveAttribute("open");
    await userEvent.click(screen.getByRole("button", { name: /调试面板/i }));
    await waitFor(() => expect(screen.queryByText("语义识别")).not.toBeInTheDocument());
  });

  it("shows idle game detector state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return debugAction;
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return pendingResponse;
        const settings = settingsResponse(url, init);
        if (settings) return settings;
        if (url.endsWith("/api/game/context")) return Response.json(idleGameContext);
        if (url.endsWith("/api/game/context/manual") && init?.method === "POST") return Response.json(idleGameContext);
        const proactive = proactiveResponse(url, init);
        if (proactive) return proactive;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json({ ...runningStatus, status: "idle", game_id: null, game_name: null });
        if (url.endsWith("/api/game/detected")) return Response.json(idleGameDetection);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(chatDebug);
        if (url.endsWith("/api/debug/provider")) return Response.json(providerDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json({ ...gameSessionDebug, current_game: null });
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Response.json(semanticExtractionDebug);
        if (url.includes("/api/debug/prompt-preview")) return Response.json(promptPreview);
        if (url.endsWith("/api/chat") && init?.method === "POST") return Response.json(chatResponse);
        return new Response("missing", { status: 404 });
      })
    );

    render(<App />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "游戏检测" })).toBeInTheDocument());
    expect(screen.getAllByText("未检测到游戏").length).toBeGreaterThan(0);
    expect(screen.getAllByText("未匹配").length).toBeGreaterThan(0);
  });

  it("shows unsupported catalog games as model-only knowledge context", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return debugAction;
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return pendingResponse;
        const settings = settingsResponse(url, init);
        if (settings) return settings;
        if (url.endsWith("/api/game/context")) return Response.json(unsupportedGameContext);
        if (url.endsWith("/api/game/context/manual") && init?.method === "POST") {
          return Response.json(unsupportedGameContext);
        }
        const proactive = proactiveResponse(url, init);
        if (proactive) return proactive;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json({ ...runningStatus, game_id: "sekiro", game_name: "只狼" });
        if (url.endsWith("/api/game/detected")) return Response.json(idleGameDetection);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(unsupportedChatDebug);
        if (url.endsWith("/api/debug/provider")) return Response.json(providerDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json({ ...gameSessionDebug, current_game: "只狼" });
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Response.json(semanticExtractionDebug);
        if (url.includes("/api/debug/prompt-preview")) return Response.json(unsupportedPromptPreview);
        if (url.endsWith("/api/chat") && init?.method === "POST") return Response.json(chatResponse);
        return new Response("missing", { status: 404 });
      })
    );

    render(<App />);

    await waitFor(() => expect(screen.getAllByText("只狼").length).toBeGreaterThan(0));
    expect(screen.getAllByText("暂未支持").length).toBeGreaterThan(0);
    expect(screen.getByText("该游戏暂未接入本地知识库，Rei 会先根据通用模型回答。")).toBeInTheDocument();
    expect(screen.getAllByText("仅使用模型回答").length).toBeGreaterThan(0);
    expect(screen.getAllByText("未支持知识库").length).toBeGreaterThan(0);
    expect(screen.getAllByText("manifest 缺失").length).toBeGreaterThan(0);
    expect(screen.getAllByText("用户切换").length).toBeGreaterThan(0);
    expect(screen.queryByText(/恶兆妖鬼 Margit：延迟攻击/)).not.toBeInTheDocument();
  });

  it("shows Hollow Knight as supported knowledge context", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return debugAction;
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return pendingResponse;
        const settings = settingsResponse(url, init);
        if (settings) return settings;
        if (url.endsWith("/api/game/context")) return Response.json(hollowKnightGameContext);
        if (url.endsWith("/api/game/context/manual") && init?.method === "POST") {
          return Response.json(hollowKnightGameContext);
        }
        const proactive = proactiveResponse(url, init);
        if (proactive) return proactive;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json({ ...runningStatus, game_id: "hollow_knight", game_name: "空洞骑士" });
        if (url.endsWith("/api/game/detected")) return Response.json(idleGameDetection);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(hollowKnightChatDebug);
        if (url.endsWith("/api/debug/provider")) return Response.json(providerDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json({ ...gameSessionDebug, current_game: "空洞骑士" });
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Response.json(semanticExtractionDebug);
        if (url.includes("/api/debug/prompt-preview")) return Response.json(hollowKnightPromptPreview);
        if (url.endsWith("/api/chat") && init?.method === "POST") return Response.json(chatResponse);
        return new Response("missing", { status: 404 });
      })
    );

    render(<App />);

    await waitFor(() => expect(screen.getAllByText("空洞骑士").length).toBeGreaterThan(0));
    expect(screen.getAllByText("已支持").length).toBeGreaterThan(0);
    expect(screen.getAllByText("使用知识库").length).toBeGreaterThan(0);
    expect(screen.getAllByText("0.1.0").length).toBeGreaterThan(0);
    expect(screen.getAllByText("zh-CN").length).toBeGreaterThan(0);
    expect(screen.getAllByText("样例").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/机制/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/螳螂领主/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("螳螂领主：节奏观察").length).toBeGreaterThan(0);
  });

  it("shows manual override conflict warning from game context", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return debugAction;
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return pendingResponse;
        const settings = settingsResponse(url, init);
        if (settings) return settings;
        if (url.endsWith("/api/game/context")) return Response.json(manualConflictGameContext);
        if (url.endsWith("/api/game/context/manual") && init?.method === "POST") {
          return Response.json(manualConflictGameContext);
        }
        const proactive = proactiveResponse(url, init);
        if (proactive) return proactive;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json(runningStatus);
        if (url.endsWith("/api/game/detected")) return Response.json(gameDetection);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(chatDebug);
        if (url.endsWith("/api/debug/provider")) return Response.json(providerDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json(gameSessionDebug);
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Response.json(semanticExtractionDebug);
        if (url.includes("/api/debug/prompt-preview")) {
          return Response.json({
            ...promptPreview,
            game_context_summary: manualConflictGameContext,
            warnings: ["user_message_game_conflicts_with_manual_override"]
          });
        }
        if (url.endsWith("/api/chat") && init?.method === "POST") return Response.json(chatResponse);
        return new Response("missing", { status: 404 });
      })
    );

    render(<App />);

    await waitFor(() =>
      expect(screen.getAllByText("用户消息疑似切换游戏，但手动选择优先").length).toBeGreaterThan(0)
    );
    expect(screen.getAllByText("手动选择").length).toBeGreaterThan(0);
  });

  it("shows unknown switched game as not connected to knowledge", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return debugAction;
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return pendingResponse;
        const settings = settingsResponse(url, init);
        if (settings) return settings;
        if (url.endsWith("/api/game/context")) return Response.json(unknownGameContext);
        if (url.endsWith("/api/game/context/manual") && init?.method === "POST") {
          return Response.json(unknownGameContext);
        }
        const proactive = proactiveResponse(url, init);
        if (proactive) return proactive;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json({ ...runningStatus, game_id: null, game_name: "星之门遗迹" });
        if (url.endsWith("/api/game/detected")) return Response.json(idleGameDetection);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(unknownChatDebug);
        if (url.endsWith("/api/debug/provider")) return Response.json(providerDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json({ ...gameSessionDebug, current_game: "星之门遗迹" });
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Response.json(semanticExtractionDebug);
        if (url.includes("/api/debug/prompt-preview")) return Response.json(unknownPromptPreview);
        if (url.endsWith("/api/chat") && init?.method === "POST") return Response.json(chatResponse);
        return new Response("missing", { status: 404 });
      })
    );

    render(<App />);

    await waitFor(() => expect(screen.getAllByText("星之门遗迹").length).toBeGreaterThan(0));
    expect(screen.getAllByText("未接入知识库").length).toBeGreaterThan(0);
    expect(screen.getAllByText("仅使用模型回答").length).toBeGreaterThan(0);
  });

  it("falls back to game session debug data and shows empty warnings as none", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return debugAction;
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return pendingResponse;
        const settings = settingsResponse(url, init);
        if (settings) return settings;
        const gameContextResponseValue = gameContextResponse(url, init);
        if (gameContextResponseValue) return gameContextResponseValue;
        const proactive = proactiveResponse(url, init);
        if (proactive) return proactive;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json(runningStatus);
        if (url.endsWith("/api/game/detected")) return Response.json(gameDetection);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(chatDebug);
        if (url.endsWith("/api/debug/provider")) return Response.json(providerDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json(gameSessionDebug);
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Response.json(semanticExtractionDebug);
        if (url.includes("/api/debug/prompt-preview")) {
          return Response.json({
            ...promptPreview,
            game_state_summary: {},
            memory_summary: { injected: [], skipped: [] },
            warnings: []
          });
        }
        return new Response("missing", { status: 404 });
      })
    );

    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /回复上下文预览/i }));

    const gameStateSection = screen.getByText("游戏状态摘要").closest("section");
    expect(gameStateSection).not.toBeNull();
    expect(gameStateSection?.textContent).toContain("恶兆妖鬼 Margit");
    expect(gameStateSection?.textContent).toContain("挑战中");

    const warningsSection = screen.getByText("警告").closest(".debugSubgroup");
    expect(warningsSection).not.toBeNull();
    expect(within(warningsSection as HTMLElement).getByText("无")).toBeInTheDocument();
  });

  it("accepts pending memory from the debug panel", async () => {
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "保存" }));

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/memory/pending/pending-1/accept"),
        expect.objectContaining({ method: "POST" })
      )
    );
  });

  it("shows empty pending memory state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return debugAction;
        if (url.endsWith("/api/memory/pending")) return Response.json([]);
        const settings = settingsResponse(url, init);
        if (settings) return settings;
        const gameContextResponseValue = gameContextResponse(url, init);
        if (gameContextResponseValue) return gameContextResponseValue;
        const proactive = proactiveResponse(url, init);
        if (proactive) return proactive;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json(runningStatus);
        if (url.endsWith("/api/game/detected")) return Response.json(gameDetection);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(chatDebug);
        if (url.endsWith("/api/debug/provider")) return Response.json(providerDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json(gameSessionDebug);
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Response.json(semanticExtractionDebug);
        if (url.includes("/api/debug/prompt-preview")) return Response.json(promptPreview);
        return new Response("missing", { status: 404 });
      })
    );

    render(<App />);
    expect(await screen.findByText("暂无待确认记忆")).toBeInTheDocument();
  });

  it("calls debug reset and clear endpoints", async () => {
    render(<App />);
    await screen.findByRole("button", { name: /调试面板/i });

    await userEvent.click(await screen.findByRole("button", { name: "重置游戏状态" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/debug/game-session/reset"),
        expect.objectContaining({ method: "POST" })
      )
    );

    await userEvent.click(screen.getByRole("button", { name: "重置记忆" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/memory/reset"),
        expect.objectContaining({ method: "POST" })
      )
    );

    await userEvent.click(screen.getByRole("button", { name: "清空待确认记忆" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/memory/pending/clear"),
        expect.objectContaining({ method: "POST" })
      )
    );
  });
});
