import { act } from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App, EventStreamPanel, INTERIM_PLACEHOLDERS } from "../App";
import { audioCapture } from "../audioCapture";
import { eventBus } from "../eventBus";
import { voiceInput } from "../voiceInput";
import { voiceOutput } from "../voiceOutput";
import type {
  AppSettings,
  AudioProbeResponse,
  GameContextResponse,
  GameDetectionResponse,
  LocalAsrProbeResponse,
  LocalAsrSettings,
  LocalAsrStatus,
  LocalAsrTranscriptionResponse,
  ProactiveCheckResponse,
  ProactiveStatusResponse,
  SetupStatus
} from "../../shared/api";
import type { BackendRuntimeStatus, ReilinkRuntimeBridge } from "../../shared/runtime";
import type { OverlayState } from "../../shared/overlay";

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
  snippet_previews: ["Margit 很多攻击会故意延迟。保持中距离。", "如果伤害明显不够，可以先强化武器。"],
  matched_terms: ["margit", "恶兆妖鬼"],
  result_scores: [18, 14],
  knowledge_used_in_prompt: true,
  knowledge_retrieval_status: "used",
  knowledge_not_used_reason: null,
  knowledge_retrieval_min_score: 8
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
  snippet_previews: [],
  matched_terms: [],
  result_scores: [],
  knowledge_used_in_prompt: false,
  knowledge_retrieval_status: "no_pack",
  knowledge_not_used_reason: "no_supported_knowledge",
  knowledge_retrieval_min_score: 8
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
  snippet_previews: ["螳螂领主的威胁主要来自连续冲刺和下劈。"],
  matched_terms: ["螳螂领主"],
  result_scores: [18],
  knowledge_used_in_prompt: true,
  knowledge_retrieval_status: "used",
  knowledge_not_used_reason: null,
  knowledge_retrieval_min_score: 8
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
  prompt_order: [
    "base_system_safety",
    "persona_pack",
    "current_session_context",
    "session_focus",
    "game_state",
    "memory",
    "knowledge",
    "current_user_message"
  ],
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
  persona_pack_summary: {
    id: "rei",
    name: "Rei",
    version: "1.1.2",
    language: "zh-CN",
    enabled: true,
    status: "loaded",
    loaded_sections: ["persona", "style_calibration", "voice", "response_patterns", "boundaries"],
    injected_sections: ["persona", "style_calibration", "voice", "response_patterns", "boundaries"],
    missing_sections: [],
    omitted_sections: [],
    errors: [],
    fallback_used: false,
    persona_section_truncated: false,
    truncated_sections: [],
    prompt_char_count: 2200,
    prompt_char_budget: 6000,
    raw_content_omitted: true,
    path_omitted: true
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
    retrieval_status: "used",
    not_used_reason: null,
    retrieval_min_score: 8,
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
    retrieval_status: "no_pack",
    not_used_reason: "no_supported_knowledge",
    retrieval_min_score: 8,
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
    retrieval_status: "used",
    not_used_reason: null,
    retrieval_min_score: 8,
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
    not_used_reason: "unknown_game",
    fallback_reason: "unknown_game"
  }
};

const semanticExtractionDebug = {
  latest_user_message: "记忆偏好表达 / 10 字",
  rule_result: { game_event: { type: "none" }, memory_candidate: { type: "guide_preference" } },
  rule_confidence: 0.65,
  raw_rule_confidence: 0.65,
  ambiguity_detected: false,
  fallback_reason: null,
  source: "rule",
  confidence: "medium",
  applied_updates: ["memory_candidate_created"],
  extraction_trace: {
    source: "rule",
    confidence: "medium",
    fallback_reason: null,
    skip_reason: null,
    parse_error: null,
    applied_updates: ["memory_candidate_created"],
    llm_shadow_status: "skipped",
    llm_shadow_confidence: "low",
    llm_shadow_summary: "跳过：no_semantic_signal",
    llm_shadow_diff: "LLM 影子识别未运行"
  },
  llm_called: false,
  semantic_extraction_model: null,
  semantic_extraction_latency_ms: 0,
  provider_latency_ms: 0,
  llm_result: null,
  llm_shadow: {
    status: "skipped",
    confidence: "low",
    candidate_summary: "跳过：no_semantic_signal",
    diff_summary: "LLM 影子识别未运行"
  },
  llm_shadow_status: "skipped",
  llm_shadow_confidence: "low",
  llm_shadow_summary: "跳过：no_semantic_signal",
  llm_shadow_diff: "LLM 影子识别未运行",
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

const setupStatus: SetupStatus = {
  backend_ready: true,
  provider_configured: true,
  provider: "deepseek",
  api_key_loaded: true,
  base_url: "https://api.deepseek.com",
  model_preference: "auto",
  persona_mode: "minimal",
  memory_ready: true,
  knowledge_ready: true,
  needs_setup: false,
  missing_items: [],
  fast_model: "deepseek-v4-flash",
  pro_model: "deepseek-v4-pro"
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
let setupStatusStore: SetupStatus = { ...setupStatus };
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

const appSettings: AppSettings = {
  persona_mode: "minimal",
  debug_panel: "show",
  memory_enabled: true,
  pending_memory_mode: "manual",
  response_length: "normal",
  model_preference: "auto",
  proactive_companion: "off",
  proactive_sensitivity: "low",
  auto_game_detection: "on",
  overlay_enabled: "off",
  overlay_position: "middle-right",
  overlay_opacity: 0.72,
  overlay_message_count: 2,
  voice_output: "off",
  voice_rate: 1,
  voice_volume: 1,
  onboarding_completed: true,
  onboarding_last_seen_at: "2026-06-01T12:00:00.000Z"
};

const backendRuntimeStatus: BackendRuntimeStatus = {
  backend_auto_start_enabled: true,
  backend_app_mode: "packaged",
  backend_binary_exists: false,
  backend_binary_path: null,
  bundled_backend_binary_path: "/Applications/ReiLink.app/Contents/Resources/backend/reilink-backend",
  bundled_backend_exists: true,
  backend_started_by_app: false,
  backend_started_from: "external",
  backend_start_error: null,
  backend_status: "external_backend_detected",
  backend_runtime_mode: "auto",
  backend_project_root: "/Users/aragoto/Desktop/ReiLink",
  backend_root: "/Users/aragoto/Desktop/ReiLink/services/backend",
  backend_python_path: "/Users/aragoto/Desktop/ReiLink/services/backend/.venv/bin/python",
  backend_health_url: "http://127.0.0.1:8000/api/health",
  backend_retry_count: 0,
  knowledge_path: "/Applications/ReiLink.app/Contents/Resources/knowledge/games",
  knowledge_source: "bundled",
  user_data_dir: "/Users/aragoto/Library/Application Support/ReiLink/data"
};

const localDataStatus = {
  data_dir: "/Users/aragoto/Library/Application Support/ReiLink/data",
  memory_dir: "/Users/aragoto/Library/Application Support/ReiLink/data/memory",
  session_dir: "/Users/aragoto/Library/Application Support/ReiLink/data/session",
  settings_dir: "/Users/aragoto/Library/Application Support/ReiLink/data/settings",
  logs_dir: "/Users/aragoto/Library/Application Support/ReiLink/data/logs",
  knowledge_dir: "/Applications/ReiLink.app/Contents/Resources/knowledge/games",
  knowledge_source: "bundled",
  data_dir_exists: true,
  memory_files_count: 2,
  session_files_count: 3,
  pending_memory_count: 1,
  using_bundled_knowledge: true,
  writable: true
} as const;

const localAsrStatus: LocalAsrStatus = {
  status: "local_asr_not_configured",
  available: false,
  binary_configured: false,
  binary_present: false,
  binary_executable: false,
  model_configured: false,
  model_present: false,
  display_message: "本地语音识别未配置",
  safe_binary_name: null,
  safe_model_name: null,
  converter_configured: false,
  safe_converter_name: null,
  source: "none"
};

const localAsrSettings: LocalAsrSettings = {
  configured: false,
  binary_configured: false,
  model_configured: false,
  converter_configured: false,
  safe_binary_name: null,
  safe_model_name: null,
  safe_converter_name: null,
  source: "none"
};

const localAsrProbeResponse: LocalAsrProbeResponse = {
  status: "local_asr_probe_succeeded",
  available: true,
  display_message: "本地语音识别程序可以启动",
  binary_name: "whisper-cli",
  model_name: "ggml-base.bin",
  duration_ms: 42
};

const audioProbeResponse: AudioProbeResponse = {
  status: "audio_probe_succeeded",
  available: true,
  display_message: "录音测试完成，临时音频已清理",
  duration_ms: 3000,
  size_bytes: 16,
  mime_type: "audio/webm",
  temporary_file_cleaned: true
};

const localAsrTranscriptionResponse: LocalAsrTranscriptionResponse = {
  status: "local_asr_transcription_succeeded",
  available: true,
  display_message: "本地语音识别完成",
  transcript: "Margit 怎么打",
  transcript_char_count: "Margit 怎么打".length,
  language: "zh",
  transcript_normalized_to_simplified: false,
  duration_ms: 3000,
  size_bytes: 16,
  mime_type: "audio/webm",
  audio_format: "audio/webm",
  conversion_status: "audio_conversion_succeeded",
  conversion_required: true,
  converted_mime_type: "audio/wav",
  converter_configured: true,
  safe_converter_name: "ffmpeg",
  temporary_file_cleaned: true,
  temporary_input_cleaned: true,
  temporary_converted_cleaned: true,
  binary_name: "whisper-cli",
  model_name: "ggml-base.bin"
};

let appSettingsStore = { ...appSettings };
let localAsrStatusStore: LocalAsrStatus = { ...localAsrStatus };
let localAsrSettingsStore: LocalAsrSettings = { ...localAsrSettings };
let localAsrProbeResponseStore: LocalAsrProbeResponse = { ...localAsrProbeResponse };
let audioProbeResponseStore: AudioProbeResponse = { ...audioProbeResponse };
let localAsrTranscriptionResponseStore: LocalAsrTranscriptionResponse = { ...localAsrTranscriptionResponse };
let gameContextStore = { ...gameContext };
let chatFailureResponse: (() => Response) | null = null;
let omitVoiceOutputFromSettings = false;
let scrollToMock: ReturnType<typeof vi.fn>;

class MockSpeechSynthesisUtterance {
  text: string;
  rate = 1;
  volume = 1;
  voice: SpeechSynthesisVoice | null = null;
  lang = "";
  onstart: ((event: SpeechSynthesisEvent) => void) | null = null;
  onend: ((event: SpeechSynthesisEvent) => void) | null = null;
  onerror: ((event: SpeechSynthesisErrorEvent) => void) | null = null;

  constructor(text: string) {
    this.text = text;
  }
}

const mockVoice = (lang: string, name = lang): SpeechSynthesisVoice =>
  ({
    default: false,
    lang,
    localService: true,
    name,
    voiceURI: name
  }) as SpeechSynthesisVoice;

const installSpeechSynthesisMock = (voices: SpeechSynthesisVoice[] = []) => {
  const listeners = new Set<() => void>();
  const speak = vi.fn();
  const cancel = vi.fn();
  const resume = vi.fn();
  const getVoices = vi.fn(() => voices);
  const setVoices = (nextVoices: SpeechSynthesisVoice[]) => {
    voices = nextVoices;
    for (const listener of listeners) listener();
  };
  vi.stubGlobal("SpeechSynthesisUtterance", MockSpeechSynthesisUtterance);
  Object.defineProperty(window, "speechSynthesis", {
    configurable: true,
    value: {
      speak,
      cancel,
      resume,
      getVoices,
      paused: false,
      pending: false,
      speaking: false,
      addEventListener: vi.fn((event: string, listener: () => void) => {
        if (event === "voiceschanged") listeners.add(listener);
      }),
      removeEventListener: vi.fn((event: string, listener: () => void) => {
        if (event === "voiceschanged") listeners.delete(listener);
      }),
      onvoiceschanged: null
    }
  });
  return { speak, cancel, resume, getVoices, setVoices };
};

type MockRecognitionResult = {
  isFinal: boolean;
  0: { transcript: string };
  length: number;
};

class MockSpeechRecognition {
  static instances: MockSpeechRecognition[] = [];
  static startError: Error | null = null;

  lang = "";
  interimResults = false;
  continuous = false;
  onstart: (() => void) | null = null;
  onresult: ((event: { resultIndex: number; results: MockRecognitionResult[] }) => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;
  start = vi.fn(() => {
    if (MockSpeechRecognition.startError) throw MockSpeechRecognition.startError;
    this.onstart?.();
  });
  stop = vi.fn(() => {
    this.onend?.();
  });
  abort = vi.fn(() => {
    this.onend?.();
  });

  constructor() {
    MockSpeechRecognition.instances.push(this);
  }

  emitResult(transcript: string, isFinal = true) {
    this.onresult?.({
      resultIndex: 0,
      results: [{ 0: { transcript }, length: 1, isFinal }]
    });
  }

  emitError(error: string) {
    this.onerror?.({ error });
  }
}

class MockMediaRecorder {
  static instances: MockMediaRecorder[] = [];
  static isTypeSupported = vi.fn(() => true);

  state: RecordingState = "inactive";
  mimeType: string;
  stream: MediaStream;
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onstop: (() => void) | null = null;
  onerror: (() => void) | null = null;
  start = vi.fn(() => {
    this.state = "recording";
  });
  stop = vi.fn(() => {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["fake-webm-audio"], { type: this.mimeType }) } as BlobEvent);
    this.onstop?.();
  });

  constructor(stream: MediaStream, options?: MediaRecorderOptions) {
    this.stream = stream;
    this.mimeType = options?.mimeType || "audio/webm";
    MockMediaRecorder.instances.push(this);
  }
}

const installSpeechRecognitionMock = (kind: "standard" | "webkit" = "standard") => {
  MockSpeechRecognition.instances = [];
  MockSpeechRecognition.startError = null;
  if (kind === "standard") {
    vi.stubGlobal("SpeechRecognition", MockSpeechRecognition);
    Object.defineProperty(window, "SpeechRecognition", { configurable: true, value: MockSpeechRecognition });
    Reflect.deleteProperty(window, "webkitSpeechRecognition");
  } else {
    vi.stubGlobal("webkitSpeechRecognition", MockSpeechRecognition);
    Object.defineProperty(window, "webkitSpeechRecognition", { configurable: true, value: MockSpeechRecognition });
    Reflect.deleteProperty(window, "SpeechRecognition");
  }
  return MockSpeechRecognition;
};

const installMediaDevicesMock = (permission: "prompt" | "granted" | "denied" = "prompt") => {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: vi.fn()
    }
  });
  Object.defineProperty(navigator, "permissions", {
    configurable: true,
    value: {
      query: vi.fn(async () => ({ state: permission }))
    }
  });
};

const installAudioCaptureMock = (options: { permissionDenied?: boolean } = {}) => {
  MockMediaRecorder.instances = [];
  MockMediaRecorder.isTypeSupported = vi.fn(() => true);
  const stop = vi.fn();
  const stream = {
    getTracks: vi.fn(() => [{ stop }])
  } as unknown as MediaStream;
  const getUserMedia = vi.fn(async () => {
    if (options.permissionDenied) {
      throw new DOMException("Permission denied", "NotAllowedError");
    }
    return stream;
  });
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia }
  });
  vi.stubGlobal("MediaRecorder", MockMediaRecorder);
  return { getUserMedia, stopTrack: stop, stream, recorder: MockMediaRecorder };
};

const installRuntimeBridge = (initialStatus: BackendRuntimeStatus) => {
  let status = { ...initialStatus };
  let overlayState: OverlayState = {
    enabled: false,
    visible: false,
    position: "middle-right",
    opacity: 0.72,
    messages: [],
    max_messages: 2,
    max_message_length: 96,
    updated_at: null
  };
  const listeners = new Set<(nextStatus: BackendRuntimeStatus) => void>();
  const overlayListeners = new Set<(nextState: typeof overlayState) => void>();
  const bridge: ReilinkRuntimeBridge = {
    getBackendStatus: vi.fn(async () => status),
    setBackendAutoStart: vi.fn(async (enabled: boolean) => {
      status = {
        ...status,
        backend_auto_start_enabled: enabled,
        backend_start_error: enabled ? null : "自动启动已关闭，请手动运行 make dev-backend。",
        backend_started_from: enabled ? status.backend_started_from : "none",
        backend_status: enabled ? status.backend_status : "disabled"
      };
      for (const listener of listeners) listener(status);
      return status;
    }),
    openLocalDataDir: vi.fn(async () => ({ ok: true, path: status.user_data_dir, error: null })),
    selectLocalFile: vi.fn(async () => ({ canceled: true, path: null })),
    getOverlayStatus: vi.fn(async () => overlayState),
    setOverlayEnabled: vi.fn(async (enabled: boolean) => {
      overlayState = { ...overlayState, enabled, visible: false };
      for (const listener of overlayListeners) listener(overlayState);
      return overlayState;
    }),
    setOverlayConfig: vi.fn(async (config) => {
      overlayState = {
        ...overlayState,
        position: config.position ?? overlayState.position,
        opacity: config.opacity ?? overlayState.opacity,
        max_messages: config.max_messages ?? overlayState.max_messages,
        messages: overlayState.messages.slice(-(config.max_messages ?? overlayState.max_messages))
      };
      for (const listener of overlayListeners) listener(overlayState);
      return overlayState;
    }),
    updateOverlayContent: vi.fn(async (content) => {
      const message = {
        id: `overlay-${overlayState.messages.length}`,
        speaker: "Rei" as const,
        text: content.text,
        source: content.source ?? "assistant_reply",
        timestamp: content.timestamp ?? new Date().toISOString()
      };
      overlayState = {
        ...overlayState,
        messages: [...overlayState.messages, message].slice(-overlayState.max_messages),
        updated_at: message.timestamp
      };
      for (const listener of overlayListeners) listener(overlayState);
      return overlayState;
    }),
    onBackendStatus: vi.fn((callback: (nextStatus: BackendRuntimeStatus) => void) => {
      listeners.add(callback);
      return () => listeners.delete(callback);
    }),
    onOverlayState: vi.fn((callback: (nextState: typeof overlayState) => void) => {
      overlayListeners.add(callback);
      return () => overlayListeners.delete(callback);
    })
  };
  Object.defineProperty(window, "reilinkRuntime", {
    configurable: true,
    value: bridge
  });
  return {
    bridge,
    emit: (nextStatus: BackendRuntimeStatus) => {
      status = nextStatus;
      for (const listener of listeners) listener(status);
    }
  };
};

const setChatScroll = (
  element: HTMLElement,
  values: { scrollHeight: number; clientHeight: number; scrollTop: number }
) => {
  Object.defineProperty(element, "scrollHeight", { configurable: true, value: values.scrollHeight });
  Object.defineProperty(element, "clientHeight", { configurable: true, value: values.clientHeight });
  Object.defineProperty(element, "scrollTop", { configurable: true, writable: true, value: values.scrollTop });
  fireEvent.scroll(element);
};

const resetSettingsResponse = () => {
  appSettingsStore = { ...appSettings };
  localAsrStatusStore = { ...localAsrStatus };
  localAsrSettingsStore = { ...localAsrSettings };
  localAsrProbeResponseStore = { ...localAsrProbeResponse };
  audioProbeResponseStore = { ...audioProbeResponse };
  localAsrTranscriptionResponseStore = { ...localAsrTranscriptionResponse };
  gameContextStore = { ...gameContext };
  proactiveStatusStore = { ...proactiveStatus };
  setupStatusStore = { ...setupStatus };
  chatFailureResponse = null;
  omitVoiceOutputFromSettings = false;
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

const setLocalAsrReady = () => {
  localAsrStatusStore = {
    ...localAsrStatus,
    status: "local_asr_ready",
    available: true,
    binary_configured: true,
    binary_present: true,
    binary_executable: true,
    model_configured: true,
    model_present: true,
    display_message: "本地语音识别配置已就绪",
    safe_binary_name: "whisper-cli",
    safe_model_name: "ggml-base.bin",
    converter_configured: true,
    safe_converter_name: "ffmpeg",
    source: "user_settings"
  };
  localAsrSettingsStore = {
    ...localAsrSettings,
    configured: true,
    binary_configured: true,
    model_configured: true,
    converter_configured: true,
    safe_binary_name: "whisper-cli",
    safe_model_name: "ggml-base.bin",
    safe_converter_name: "ffmpeg",
    source: "user_settings"
  };
};

const setupStatusResponse = (url: string) => {
  if (url.endsWith("/api/setup/status")) return Response.json(setupStatusStore);
  return null;
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
  const settingsPayload = () => {
    if (!omitVoiceOutputFromSettings) return appSettingsStore;
    const legacySettings = { ...appSettingsStore } as Partial<AppSettings>;
    delete legacySettings.voice_output;
    delete legacySettings.voice_rate;
    delete legacySettings.voice_volume;
    return legacySettings;
  };

  if (url.endsWith("/api/settings") && init?.method === "POST") {
    appSettingsStore = { ...appSettingsStore, ...JSON.parse(String(init.body ?? "{}")) };
    return Response.json(settingsPayload());
  }
  if (url.endsWith("/api/settings")) return Response.json(settingsPayload());
  return null;
};

const safePathName = (value: unknown) => {
  if (typeof value !== "string" || !value.trim()) return null;
  return value.trim().split(/[\\/]/).filter(Boolean).pop() ?? "已配置";
};

const localAsrSettingsResponse = (url: string, init?: RequestInit) => {
  if (url.endsWith("/api/voice-input/local-asr/settings") && init?.method === "PUT") {
    const body = JSON.parse(String(init.body ?? "{}")) as {
      local_asr_binary_path?: string | null;
      local_asr_model_path?: string | null;
      audio_converter_binary_path?: string | null;
    };
    const safeBinaryName = safePathName(body.local_asr_binary_path) ?? localAsrSettingsStore.safe_binary_name;
    const safeModelName = safePathName(body.local_asr_model_path) ?? localAsrSettingsStore.safe_model_name;
    const safeConverterName = safePathName(body.audio_converter_binary_path) ?? localAsrSettingsStore.safe_converter_name;
    localAsrSettingsStore = {
      configured: Boolean(safeBinaryName && safeModelName),
      binary_configured: Boolean(safeBinaryName),
      model_configured: Boolean(safeModelName),
      converter_configured: Boolean(safeConverterName),
      safe_binary_name: safeBinaryName,
      safe_model_name: safeModelName,
      safe_converter_name: safeConverterName,
      source: safeBinaryName || safeModelName || safeConverterName ? "user_settings" : "none"
    };
    localAsrStatusStore = {
      ...localAsrStatusStore,
      status: safeBinaryName && safeModelName ? "local_asr_ready" : "local_asr_not_configured",
      available: Boolean(safeBinaryName && safeModelName),
      binary_configured: Boolean(safeBinaryName),
      binary_present: Boolean(safeBinaryName),
      binary_executable: Boolean(safeBinaryName),
      model_configured: Boolean(safeModelName),
      model_present: Boolean(safeModelName),
      converter_configured: Boolean(safeConverterName),
      safe_binary_name: safeBinaryName,
      safe_model_name: safeModelName,
      safe_converter_name: safeConverterName,
      source: localAsrSettingsStore.source,
      display_message: safeBinaryName && safeModelName ? "本地语音识别配置已就绪" : "本地语音识别未配置"
    };
    return Response.json(localAsrSettingsStore);
  }
  if (url.endsWith("/api/voice-input/local-asr/settings") && init?.method === "DELETE") {
    localAsrSettingsStore = { ...localAsrSettings };
    localAsrStatusStore = { ...localAsrStatus };
    return Response.json(localAsrSettingsStore);
  }
  if (url.endsWith("/api/voice-input/local-asr/settings")) return Response.json(localAsrSettingsStore);
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
  if (url.endsWith("/api/proactive/reset") && init?.method === "POST") {
    proactiveStatusStore = {
      ...proactiveStatusStore,
      last_triggered_at: null,
      last_triggered_type: "none",
      requires_user_activity_after_proactive: false,
      cooldown_remaining_seconds: 0,
      last_trigger_reason: null
    };
    return Response.json({ status: "reset", ...proactiveStatusStore });
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
let chatResponseStore = { ...chatResponse };

const defaultFetchResponse = async (url: string, init?: RequestInit) => {
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
  const setup = setupStatusResponse(url);
  if (setup) return setup;
  const localAsrSettingsValue = localAsrSettingsResponse(url, init);
  if (localAsrSettingsValue) return localAsrSettingsValue;
  if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
  if (url.endsWith("/api/local-data/status")) return Response.json(localDataStatus);
  if (url.endsWith("/api/voice-input/local-asr/status")) return Response.json(localAsrStatusStore);
  if (url.endsWith("/api/voice-input/local-asr/probe") && init?.method === "POST") {
    return Response.json(localAsrProbeResponseStore);
  }
  if (url.endsWith("/api/voice-input/audio/probe") && init?.method === "POST") {
    return Response.json(audioProbeResponseStore);
  }
  if (url.endsWith("/api/voice-input/local-asr/transcribe") && init?.method === "POST") {
    return Response.json(localAsrTranscriptionResponseStore);
  }
  if (url.endsWith("/api/game/status")) return Response.json(runningStatus);
  if (url.endsWith("/api/game/detected")) return Response.json(gameDetection);
  if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
  if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
  if (url.endsWith("/api/debug/chat")) return Response.json(chatDebug);
  if (url.endsWith("/api/debug/provider")) return Response.json(providerDebug);
  if (url.endsWith("/api/debug/game-session")) return Response.json(gameSessionDebug);
  if (url.endsWith("/api/debug/semantic-extraction/latest")) return Response.json(semanticExtractionDebug);
  if (url.includes("/api/debug/semantic-shadow/events")) return Response.json({ events: [], latest_id: 0 });
  if (url.includes("/api/debug/prompt-preview")) return Response.json(promptPreview);
  if (url.endsWith("/api/chat") && init?.method === "POST") {
    if (chatFailureResponse) return chatFailureResponse();
    return Response.json(chatResponseStore);
  }
  return new Response("missing", { status: 404 });
};

describe("App", () => {
  beforeEach(() => {
    let uuid = 0;
    resetSettingsResponse();
    chatResponseStore = { ...chatResponse };
    eventBus.clear();
    scrollToMock = vi.fn(function (this: HTMLElement, options?: ScrollToOptions | number) {
      const top = typeof options === "number" ? options : options?.top;
      if (typeof top === "number") {
        Object.defineProperty(this, "scrollTop", { configurable: true, writable: true, value: top });
      }
    });
    Object.defineProperty(HTMLElement.prototype, "scrollTo", {
      configurable: true,
      writable: true,
      value: scrollToMock
    });
    vi.stubGlobal("crypto", { randomUUID: () => `test-id-${uuid++}` });
    vi.stubGlobal("fetch", vi.fn(defaultFetchResponse));
  });

  afterEach(() => {
    vi.useRealTimers();
    audioCapture.resetForTest();
    voiceInput.resetForTest();
    voiceOutput.resetForTest();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    Reflect.deleteProperty(window, "SpeechRecognition");
    Reflect.deleteProperty(window, "webkitSpeechRecognition");
    Reflect.deleteProperty(window, "reilinkRuntime");
    Reflect.deleteProperty(window, "MediaRecorder");
    Reflect.deleteProperty(navigator, "mediaDevices");
    Reflect.deleteProperty(navigator, "permissions");
    eventBus.clear();
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
    const overlayToggle = screen.getByRole("group", { name: "Overlay / 游戏悬浮层" });
    expect(within(overlayToggle).getByRole("button", { name: "关闭 Overlay" })).toHaveAttribute("aria-pressed", "true");
    expect(within(overlayToggle).getByRole("button", { name: "开启 Overlay" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "强制关闭悬浮层" })).toBeInTheDocument();
    expect(screen.getByLabelText("Overlay 位置预设")).toHaveValue("middle-right");
    expect(screen.getByLabelText("Overlay 背景透明度")).toHaveValue("0.72");
    expect(screen.getByLabelText("Overlay 显示消息数量")).toHaveValue("2");
    expect(screen.getByText("默认关闭。开启后只保存设置，ReiLink 前台时不显示，避免遮挡 Settings。")).toBeInTheDocument();
    expect(screen.getByText("macOS 当前为安全模式：自动显示小气泡暂时关闭，以避免抢焦点或影响窗口切换。")).toBeInTheDocument();
    expect(screen.getByText("强制关闭用于异常时立即关闭悬浮层；不显示调试信息、路径、密钥或完整回复。")).toBeInTheDocument();
    expect(screen.getByLabelText("语音输出 / Voice Output")).toHaveValue("off");
    expect(screen.getByText(/当前状态：已关闭/)).toBeInTheDocument();
    expect(screen.getByText(/本地语音：不可用/)).toBeInTheDocument();
    expect(screen.getByText(/播放状态：当前环境不支持本地语音输出/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "测试语音 / Test Voice" })).toBeDisabled();
    expect(screen.getByLabelText("语速 / Rate")).toHaveValue("1");
    expect(screen.getByLabelText("音量 / Volume")).toHaveValue("1");
    expect(screen.getByLabelText("自动启动本地后端")).toHaveValue("on");
    expect(screen.getByLabelText("自动启动本地后端")).toBeDisabled();
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
    const providerStatusPanel = screen.getByRole("group", { name: "模型服务状态" });
    expect(within(providerStatusPanel).getByText("模型服务")).toBeInTheDocument();
    expect(within(providerStatusPanel).getByText("DeepSeek")).toBeInTheDocument();
    expect(within(providerStatusPanel).getByText("本地后端")).toBeInTheDocument();
    expect(within(providerStatusPanel).getByText("后端已连接")).toBeInTheDocument();
    expect(within(providerStatusPanel).getByText("API Key")).toBeInTheDocument();
    expect(within(providerStatusPanel).getByText("已加载")).toBeInTheDocument();
    expect(within(providerStatusPanel).getByText("Base URL")).toBeInTheDocument();
    expect(within(providerStatusPanel).getByText("https://api.deepseek.com")).toBeInTheDocument();
    expect(within(providerStatusPanel).getByText("auto")).toBeInTheDocument();
    expect(within(providerStatusPanel).getByText("deepseek-v4-flash")).toBeInTheDocument();
    expect(within(providerStatusPanel).getByText("deepseek-v4-pro")).toBeInTheDocument();
    const onboardingSettings = screen.getByRole("group", { name: "新手引导设置" });
    expect(within(onboardingSettings).getByText("已完成")).toBeInTheDocument();
    expect(within(onboardingSettings).getByRole("button", { name: "新手引导：重新查看" })).toBeInTheDocument();
    const demoResetPanel = screen.getByRole("group", { name: "本地数据" });
    expect(within(demoResetPanel).getByText("Local Data")).toBeInTheDocument();
    expect(within(demoResetPanel).getByText("用户数据目录")).toBeInTheDocument();
    expect(within(demoResetPanel).getAllByText("/Users/aragoto/Library/Application Support/ReiLink/data").length).toBeGreaterThan(0);
    expect(within(demoResetPanel).getByText("记忆目录")).toBeInTheDocument();
    expect(within(demoResetPanel).getByText("会话目录")).toBeInTheDocument();
    expect(within(demoResetPanel).getByText("设置目录")).toBeInTheDocument();
    expect(within(demoResetPanel).getByText("日志目录")).toBeInTheDocument();
    expect(within(demoResetPanel).getByText("内置知识资源")).toBeInTheDocument();
    expect(within(demoResetPanel).getByText("可写")).toBeInTheDocument();
    expect(within(demoResetPanel).getByText("待确认记忆数")).toBeInTheDocument();
    expect(within(demoResetPanel).getByText("记忆文件数")).toBeInTheDocument();
    expect(within(demoResetPanel).getByText("会话文件数")).toBeInTheDocument();
    expect(within(demoResetPanel).getByRole("button", { name: "打开本地数据目录" })).toBeInTheDocument();
    expect(within(demoResetPanel).getByRole("button", { name: "重置新手引导" })).toBeInTheDocument();
    expect(within(demoResetPanel).getByRole("button", { name: "清空聊天记录" })).toBeInTheDocument();
    expect(within(demoResetPanel).getByRole("button", { name: "清空会话状态" })).toBeInTheDocument();
    expect(within(demoResetPanel).getByRole("button", { name: "清空待确认记忆" })).toBeInTheDocument();
    expect(within(demoResetPanel).getByRole("button", { name: "重置长期记忆" })).toBeInTheDocument();
    expect(within(demoResetPanel).getByRole("button", { name: "重置主动陪伴状态" })).toBeInTheDocument();
    expect(within(demoResetPanel).getByRole("button", { name: "重置演示状态" })).toBeInTheDocument();
    expect(screen.getByText(/自动游戏检测当前为开启/)).toBeInTheDocument();
  });

  it("shows backend runtime startup status from Electron", async () => {
    installRuntimeBridge({
      ...backendRuntimeStatus,
      backend_started_by_app: true,
      backend_started_from: "repo",
      backend_status: "starting"
    });
    vi.stubGlobal("fetch", vi.fn(async () => new Response("offline", { status: 500 })));

    render(<App />);

    expect(await screen.findByRole("status", { name: "后端状态提示" })).toHaveTextContent("正在启动本地后端");
    expect(screen.getByText("ReiLink 正在尝试启动本地 FastAPI backend。")).toBeInTheDocument();
  });

  it("shows a clear Chinese error when backend auto-start fails", async () => {
    installRuntimeBridge({
      ...backendRuntimeStatus,
      backend_start_error: "本地后端启动失败，请在项目目录运行 make dev-backend。",
      backend_status: "failed"
    });
    vi.stubGlobal("fetch", vi.fn(async () => new Response("offline", { status: 500 })));

    render(<App />);

    const notice = await screen.findByRole("status", { name: "后端状态提示" });
    expect(notice).toHaveTextContent("后端启动失败");
    expect(notice).toHaveTextContent("本地后端启动失败，请在项目目录运行 make dev-backend。");
  });

  it("lets settings disable backend auto-start", async () => {
    const runtime = installRuntimeBridge(backendRuntimeStatus);
    render(<App />);

    const select = await screen.findByLabelText("自动启动本地后端");
    expect(select).toBeEnabled();
    await userEvent.selectOptions(select, "off");

    await waitFor(() => expect(runtime.bridge.setBackendAutoStart).toHaveBeenCalledWith(false));
    expect(screen.getByLabelText("自动启动本地后端")).toHaveValue("off");
  });

  it("syncs the Overlay setting through the Electron runtime bridge", async () => {
    const runtime = installRuntimeBridge(backendRuntimeStatus);
    render(<App />);

    await waitFor(() => expect(runtime.bridge.setOverlayEnabled).toHaveBeenCalledWith(false));
    vi.mocked(runtime.bridge.setOverlayEnabled).mockClear();

    const overlayToggle = await screen.findByRole("group", { name: "Overlay / 游戏悬浮层" });
    await userEvent.click(within(overlayToggle).getByRole("button", { name: "开启 Overlay" }));

    await waitFor(() => expect(runtime.bridge.setOverlayEnabled).toHaveBeenCalledWith(true));
    expect(within(overlayToggle).getByRole("button", { name: "开启 Overlay" })).toHaveAttribute("aria-pressed", "true");
    expect(eventBus.getRecentEvents().some((event) => event.type === "overlay_enabled_changed")).toBe(true);
    expect(eventBus.getRecentEvents().some((event) => event.type === "overlay_visibility_suppressed")).toBe(true);
    await userEvent.click(screen.getByRole("button", { name: "强制关闭悬浮层" }));
    await waitFor(() => expect(runtime.bridge.setOverlayEnabled).toHaveBeenCalledWith(false));
    expect(within(overlayToggle).getByRole("button", { name: "关闭 Overlay" })).toHaveAttribute("aria-pressed", "true");
  });

  it("syncs Overlay position, opacity, and message count settings", async () => {
    const runtime = installRuntimeBridge(backendRuntimeStatus);
    render(<App />);

    await waitFor(() =>
      expect(runtime.bridge.setOverlayConfig).toHaveBeenCalledWith({
        position: "middle-right",
        opacity: 0.72,
        max_messages: 2
      })
    );
    vi.mocked(runtime.bridge.setOverlayConfig).mockClear();

    await userEvent.selectOptions(await screen.findByLabelText("Overlay 位置预设"), "bottom-left");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ overlay_position: "bottom-left" }) })
      )
    );
    await waitFor(() =>
      expect(runtime.bridge.setOverlayConfig).toHaveBeenLastCalledWith({
        position: "bottom-left",
        opacity: 0.72,
        max_messages: 2
      })
    );

    fireEvent.change(screen.getByLabelText("Overlay 背景透明度"), { target: { value: "0.85" } });
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ overlay_opacity: 0.85 }) })
      )
    );
    await waitFor(() =>
      expect(runtime.bridge.setOverlayConfig).toHaveBeenLastCalledWith({
        position: "bottom-left",
        opacity: 0.85,
        max_messages: 2
      })
    );

    await userEvent.selectOptions(screen.getByLabelText("Overlay 显示消息数量"), "1");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ overlay_message_count: 1 }) })
      )
    );
    await waitFor(() =>
      expect(runtime.bridge.setOverlayConfig).toHaveBeenLastCalledWith({
        position: "bottom-left",
        opacity: 0.85,
        max_messages: 1
      })
    );
    expect(screen.getByLabelText("Overlay 位置预设")).toHaveValue("bottom-left");
    expect(screen.getByLabelText("Overlay 显示消息数量")).toHaveValue("1");
    expect(eventBus.getRecentEvents().some((event) => event.type === "overlay_settings_changed")).toBe(true);
    expect(eventBus.getRecentEvents().some((event) => event.type === "overlay_window_moved")).toBe(true);
  });

  it("sends only a sanitized short assistant summary to Overlay", async () => {
    appSettingsStore = { ...appSettingsStore, overlay_enabled: "on" };
    chatResponseStore = {
      ...chatResponse,
      reply: "这是一条很长的回复，包含 /Users/aragoto/Desktop/ReiLink/services/backend/.env 和 API key，还有后面很多很多不该完整显示的文字。先停一下，看动作，再试一次。继续观察距离、翻滚时机、精力条、走位和节奏，这些内容都不应该完整塞进悬浮层。继续追加很多很多很多很多很多很多很多安全但冗长的内容。",
      reply_segments: [
        "这是一条很长的回复，包含 /Users/aragoto/Desktop/ReiLink/services/backend/.env 和 API key，还有后面很多很多不该完整显示的文字。先停一下，看动作，再试一次。继续观察距离、翻滚时机、精力条、走位和节奏，这些内容都不应该完整塞进悬浮层。继续追加很多很多很多很多很多很多很多安全但冗长的内容。"
      ]
    };
    const runtime = installRuntimeBridge(backendRuntimeStatus);
    render(<App />);

    await waitFor(() => expect(runtime.bridge.setOverlayEnabled).toHaveBeenCalledWith(true));
    await userEvent.type(await screen.findByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));

    await waitFor(() => expect(runtime.bridge.updateOverlayContent).toHaveBeenCalled());
    const content = vi.mocked(runtime.bridge.updateOverlayContent).mock.calls.at(-1)?.[0];
    expect(content?.text.length).toBeLessThanOrEqual(96);
    expect(content?.text).toContain("…");
    expect(content?.text).not.toContain("/Users/aragoto");
    expect(content?.text).not.toContain(".env");
    expect(content?.text).not.toContain("API key");
    expect(eventBus.getRecentEvents().some((event) =>
      event.type === "overlay_content_updated" &&
      event.character_count <= 96 &&
      event.message_count === 1
    )).toBe(true);
  });

  it("opens the local data directory through the runtime bridge", async () => {
    const runtime = installRuntimeBridge(backendRuntimeStatus);
    render(<App />);

    const localDataPanel = await screen.findByRole("group", { name: "本地数据" });
    const openButton = within(localDataPanel).getByRole("button", { name: "打开本地数据目录" });
    await waitFor(() => expect(openButton).toBeEnabled());
    await userEvent.click(openButton);

    await waitFor(() => expect(runtime.bridge.openLocalDataDir).toHaveBeenCalledTimes(1));
    expect(screen.getByText("已打开本地数据目录")).toBeInTheDocument();
  });

  it("keeps the debug panel last in the right rail", async () => {
    render(<App />);

    await screen.findByRole("complementary", { name: "信息侧栏" });
    const orderOf = (id: string) => Number(window.getComputedStyle(document.getElementById(id) as HTMLElement).order);
    expect(orderOf("settings-panel")).toBe(1);
    expect(orderOf("pending-memory-panel")).toBe(2);
    expect(orderOf("game-session-panel")).toBe(3);
    expect(orderOf("prompt-preview-panel")).toBe(4);
    expect(orderOf("debug-panel")).toBe(5);
  });

  it("shows onboarding card when onboarding is incomplete", async () => {
    appSettingsStore = { ...appSettings, onboarding_completed: false, onboarding_last_seen_at: null };

    render(<App />);

    expect(await screen.findByRole("region", { name: "新手引导" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "快速开始 ReiLink" })).toBeInTheDocument();
    expect(screen.getByText("当前 DeepSeek API Key 已加载。")).toBeInTheDocument();
    expect(screen.getByText("可以让 ReiLink 自动检测，也可以手动选择当前游戏。")).toBeInTheDocument();
    expect(screen.getByText("ReiLink 不会直接写入长期记忆，需要你手动保存。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开始使用" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "打开设置" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看 Demo 文档" })).toBeInTheDocument();
  });

  it("hides onboarding after start and only persists app settings", async () => {
    appSettingsStore = { ...appSettings, onboarding_completed: false, onboarding_last_seen_at: null };

    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "开始使用" }));

    await waitFor(() => expect(screen.queryByRole("region", { name: "新手引导" })).not.toBeInTheDocument());
    expect(appSettingsStore.onboarding_completed).toBe(true);
    expect(appSettingsStore.onboarding_last_seen_at).toEqual(expect.any(String));
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/settings"),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining("\"onboarding_completed\":true")
      })
    );
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/memory/pending"),
      expect.objectContaining({ method: "POST" })
    );
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/game/context/manual"),
      expect.objectContaining({ method: "POST" })
    );
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/debug/game-session/reset"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("reopens onboarding from settings", async () => {
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "新手引导：重新查看" }));

    expect(screen.getByRole("region", { name: "新手引导" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "查看 Demo 文档" }));
    expect(screen.getByText("Demo 文档在本地仓库：docs/DEMO_SCRIPT.md")).toBeInTheDocument();
  });

  it("resets onboarding from demo reset controls", async () => {
    render(<App />);

    const demoResetPanel = await screen.findByRole("group", { name: "本地数据" });
    await userEvent.click(within(demoResetPanel).getByRole("button", { name: "重置新手引导" }));

    await waitFor(() => expect(appSettingsStore.onboarding_completed).toBe(false));
    expect(appSettingsStore.onboarding_last_seen_at).toBeNull();
    expect(screen.getByRole("region", { name: "新手引导" })).toBeInTheDocument();
    expect(screen.getByText("已恢复新手引导")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/settings"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ onboarding_completed: false, onboarding_last_seen_at: null })
      })
    );
  });

  it("runs demo reset actions with confirmation where needed", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<App />);

    const demoResetPanel = await screen.findByRole("group", { name: "本地数据" });
    await userEvent.click(within(demoResetPanel).getByRole("button", { name: "清空会话状态" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/debug/game-session/reset"),
        expect.objectContaining({ method: "POST" })
      )
    );
    expect(screen.getByText("已清空会话状态")).toBeInTheDocument();

    await userEvent.click(within(demoResetPanel).getByRole("button", { name: "清空待确认记忆" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/memory/pending/clear"),
        expect.objectContaining({ method: "POST" })
      )
    );

    await userEvent.click(within(demoResetPanel).getByRole("button", { name: "重置主动陪伴状态" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/proactive/reset"),
        expect.objectContaining({ method: "POST" })
      )
    );

    await userEvent.click(within(demoResetPanel).getByRole("button", { name: "重置长期记忆" }));
    expect(confirm).toHaveBeenCalledWith("这会清空本地记忆，无法撤销。确定继续吗？");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/memory/reset"),
        expect.objectContaining({ method: "POST" })
      )
    );
  });

  it("clears the current chat session without touching memory", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<App />);

    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("Margit 怎么打？");
    await screen.findByText("别急着翻滚。先看动作。再试一次。");

    const demoResetPanel = screen.getByRole("group", { name: "本地数据" });
    await userEvent.click(within(demoResetPanel).getByRole("button", { name: "清空聊天记录" }));

    await waitFor(() => expect(screen.queryByText("Margit 怎么打？")).not.toBeInTheDocument());
    expect(screen.queryByText("我在。想问的时候就说。")).not.toBeInTheDocument();
    expect(screen.getByText("已清空当前聊天记录")).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/memory/reset"),
      expect.objectContaining({ method: "POST" })
    );
    await userEvent.type(screen.getByLabelText("聊天输入"), "还能用吗");
    expect(screen.getByLabelText("聊天输入")).toHaveValue("还能用吗");
  });

  it("cancels dangerous demo reset actions when confirmation is rejected", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<App />);

    const demoResetPanel = await screen.findByRole("group", { name: "本地数据" });
    await userEvent.click(within(demoResetPanel).getByRole("button", { name: "重置长期记忆" }));
    await userEvent.click(within(demoResetPanel).getByRole("button", { name: "重置演示状态" }));

    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/memory/reset"),
      expect.objectContaining({ method: "POST" })
    );
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/debug/game-session/reset"),
      expect.objectContaining({ method: "POST" })
    );
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/proactive/reset"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("one-click reset prepares demo state without clearing long-term memory", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<App />);

    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("Margit 怎么打？");

    const demoResetPanel = screen.getByRole("group", { name: "本地数据" });
    await userEvent.click(within(demoResetPanel).getByRole("button", { name: "重置演示状态" }));

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/debug/game-session/reset"),
        expect.objectContaining({ method: "POST" })
      )
    );
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/memory/pending/clear"),
      expect.objectContaining({ method: "POST" })
    );
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/proactive/reset"),
      expect.objectContaining({ method: "POST" })
    );
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/settings"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ onboarding_completed: false, onboarding_last_seen_at: null })
      })
    );
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/memory/reset"),
      expect.objectContaining({ method: "POST" })
    );
    expect(screen.queryByText("Margit 怎么打？")).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "新手引导" })).toBeInTheDocument();
    expect(screen.getByText("已重置演示状态（未清空长期记忆）")).toBeInTheDocument();
  });

  it("shows first-run provider setup prompt when the API key is missing", async () => {
    setupStatusStore = {
      ...setupStatus,
      provider_configured: false,
      api_key_loaded: false,
      needs_setup: true,
      missing_items: ["DEEPSEEK_API_KEY"]
    };

    render(<App />);

    expect(await screen.findByText("需要完成模型配置")).toBeInTheDocument();
    expect(screen.getByText("ReiLink 需要 DeepSeek API Key 才能生成回复。请在本地 .env 中配置，或进入设置查看配置状态。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /打开设置/i })).toBeEnabled();
    await userEvent.click(screen.getByRole("button", { name: /打开设置/i }));
    expect(screen.getByLabelText("人格模式")).toHaveFocus();
    await userEvent.click(screen.getByRole("button", { name: /查看配置说明/i }));
    expect(screen.getByText(/LLM_PROVIDER=deepseek/)).toBeInTheDocument();
    expect(screen.getByText(/DEEPSEEK_API_KEY=/)).toBeInTheDocument();
    const providerStatusPanel = screen.getByRole("group", { name: "模型服务状态" });
    expect(within(providerStatusPanel).getByText("未配置")).toBeInTheDocument();
  });

  it("keeps provider setup before onboarding when the API key is missing", async () => {
    appSettingsStore = { ...appSettings, onboarding_completed: false, onboarding_last_seen_at: null };
    setupStatusStore = {
      ...setupStatus,
      provider_configured: false,
      api_key_loaded: false,
      needs_setup: true,
      missing_items: ["DEEPSEEK_API_KEY"]
    };

    render(<App />);

    const setupPrompt = await screen.findByLabelText("模型配置提示");
    const onboarding = screen.getByLabelText("新手引导");
    expect(setupPrompt.compareDocumentPosition(onboarding) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText("当前 API Key 未配置，请先完成模型配置。")).toBeInTheDocument();
  });

  it("updates settings through the API", async () => {
    installSpeechSynthesisMock();
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

    await userEvent.click(
      within(screen.getByRole("group", { name: "Overlay / 游戏悬浮层" })).getByRole("button", { name: "开启 Overlay" })
    );
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ overlay_enabled: "on" }) })
      )
    );

    await userEvent.selectOptions(screen.getByLabelText("语音输出 / Voice Output"), "on");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ voice_output: "on" }) })
      )
    );

    fireEvent.change(screen.getByLabelText("语速 / Rate"), { target: { value: "1.2" } });
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ voice_rate: 1.2 }) })
      )
    );

    fireEvent.change(screen.getByLabelText("音量 / Volume"), { target: { value: "0.6" } });
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ voice_volume: 0.6 }) })
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

  it("emits interaction events for sent messages and shown assistant segments", async () => {
    render(<App />);
    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");

    const events = eventBus.getRecentEvents(20);
    expect(events).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: "user_message_sent", text: "Margit 怎么打？" }),
        expect.objectContaining({ type: "assistant_reply_started" }),
        expect.objectContaining({
          type: "assistant_reply_segment_shown",
          segment_index: 0,
          text: "别急着翻滚。先看动作。再试一次。"
        }),
        expect.objectContaining({ type: "assistant_reply_completed" })
      ])
    );
  });

  it("emits observable semantic trace events for low-confidence no-op game hints", async () => {
    const lowConfidenceTrace = {
      ...semanticExtractionDebug,
      latest_user_message: "低置信游戏语义 / 18 字",
      rule_result: { game_event: { type: "none" } },
      rule_confidence: 0,
      raw_rule_confidence: 0,
      ambiguity_detected: true,
      fallback_reason: "unknown_boss_alias",
      source: "none",
      confidence: "low",
      applied_updates: [],
      extraction_trace: {
        source: "none",
        confidence: "low",
        fallback_reason: "unknown_boss_alias",
        skip_reason: "provider_unavailable",
        parse_error: null,
        applied_updates: [],
        llm_shadow_status: "skipped",
        llm_shadow_confidence: "low",
        llm_shadow_summary: "跳过：provider_unavailable",
        llm_shadow_diff: "LLM 影子识别未运行"
      },
      llm_called: false,
      semantic_extraction_model: null,
      semantic_extraction_latency_ms: 0,
      provider_latency_ms: 0,
      llm_result: null,
      llm_shadow: {
        status: "skipped",
        confidence: "low",
        candidate_summary: "跳过：provider_unavailable",
        diff_summary: "LLM 影子识别未运行"
      },
      llm_shadow_status: "skipped",
      llm_shadow_confidence: "low",
      llm_shadow_summary: "跳过：provider_unavailable",
      llm_shadow_diff: "LLM 影子识别未运行",
      final_decision: { game_event: { type: "none" } },
      skip_reason: "provider_unavailable",
      parse_error: null
    };
    vi.mocked(fetch).mockImplementation((input: URL | RequestInfo, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (url.endsWith("/api/debug/semantic-extraction/latest")) return Promise.resolve(Response.json(lowConfidenceTrace));
      return defaultFetchResponse(url, init);
    });

    render(<App />);
    await userEvent.type(screen.getByLabelText("聊天输入"), "我在那个骑马金甲大哥那里又寄了几次。");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");

    await waitFor(() =>
      expect(eventBus.getRecentEvents(20)).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            type: "semantic_extraction_traced",
            source: "none",
            confidence: "low",
            fallback_reason: "unknown_boss_alias",
            skip_reason: "provider_unavailable",
            applied_updates: [],
            llm_shadow_status: "skipped",
            llm_shadow_summary: "跳过：provider_unavailable"
          })
        ])
      )
    );
    const semanticEvent = eventBus.getRecentEvents(20).find((event) => event.type === "semantic_extraction_traced");
    expect(JSON.stringify(semanticEvent)).not.toContain("骑马金甲大哥");
  });

  it("emits safe LLM shadow semantic summaries without applying state", async () => {
    const shadowTrace = {
      ...semanticExtractionDebug,
      latest_user_message: "低置信游戏语义 / 18 字",
      rule_result: { game_event: { type: "none" } },
      rule_confidence: 0,
      raw_rule_confidence: 0,
      ambiguity_detected: true,
      fallback_reason: "unknown_boss_alias",
      source: "none",
      confidence: "low",
      applied_updates: [],
      extraction_trace: {
        source: "none",
        confidence: "low",
        fallback_reason: "unknown_boss_alias",
        skip_reason: null,
        parse_error: null,
        applied_updates: [],
        llm_shadow_status: "succeeded",
        llm_shadow_confidence: "medium",
        llm_shadow_summary: "Boss 候选：大树守卫 / 失败次数候选：increment 2",
        llm_shadow_diff: "规则未识别，LLM 认为可能是 大树守卫"
      },
      llm_called: true,
      semantic_extraction_model: "deepseek-v4-flash",
      semantic_extraction_latency_ms: 38,
      provider_latency_ms: 38,
      llm_result: null,
      llm_shadow: {
        status: "succeeded",
        confidence: "medium",
        candidate_summary: "Boss 候选：大树守卫 / 失败次数候选：increment 2",
        diff_summary: "规则未识别，LLM 认为可能是 大树守卫"
      },
      llm_shadow_status: "succeeded",
      llm_shadow_confidence: "medium",
      llm_shadow_summary: "Boss 候选：大树守卫 / 失败次数候选：increment 2",
      llm_shadow_diff: "规则未识别，LLM 认为可能是 大树守卫",
      final_decision: { game_event: { type: "none" } },
      skip_reason: null,
      parse_error: null
    };
    vi.mocked(fetch).mockImplementation((input: URL | RequestInfo, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (url.endsWith("/api/debug/semantic-extraction/latest")) return Promise.resolve(Response.json(shadowTrace));
      return defaultFetchResponse(url, init);
    });

    render(<App />);
    await userEvent.type(screen.getByLabelText("聊天输入"), "我在那个骑马金甲大哥那里又寄了几次。");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");

    await waitFor(() =>
      expect(eventBus.getRecentEvents(20)).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            type: "semantic_extraction_traced",
            source: "none",
            llm_shadow_status: "succeeded",
            llm_shadow_summary: "Boss 候选：大树守卫 / 失败次数候选：increment 2",
            applied_updates: []
          })
        ])
      )
    );
    const semanticEvent = eventBus.getRecentEvents(20).find((event) => event.type === "semantic_extraction_traced");
    expect(JSON.stringify(semanticEvent)).toContain("大树守卫");
    expect(JSON.stringify(semanticEvent)).not.toContain("骑马金甲大哥");
  });

  it("polls background LLM shadow final events into Event Stream without raw text", async () => {
    const finalShadowEvent = {
      id: 1,
      trace_id: "shadow#1",
      timestamp: new Date().toISOString(),
      phase: "final",
      status: "shadow_timeout",
      source: "none",
      confidence: "low",
      fallback_reason: "unknown_boss_alias",
      skip_reason: null,
      parse_error: "semantic_extraction_timeout",
      applied_updates: [],
      llm_shadow_status: "failed",
      llm_shadow_confidence: "low",
      llm_shadow_summary: "LLM 影子识别超时",
      llm_shadow_diff: "LLM 影子识别失败，未应用状态",
      semantic_extraction_model: "deepseek-v4-flash",
      semantic_extraction_latency_ms: 12000
    };
    let servedShadowEvent = false;
    vi.mocked(fetch).mockImplementation((input: URL | RequestInfo, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (url.includes("/api/debug/semantic-shadow/events")) {
        const events = servedShadowEvent ? [] : [finalShadowEvent];
        servedShadowEvent = true;
        return Promise.resolve(Response.json({ events, latest_id: 1 }));
      }
      return defaultFetchResponse(url, init);
    });

    render(<App />);

    await waitFor(() =>
      expect(eventBus.getRecentEvents(20)).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            type: "semantic_extraction_traced",
            source: "none",
            shadow_event_status: "shadow_timeout",
            llm_shadow_status: "failed",
            applied_updates: []
          })
        ])
      )
    );
    fireEvent.click(screen.getByText("事件流 / Event Stream"));
    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    await waitFor(() => expect(eventStream).toHaveTextContent("LLM 影子识别超时"));
    const serialized = JSON.stringify(eventBus.getRecentEvents(20));
    expect(serialized).not.toContain("骑马金甲大哥");
    expect(serialized).not.toContain("raw prompt");
    expect(serialized).not.toContain(".env");
  });

  it("does not speak assistant replies when Voice Output is disabled", async () => {
    const speech = installSpeechSynthesisMock();
    render(<App />);

    await screen.findByLabelText("语音输出 / Voice Output");
    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");

    expect(speech.speak).not.toHaveBeenCalled();
    expect(eventBus.getRecentEvents(20)).not.toEqual(expect.arrayContaining([expect.objectContaining({ type: "tts_started" })]));
  });

  it("does not crash and shows a readable status when local TTS is unavailable", async () => {
    appSettingsStore = { ...appSettingsStore, voice_output: "on" };
    render(<App />);

    expect(await screen.findByText(/本地语音：不可用/)).toBeInTheDocument();
    expect(screen.getByText("当前环境不支持本地语音输出。")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");

    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: "tts_error", reason: "unavailable", status: "当前环境不支持" })
      ])
    );
  });

  it("updates the Voice Output status when system voices load later", async () => {
    const speech = installSpeechSynthesisMock();
    render(<App />);

    expect(await screen.findByText(/等待系统语音列表/)).toBeInTheDocument();

    act(() => {
      speech.setVoices([mockVoice("zh-Hans")]);
    });

    expect(await screen.findByText(/优先使用中文语音/)).toBeInTheDocument();
  });

  it("plays a test voice from Settings without writing chat", async () => {
    const speech = installSpeechSynthesisMock([mockVoice("zh-CN")]);
    render(<App />);

    expect(await screen.findByText(/优先使用中文语音/)).toBeInTheDocument();
    const chatPanel = screen.getByRole("region", { name: "聊天面板" });
    await userEvent.click(screen.getByRole("button", { name: "测试语音 / Test Voice" }));

    await waitFor(() => expect(speech.speak).toHaveBeenCalledTimes(1));
    expect(speech.speak.mock.calls[0][0]).toMatchObject({
      text: "你好，我是 Rei。语音输出测试。",
      lang: "zh-CN",
      voice: expect.objectContaining({ lang: "zh-CN" })
    });
    expect(within(chatPanel).queryByText("你好，我是 Rei。语音输出测试。")).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/chat"),
      expect.objectContaining({ method: "POST" })
    );

    act(() => {
      speech.speak.mock.calls[0][0].onstart?.({} as SpeechSynthesisEvent);
    });

    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "tts_started", source: "test_voice" })])
    );
  });

  it("shows Voice Input controls and Settings availability status", async () => {
    installMediaDevicesMock("prompt");
    installSpeechRecognitionMock();
    render(<App />);

    expect(await screen.findByRole("button", { name: "开始语音 / Start Voice" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("语音输入 / Voice Input");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("可用");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("语音识别功能：可用");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("麦克风权限：可请求");
    expect(screen.getByText(/语音输入：待命/)).toBeInTheDocument();
  });

  it("shows Local ASR not configured status in Voice Input settings", async () => {
    render(<App />);

    const voiceInputSettings = await screen.findByRole("group", { name: "语音输入设置" });

    expect(voiceInputSettings).toHaveTextContent("本地语音识别 / Local ASR");
    expect(voiceInputSettings).toHaveTextContent("未配置");
    expect(voiceInputSettings).toHaveTextContent("本地语音识别未配置");
    expect(voiceInputSettings).toHaveTextContent("未配置本地 ASR 时，主聊天语音按钮会回退到 Web Speech");
    expect(voiceInputSettings).toHaveTextContent("配置未就绪");
    expect(screen.getByRole("button", { name: "检查本地 ASR / Check Local ASR" })).toBeDisabled();
    expect(voiceInputSettings).not.toHaveTextContent("/Users/aragoto");
    expect(voiceInputSettings).not.toHaveTextContent("REILINK_LOCAL_ASR_BINARY");
    expect(voiceInputSettings).not.toHaveTextContent("REILINK_LOCAL_ASR_MODEL");
  });

  it("shows Local ASR setup controls with safe settings summary", async () => {
    render(<App />);

    const setup = await screen.findByRole("group", { name: "本地 ASR 配置 / Local ASR Setup" });

    expect(setup).toHaveTextContent("本地 ASR 配置 / Local ASR Setup");
    expect(setup).toHaveTextContent("未配置");
    expect(setup).toHaveTextContent("识别程序：未配置");
    expect(setup).toHaveTextContent("模型：未配置");
    expect(setup).toHaveTextContent("转换工具：未配置");
    expect(screen.getByLabelText("本地识别程序 / ASR Binary")).toBeInTheDocument();
    expect(screen.getByLabelText("模型文件 / Model File")).toBeInTheDocument();
    expect(screen.getByLabelText("音频转换工具 / Audio Converter")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "选择本地识别程序文件" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "选择模型文件" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "选择音频转换工具文件" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "保存配置 / Save" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "清除配置 / Clear" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "重新检测 / Refresh Status" })).toBeEnabled();
  });

  it("fills only the selected Local ASR path field from the native file picker", async () => {
    const runtime = installRuntimeBridge(backendRuntimeStatus);
    render(<App />);

    const binaryInput = await screen.findByLabelText("本地识别程序 / ASR Binary");
    const modelInput = screen.getByLabelText("模型文件 / Model File");
    const converterInput = screen.getByLabelText("音频转换工具 / Audio Converter");

    await userEvent.type(binaryInput, "/Users/aragoto/private/old-whisper-cli");
    vi.mocked(runtime.bridge.selectLocalFile).mockResolvedValueOnce({ canceled: true, path: null });
    await userEvent.click(screen.getByRole("button", { name: "选择本地识别程序文件" }));
    await waitFor(() =>
      expect(runtime.bridge.selectLocalFile).toHaveBeenLastCalledWith({
        kind: "asr_binary",
        currentPath: "/Users/aragoto/private/old-whisper-cli"
      })
    );
    expect(binaryInput).toHaveValue("/Users/aragoto/private/old-whisper-cli");

    vi.mocked(runtime.bridge.selectLocalFile).mockResolvedValueOnce({
      canceled: false,
      path: "/Users/aragoto/private/whisper-cli"
    });
    await userEvent.click(screen.getByRole("button", { name: "选择本地识别程序文件" }));
    await waitFor(() => expect(binaryInput).toHaveValue("/Users/aragoto/private/whisper-cli"));
    expect(modelInput).toHaveValue("");
    expect(converterInput).toHaveValue("");

    vi.mocked(runtime.bridge.selectLocalFile).mockResolvedValueOnce({
      canceled: false,
      path: "/Users/aragoto/Library/Application Support/ReiLink/models/ggml-base.bin"
    });
    await userEvent.click(screen.getByRole("button", { name: "选择模型文件" }));
    await waitFor(() =>
      expect(runtime.bridge.selectLocalFile).toHaveBeenLastCalledWith({
        kind: "asr_model",
        currentPath: ""
      })
    );
    await waitFor(() =>
      expect(modelInput).toHaveValue("/Users/aragoto/Library/Application Support/ReiLink/models/ggml-base.bin")
    );
    expect(binaryInput).toHaveValue("/Users/aragoto/private/whisper-cli");
    expect(converterInput).toHaveValue("");

    vi.mocked(runtime.bridge.selectLocalFile).mockResolvedValueOnce({
      canceled: false,
      path: "/opt/homebrew/bin/ffmpeg"
    });
    await userEvent.click(screen.getByRole("button", { name: "选择音频转换工具文件" }));
    await waitFor(() =>
      expect(runtime.bridge.selectLocalFile).toHaveBeenLastCalledWith({
        kind: "asr_converter",
        currentPath: ""
      })
    );
    await waitFor(() => expect(converterInput).toHaveValue("/opt/homebrew/bin/ffmpeg"));
    expect(binaryInput).toHaveValue("/Users/aragoto/private/whisper-cli");
    expect(modelInput).toHaveValue("/Users/aragoto/Library/Application Support/ReiLink/models/ggml-base.bin");
    expect(screen.getByText("已选择文件，请点击保存配置。")).toBeInTheDocument();

    expect(JSON.stringify(eventBus.getRecentEvents(50))).not.toContain("/Users/aragoto/private/whisper-cli");
    expect(JSON.stringify(eventBus.getRecentEvents(50))).not.toContain("ggml-base.bin");
    expect(JSON.stringify(eventBus.getRecentEvents(50))).not.toContain("/opt/homebrew/bin/ffmpeg");
  });

  it("saves Local ASR paths, shows basenames, and keeps debug surfaces safe", async () => {
    const binaryPath = "/Users/aragoto/private/whisper-cli";
    const modelPath = "/Users/aragoto/Library/Application Support/ReiLink/models/ggml-base.bin";
    const converterPath = "/Users/aragoto/tools/ffmpeg";
    render(<App />);

    await userEvent.type(await screen.findByLabelText("本地识别程序 / ASR Binary"), binaryPath);
    await userEvent.type(screen.getByLabelText("模型文件 / Model File"), modelPath);
    await userEvent.type(screen.getByLabelText("音频转换工具 / Audio Converter"), converterPath);
    await userEvent.click(screen.getByRole("button", { name: "保存配置 / Save" }));

    const setup = await screen.findByRole("group", { name: "本地 ASR 配置 / Local ASR Setup" });
    await waitFor(() => expect(setup).toHaveTextContent("本地 ASR 配置已保存"));
    expect(setup).toHaveTextContent("用户配置");
    expect(setup).toHaveTextContent("识别程序：whisper-cli");
    expect(setup).toHaveTextContent("模型：ggml-base.bin");
    expect(setup).toHaveTextContent("转换工具：ffmpeg");
    expect(screen.getByLabelText("本地识别程序 / ASR Binary")).toHaveValue("");
    expect(screen.getByLabelText("模型文件 / Model File")).toHaveValue("");
    expect(screen.getByLabelText("音频转换工具 / Audio Converter")).toHaveValue("");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/voice-input/local-asr/settings"),
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          local_asr_binary_path: binaryPath,
          local_asr_model_path: modelPath,
          audio_converter_binary_path: converterPath
        })
      })
    );

    const rawJson = screen.getByText("原始 JSON").closest("details");
    expect(rawJson).not.toBeNull();
    expect(rawJson).toHaveTextContent("safe_converter_name");
    expect(rawJson).toHaveTextContent("whisper-cli");
    expect(rawJson).toHaveTextContent("ggml-base.bin");
    expect(rawJson).toHaveTextContent("ffmpeg");
    const debugSummary = screen.getByText("配置摘要").closest("div");
    expect(debugSummary).toHaveTextContent("whisper-cli");
    expect(debugSummary).toHaveTextContent("ggml-base.bin");
    expect(debugSummary).toHaveTextContent("ffmpeg");
    const combinedSafeSurface = [
      setup.textContent,
      rawJson?.textContent,
      debugSummary?.textContent,
      JSON.stringify(eventBus.getRecentEvents(50))
    ].join("\n");
    expect(combinedSafeSurface).not.toContain(binaryPath);
    expect(combinedSafeSurface).not.toContain(modelPath);
    expect(combinedSafeSurface).not.toContain(converterPath);
  });

  it("clears Local ASR settings and refreshes local status", async () => {
    setLocalAsrReady();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "清除配置 / Clear" }));

    const setup = await screen.findByRole("group", { name: "本地 ASR 配置 / Local ASR Setup" });
    await waitFor(() => expect(setup).toHaveTextContent("本地 ASR 配置已清除"));
    expect(setup).toHaveTextContent("识别程序：未配置");
    expect(screen.getByRole("button", { name: "检查本地 ASR / Check Local ASR" })).toBeDisabled();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/voice-input/local-asr/settings"),
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("refreshes Local ASR settings and status on demand", async () => {
    render(<App />);
    await screen.findByRole("group", { name: "本地 ASR 配置 / Local ASR Setup" });
    const initialSettingsCalls = vi.mocked(fetch).mock.calls.filter(([url]) =>
      String(url).includes("/api/voice-input/local-asr/settings")
    ).length;
    localAsrSettingsStore = {
      ...localAsrSettings,
      configured: true,
      binary_configured: true,
      model_configured: true,
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin",
      source: "env"
    };
    localAsrStatusStore = {
      ...localAsrStatus,
      status: "local_asr_ready",
      available: true,
      binary_configured: true,
      binary_present: true,
      binary_executable: true,
      model_configured: true,
      model_present: true,
      display_message: "本地语音识别配置已就绪",
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin",
      source: "env"
    };

    await userEvent.click(screen.getByRole("button", { name: "重新检测 / Refresh Status" }));

    const setup = screen.getByRole("group", { name: "本地 ASR 配置 / Local ASR Setup" });
    await waitFor(() => expect(setup).toHaveTextContent("本地 ASR 状态已刷新"));
    expect(setup).toHaveTextContent("环境变量");
    expect(screen.getByRole("button", { name: "检查本地 ASR / Check Local ASR" })).toBeEnabled();
    expect(vi.mocked(fetch).mock.calls.filter(([url]) =>
      String(url).includes("/api/voice-input/local-asr/settings")
    ).length).toBeGreaterThan(initialSettingsCalls);
  });

  it("shows Local ASR model missing with safe file names only", async () => {
    localAsrStatusStore = {
      ...localAsrStatus,
      status: "local_asr_model_missing",
      binary_configured: true,
      binary_present: true,
      binary_executable: true,
      model_configured: true,
      model_present: false,
      display_message: "缺少本地语音模型",
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin"
    };
    render(<App />);

    const voiceInputSettings = await screen.findByRole("group", { name: "语音输入设置" });

    expect(voiceInputSettings).toHaveTextContent("缺少模型文件");
    expect(voiceInputSettings).toHaveTextContent("缺少本地语音模型");
    expect(voiceInputSettings).toHaveTextContent("识别程序：whisper-cli");
    expect(voiceInputSettings).toHaveTextContent("模型：ggml-base.bin");
    expect(screen.getByRole("button", { name: "检查本地 ASR / Check Local ASR" })).toBeDisabled();
    expect(voiceInputSettings).not.toHaveTextContent("/Users/aragoto/Library/Application Support/ReiLink/models");
  });

  it("shows Local ASR ready and enables the main chat voice button", async () => {
    setLocalAsrReady();
    installAudioCaptureMock();
    render(<App />);

    const voiceInputSettings = await screen.findByRole("group", { name: "语音输入设置" });

    expect(voiceInputSettings).toHaveTextContent("已就绪");
    expect(voiceInputSettings).toHaveTextContent("本地语音识别配置已就绪");
    expect(voiceInputSettings).toHaveTextContent("主聊天语音按钮会优先使用本地 ASR");
    expect(voiceInputSettings).toHaveTextContent("未检查");
    expect(screen.getByRole("button", { name: "检查本地 ASR / Check Local ASR" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "开始本地语音 / Start Local ASR" })).toBeEnabled();
    expect(screen.getByText("语音输入：本地语音识别可用")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "测试语音 / Test Voice" })).toBeInTheDocument();
  });

  it("checks Local ASR and shows succeeded status without leaking raw output", async () => {
    localAsrStatusStore = {
      ...localAsrStatus,
      status: "local_asr_ready",
      available: true,
      binary_configured: true,
      binary_present: true,
      binary_executable: true,
      model_configured: true,
      model_present: true,
      display_message: "本地语音识别配置已就绪",
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin"
    };
    localAsrProbeResponseStore = {
      ...localAsrProbeResponse,
      display_message: "本地语音识别程序可以启动",
      binary_name: "whisper-cli",
      model_name: "ggml-base.bin",
      duration_ms: 58
    };
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "检查本地 ASR / Check Local ASR" }));

    const voiceInputSettings = await screen.findByRole("group", { name: "语音输入设置" });
    await waitFor(() => expect(voiceInputSettings).toHaveTextContent("可以启动"));
    expect(voiceInputSettings).toHaveTextContent("本地语音识别程序可以启动");
    expect(voiceInputSettings).toHaveTextContent("58 ms");
    expect(voiceInputSettings).not.toHaveTextContent("Usage:");
    expect(voiceInputSettings).not.toHaveTextContent("stderr");
    expect(voiceInputSettings).not.toHaveTextContent("/Users/aragoto");
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/voice-input/local-asr/probe"), expect.objectContaining({ method: "POST" }));
  });

  it("shows Local ASR checking state while probe is pending", async () => {
    localAsrStatusStore = {
      ...localAsrStatus,
      status: "local_asr_ready",
      available: true,
      binary_configured: true,
      binary_present: true,
      binary_executable: true,
      model_configured: true,
      model_present: true,
      display_message: "本地语音识别配置已就绪",
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin"
    };
    let resolveProbe: (response: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.endsWith("/api/voice-input/local-asr/probe") && init?.method === "POST") {
          return new Promise<Response>((resolve) => {
            resolveProbe = resolve;
          });
        }
        return defaultFetchResponse(url, init);
      })
    );
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "检查本地 ASR / Check Local ASR" }));
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("正在检查");

    resolveProbe(Response.json(localAsrProbeResponse));
    await waitFor(() => expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("可以启动"));
  });

  it("shows Local ASR timeout and failed probe states safely", async () => {
    localAsrStatusStore = {
      ...localAsrStatus,
      status: "local_asr_ready",
      available: true,
      binary_configured: true,
      binary_present: true,
      binary_executable: true,
      model_configured: true,
      model_present: true,
      display_message: "本地语音识别配置已就绪",
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin"
    };
    localAsrProbeResponseStore = {
      ...localAsrProbeResponse,
      status: "local_asr_probe_timed_out",
      available: false,
      display_message: "本地语音识别程序启动超时",
      duration_ms: 3000
    };
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "检查本地 ASR / Check Local ASR" }));
    await waitFor(() => expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("启动超时"));

    localAsrProbeResponseStore = {
      ...localAsrProbeResponse,
      status: "local_asr_probe_failed",
      available: false,
      display_message: "本地语音识别程序启动失败",
      duration_ms: 61
    };
    await userEvent.click(screen.getByRole("button", { name: "检查本地 ASR / Check Local ASR" }));
    await waitFor(() => expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("启动失败"));
    expect(screen.getByRole("group", { name: "语音输入设置" })).not.toHaveTextContent("raw stderr");
  });

  it("Local ASR probe does not fill chat input or auto send", async () => {
    localAsrStatusStore = {
      ...localAsrStatus,
      status: "local_asr_ready",
      available: true,
      binary_configured: true,
      binary_present: true,
      binary_executable: true,
      model_configured: true,
      model_present: true,
      display_message: "本地语音识别配置已就绪",
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin"
    };
    render(<App />);

    const input = await screen.findByLabelText("聊天输入");
    await userEvent.click(screen.getByRole("button", { name: "检查本地 ASR / Check Local ASR" }));
    await waitFor(() => expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("可以启动"));

    expect(input).toHaveValue("");
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining("/api/chat"), expect.objectContaining({ method: "POST" }));
  });

  it("shows Audio Capture Test unavailable when MediaRecorder is missing", async () => {
    installMediaDevicesMock("prompt");
    render(<App />);

    const voiceInputSettings = await screen.findByRole("group", { name: "语音输入设置" });

    expect(voiceInputSettings).toHaveTextContent("录音测试 / Audio Capture Test");
    expect(voiceInputSettings).toHaveTextContent("当前环境不支持录音");
    expect(screen.getByRole("button", { name: "测试录音 / Test Recording" })).toBeDisabled();
  });

  it("shows readable Audio Capture permission denied errors", async () => {
    installAudioCaptureMock({ permissionDenied: true });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "测试录音 / Test Recording" }));

    const voiceInputSettings = screen.getByRole("group", { name: "语音输入设置" });
    await waitFor(() => expect(voiceInputSettings).toHaveTextContent("权限被拒绝"));
    expect(voiceInputSettings).toHaveTextContent("麦克风权限被拒绝");
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "audio_capture_error", reason: "permission_denied" })])
    );
  });

  it("records audio, stops tracks, uploads blob, and shows cleanup success", async () => {
    const audioMock = installAudioCaptureMock();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "测试录音 / Test Recording" }));
    expect(audioMock.getUserMedia).toHaveBeenCalledWith({ audio: true });
    expect(MockMediaRecorder.instances).toHaveLength(1);
    expect(MockMediaRecorder.instances[0].start).toHaveBeenCalled();
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("正在录音");

    await userEvent.click(screen.getByRole("button", { name: "停止录音 / Stop Recording" }));

    const voiceInputSettings = screen.getByRole("group", { name: "语音输入设置" });
    await waitFor(() => expect(voiceInputSettings).toHaveTextContent("录音测试完成"));
    expect(voiceInputSettings).toHaveTextContent("临时音频已清理：是");
    expect(voiceInputSettings).toHaveTextContent("格式：audio/webm");
    expect(voiceInputSettings).toHaveTextContent("当前录音格式需要本地转换为 WAV");
    expect(audioMock.stopTrack).toHaveBeenCalled();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/voice-input/audio/probe"),
      expect.objectContaining({
        method: "POST",
        body: expect.any(Blob),
        headers: expect.objectContaining({ "Content-Type": "audio/webm" })
      })
    );
  });

  it("Audio Capture probe does not fill chat input or auto send", async () => {
    installAudioCaptureMock();
    render(<App />);

    const input = await screen.findByLabelText("聊天输入");
    await userEvent.click(screen.getByRole("button", { name: "测试录音 / Test Recording" }));
    await userEvent.click(screen.getByRole("button", { name: "停止录音 / Stop Recording" }));
    await waitFor(() => expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("录音测试完成"));

    expect(input).toHaveValue("");
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining("/api/chat"), expect.objectContaining({ method: "POST" }));
  });

  it("Audio Capture Event Stream summaries do not expose audio content or paths", async () => {
    installAudioCaptureMock();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "测试录音 / Test Recording" }));
    await userEvent.click(screen.getByRole("button", { name: "停止录音 / Stop Recording" }));
    await waitFor(() => expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("录音测试完成"));
    fireEvent.click(screen.getByText("事件流 / Event Stream"));

    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    expect(eventStream).not.toBeNull();
    await waitFor(() => expect(eventStream).toHaveTextContent("录音测试开始"));
    expect(eventStream).toHaveTextContent("录音测试完成");
    expect(eventStream).toHaveTextContent("临时音频已清理");
    expect(eventStream).not.toHaveTextContent("fake-webm-audio");
    expect(eventStream).not.toHaveTextContent("base64");
    expect(eventStream).not.toHaveTextContent("/tmp");
    expect(eventStream).not.toHaveTextContent("Authorization");
    expect(eventStream).not.toHaveTextContent(".env");
  });

  it("shows Local Transcribe disabled until Local ASR is ready", async () => {
    installAudioCaptureMock();
    render(<App />);

    const voiceInputSettings = await screen.findByRole("group", { name: "语音输入设置" });

    expect(voiceInputSettings).toHaveTextContent("本地转写测试 / Local Transcribe Test");
    expect(voiceInputSettings).toHaveTextContent("配置未就绪");
    expect(screen.getByRole("button", { name: "录音并转写 / Record & Transcribe" })).toBeDisabled();
  });

  it("records audio, calls Local ASR transcription, fills input, and does not auto send", async () => {
    const simplifiedTranscript = "玛尔基特怎么打";
    localAsrStatusStore = {
      ...localAsrStatus,
      status: "local_asr_ready",
      available: true,
      binary_configured: true,
      binary_present: true,
      binary_executable: true,
      model_configured: true,
      model_present: true,
      display_message: "本地语音识别配置已就绪",
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin"
    };
    localAsrTranscriptionResponseStore = {
      ...localAsrTranscriptionResponse,
      transcript: simplifiedTranscript,
      transcript_char_count: simplifiedTranscript.length,
      language: "zh",
      transcript_normalized_to_simplified: true
    };
    const audioMock = installAudioCaptureMock();
    render(<App />);
    await screen.findByText("已连接");
    vi.mocked(fetch).mockClear();

    await userEvent.click(screen.getByRole("button", { name: "录音并转写 / Record & Transcribe" }));
    expect(audioMock.getUserMedia).toHaveBeenCalledWith({ audio: true });
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("正在录音");

    await userEvent.click(screen.getByRole("button", { name: "停止本地转写录音 / Stop Local Transcribe Recording" }));

    await waitFor(() => expect(screen.getByLabelText("聊天输入")).toHaveValue(simplifiedTranscript));
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("转写完成");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("转写完成，请确认后发送");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("语言：zh");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("已规范为简体中文");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("临时音频已清理：是");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("格式：audio/webm");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("当前录音格式需要本地转换为 WAV");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("转换：音频已转换为 WAV");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("目标格式：audio/wav");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("转换器：ffmpeg");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("原始音频已清理：是");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("转换音频已清理：是");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("模型取舍：ggml-base.bin");
    expect(screen.getByRole("group", { name: "语音输入设置" })).not.toHaveTextContent("/Users/aragoto");
    expect(audioMock.stopTrack).toHaveBeenCalled();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/voice-input/local-asr/transcribe"),
      expect.objectContaining({
        method: "POST",
        body: expect.any(FormData)
      })
    );
    const fetchCalls = vi.mocked(fetch).mock.calls;
    const transcribeCall = fetchCalls.find(([url]) => String(url).includes("/api/voice-input/local-asr/transcribe"));
    expect(transcribeCall).toBeTruthy();
    expect((transcribeCall?.[1]?.body as FormData).get("language")).toBe("zh-CN");
    expect(fetchCalls.some(([url, init]) => String(url).includes("/api/chat") && init?.method === "POST")).toBe(false);
    expect(fetchCalls.some(([url]) => String(url).includes("/api/memory"))).toBe(false);
    expect(fetchCalls.some(([url]) => String(url).includes("/api/debug/prompt-preview"))).toBe(false);
    expect(fetchCalls.some(([url]) => String(url).includes("/api/game/context"))).toBe(false);
    expect(screen.queryByText(simplifiedTranscript)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    expect(await screen.findByText(simplifiedTranscript)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/chat"), expect.objectContaining({ method: "POST" }));
  });

  it("shows a Local ASR timeout suggestion without filling input", async () => {
    setLocalAsrReady();
    localAsrTranscriptionResponseStore = {
      ...localAsrTranscriptionResponse,
      status: "local_asr_transcription_timed_out",
      available: false,
      display_message: "本地语音识别超时，可以尝试更小模型或更短录音",
      transcript: "",
      transcript_char_count: 0,
      conversion_status: "audio_conversion_not_needed",
      conversion_required: false
    };
    installAudioCaptureMock();
    render(<App />);
    await screen.findByText("已连接");

    await userEvent.click(await screen.findByRole("button", { name: "开始本地语音 / Start Local ASR" }));
    await userEvent.click(await screen.findByRole("button", { name: "停止本地转写录音 / Stop Local ASR Recording" }));

    await waitFor(() =>
      expect(screen.getByText("语音输入：本地语音识别超时，可以尝试更小模型或更短录音")).toBeInTheDocument()
    );
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("本地语音识别超时，可以尝试更小模型或更短录音");
    expect(screen.getByLabelText("聊天输入")).toHaveValue("");
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining("/api/chat"), expect.objectContaining({ method: "POST" }));
  });

  it("shows Local ASR audio conversion not configured without filling input", async () => {
    localAsrStatusStore = {
      ...localAsrStatus,
      status: "local_asr_ready",
      available: true,
      binary_configured: true,
      binary_present: true,
      binary_executable: true,
      model_configured: true,
      model_present: true,
      display_message: "本地语音识别配置已就绪",
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin"
    };
    localAsrTranscriptionResponseStore = {
      ...localAsrTranscriptionResponse,
      status: "local_asr_transcription_failed",
      available: false,
      display_message: "尚未配置音频转换工具",
      transcript: "",
      transcript_char_count: 0,
      conversion_status: "audio_conversion_not_configured",
      conversion_required: true,
      converted_mime_type: null,
      converter_configured: false,
      safe_converter_name: null
    };
    installAudioCaptureMock();
    render(<App />);
    await screen.findByText("已连接");
    vi.mocked(fetch).mockClear();

    await userEvent.click(screen.getByRole("button", { name: "录音并转写 / Record & Transcribe" }));
    await userEvent.click(screen.getByRole("button", { name: "停止本地转写录音 / Stop Local Transcribe Recording" }));

    const voiceInputSettings = screen.getByRole("group", { name: "语音输入设置" });
    await waitFor(() => expect(voiceInputSettings).toHaveTextContent("转写失败"));
    expect(voiceInputSettings).toHaveTextContent("尚未配置音频转换工具");
    expect(voiceInputSettings).toHaveTextContent("转换：尚未配置音频转换工具");
    expect(voiceInputSettings).toHaveTextContent("转换工具：未配置");
    expect(screen.getByLabelText("聊天输入")).toHaveValue("");
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining("/api/chat"), expect.objectContaining({ method: "POST" }));
  });

  it("keeps empty Local ASR transcription out of the input", async () => {
    localAsrStatusStore = {
      ...localAsrStatus,
      status: "local_asr_ready",
      available: true,
      binary_configured: true,
      binary_present: true,
      binary_executable: true,
      model_configured: true,
      model_present: true,
      display_message: "本地语音识别配置已就绪",
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin"
    };
    localAsrTranscriptionResponseStore = {
      ...localAsrTranscriptionResponse,
      status: "local_asr_transcription_no_text",
      available: false,
      display_message: "没有识别到可用文本",
      transcript: "",
      transcript_char_count: 0
    };
    installAudioCaptureMock();
    render(<App />);
    await screen.findByText("已连接");

    await userEvent.click(screen.getByRole("button", { name: "录音并转写 / Record & Transcribe" }));
    await userEvent.click(screen.getByRole("button", { name: "停止本地转写录音 / Stop Local Transcribe Recording" }));

    await waitFor(() => expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("没有识别到可用文本"));
    expect(screen.getByLabelText("聊天输入")).toHaveValue("");
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining("/api/chat"), expect.objectContaining({ method: "POST" }));
  });

  it("Local ASR transcription Event Stream summaries do not expose full transcript", async () => {
    const privateTranscript = "玛尔基特怎么打";
    localAsrStatusStore = {
      ...localAsrStatus,
      status: "local_asr_ready",
      available: true,
      binary_configured: true,
      binary_present: true,
      binary_executable: true,
      model_configured: true,
      model_present: true,
      display_message: "本地语音识别配置已就绪",
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin"
    };
    localAsrTranscriptionResponseStore = {
      ...localAsrTranscriptionResponse,
      transcript: privateTranscript,
      transcript_char_count: privateTranscript.length,
      language: "zh",
      transcript_normalized_to_simplified: true
    };
    installAudioCaptureMock();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "录音并转写 / Record & Transcribe" }));
    await userEvent.click(screen.getByRole("button", { name: "停止本地转写录音 / Stop Local Transcribe Recording" }));
    await waitFor(() => expect(screen.getByLabelText("聊天输入")).toHaveValue(privateTranscript));
    fireEvent.click(screen.getByText("事件流 / Event Stream"));

    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    expect(eventStream).not.toBeNull();
    await waitFor(() => expect(eventStream).toHaveTextContent("本地语音识别开始"));
    expect(eventStream).toHaveTextContent("本地语音识别完成");
    expect(eventStream).toHaveTextContent(`${privateTranscript.length} 字`);
    expect(eventStream).toHaveTextContent("语言：zh");
    expect(eventStream).toHaveTextContent("已规范为简体中文");
    expect(eventStream).toHaveTextContent("音频已转换为 WAV");
    expect(eventStream).toHaveTextContent("转为 audio/wav");
    expect(eventStream).toHaveTextContent("转换器：ffmpeg");
    expect(eventStream).not.toHaveTextContent(privateTranscript);
    expect(eventStream).not.toHaveTextContent("fake-webm-audio");
    expect(eventStream).not.toHaveTextContent("raw stdout");
    expect(eventStream).not.toHaveTextContent("raw stderr");
    expect(eventStream).not.toHaveTextContent("/Users/aragoto");
    expect(eventStream).not.toHaveTextContent("Authorization");
    expect(eventStream).not.toHaveTextContent(".env");
  });

  it("Debug Panel does not show the full Local ASR transcript", async () => {
    const privateTranscript = "本地转写私有文本";
    localAsrStatusStore = {
      ...localAsrStatus,
      status: "local_asr_ready",
      available: true,
      binary_configured: true,
      binary_present: true,
      binary_executable: true,
      model_configured: true,
      model_present: true,
      display_message: "本地语音识别配置已就绪",
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin"
    };
    localAsrTranscriptionResponseStore = {
      ...localAsrTranscriptionResponse,
      transcript: privateTranscript,
      transcript_char_count: privateTranscript.length,
      language: "zh",
      transcript_normalized_to_simplified: true
    };
    installAudioCaptureMock();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "录音并转写 / Record & Transcribe" }));
    await userEvent.click(screen.getByRole("button", { name: "停止本地转写录音 / Stop Local Transcribe Recording" }));
    await waitFor(() => expect(screen.getByLabelText("聊天输入")).toHaveValue(privateTranscript));

    const rawJson = screen.getByText("原始 JSON").closest("details");
    expect(rawJson).not.toBeNull();
    expect(rawJson).toHaveTextContent("transcript_char_count");
    expect(rawJson).not.toHaveTextContent("\"transcript\"");
    expect(rawJson).not.toHaveTextContent(privateTranscript);
    expect(screen.getByText("本地转写字数").closest("div")).toHaveTextContent(String(privateTranscript.length));
    expect(screen.getByText("本地转写语言").closest("div")).toHaveTextContent("zh");
    expect(screen.getByText("本地转写简体规范").closest("div")).toHaveTextContent("已规范为简体中文");
    expect(screen.getByText("本地转写格式").closest("div")).toHaveTextContent("audio/webm");
    expect(screen.getByText("本地转写格式提示").closest("div")).toHaveTextContent("当前录音格式需要本地转换为 WAV");
    expect(screen.getByText("本地转写转换状态").closest("div")).toHaveTextContent("音频已转换为 WAV");
    expect(screen.getByText("本地转写目标格式").closest("div")).toHaveTextContent("audio/wav");
    expect(screen.getByText("本地转写转换工具").closest("div")).toHaveTextContent("已配置 / ffmpeg");
  });

  it("shows safe audio format summaries without raw audio paths or subprocess output", async () => {
    audioProbeResponseStore = {
      ...audioProbeResponse,
      mime_type: "audio/webm;codecs=opus"
    };
    installAudioCaptureMock();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "测试录音 / Test Recording" }));
    await userEvent.click(screen.getByRole("button", { name: "停止录音 / Stop Recording" }));

    const voiceInputSettings = screen.getByRole("group", { name: "语音输入设置" });
    await waitFor(() => expect(voiceInputSettings).toHaveTextContent("录音测试完成"));
    expect(voiceInputSettings).toHaveTextContent("格式：audio/webm");
    expect(voiceInputSettings).toHaveTextContent("当前录音格式需要本地转换为 WAV");
    expect(voiceInputSettings).not.toHaveTextContent("codecs=opus");
    expect(voiceInputSettings).not.toHaveTextContent("/tmp");
    expect(voiceInputSettings).not.toHaveTextContent("raw stdout");
    expect(voiceInputSettings).not.toHaveTextContent("raw stderr");
  });

  it("stops active Voice Output when Local ASR transcription starts", async () => {
    localAsrStatusStore = {
      ...localAsrStatus,
      status: "local_asr_ready",
      available: true,
      binary_configured: true,
      binary_present: true,
      binary_executable: true,
      model_configured: true,
      model_present: true,
      display_message: "本地语音识别配置已就绪",
      safe_binary_name: "whisper-cli",
      safe_model_name: "ggml-base.bin"
    };
    const speech = installSpeechSynthesisMock([mockVoice("zh-CN")]);
    installAudioCaptureMock();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "测试语音 / Test Voice" }));
    await waitFor(() => expect(speech.speak).toHaveBeenCalledTimes(1));
    await userEvent.click(screen.getByRole("button", { name: "录音并转写 / Record & Transcribe" }));

    expect(speech.cancel).toHaveBeenCalledTimes(1);
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "tts_stopped", reason: "user_stop" })])
    );
  });

  it("routes the main chat voice button through Local ASR when Web Speech is unavailable", async () => {
    setLocalAsrReady();
    const privateTranscript = "主按钮本地转写文本";
    localAsrTranscriptionResponseStore = {
      ...localAsrTranscriptionResponse,
      transcript: privateTranscript,
      transcript_char_count: privateTranscript.length
    };
    const speech = installSpeechSynthesisMock([mockVoice("zh-CN")]);
    const audioMock = installAudioCaptureMock();
    render(<App />);
    await screen.findByText("已连接");

    const mainVoiceButton = await screen.findByRole("button", { name: "开始本地语音 / Start Local ASR" });
    expect(mainVoiceButton).toBeEnabled();
    expect(screen.getByText("语音输入：本地语音识别可用")).toBeInTheDocument();
    expect(screen.queryByText("语音输入：语音识别服务不可用")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "测试语音 / Test Voice" }));
    await waitFor(() => expect(speech.speak).toHaveBeenCalledTimes(1));
    vi.mocked(fetch).mockClear();

    await userEvent.click(mainVoiceButton);
    expect(speech.cancel).toHaveBeenCalledTimes(1);
    expect(audioMock.getUserMedia).toHaveBeenCalledWith({ audio: true });
    expect(await screen.findByRole("button", { name: "停止本地转写录音 / Stop Local ASR Recording" })).toBeEnabled();
    expect(screen.getByText("语音输入：正在录音")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "停止本地转写录音 / Stop Local ASR Recording" }));

    await waitFor(() => expect(screen.getByLabelText("聊天输入")).toHaveValue(privateTranscript));
    expect(screen.getByText("语音输入：转写完成，请确认后发送")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/voice-input/local-asr/transcribe"),
      expect.objectContaining({ method: "POST", body: expect.any(FormData) })
    );
    const fetchCalls = vi.mocked(fetch).mock.calls;
    expect(fetchCalls.some(([url, init]) => String(url).includes("/api/chat") && init?.method === "POST")).toBe(false);
    expect(fetchCalls.some(([url]) => String(url).includes("/api/memory"))).toBe(false);
    expect(fetchCalls.some(([url]) => String(url).includes("/api/debug/prompt-preview"))).toBe(false);
    expect(fetchCalls.some(([url]) => String(url).includes("/api/game/context"))).toBe(false);
    expect(screen.queryByText(privateTranscript)).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("事件流 / Event Stream"));
    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    expect(eventStream).not.toBeNull();
    await waitFor(() => expect(eventStream).toHaveTextContent("本地语音识别开始"));
    expect(eventStream).toHaveTextContent("本地语音识别完成");
    expect(eventStream).toHaveTextContent(`${privateTranscript.length} 字`);
    expect(eventStream).not.toHaveTextContent(privateTranscript);
    expect(eventStream).not.toHaveTextContent("/Users/aragoto");
    expect(eventStream).not.toHaveTextContent("raw stdout");
    expect(eventStream).not.toHaveTextContent("raw stderr");

    expect(screen.getByText("主输入提供方").closest("div")).toHaveTextContent("local_asr");
    expect(screen.getByText("主输入状态").closest("div")).toHaveTextContent("转写完成，请确认后发送");
    const rawJson = screen.getByText("原始 JSON").closest("details");
    expect(rawJson).not.toBeNull();
    expect(rawJson).toHaveTextContent("main_provider");
    expect(rawJson).toHaveTextContent("local_asr_conversion_status");
    expect(rawJson).not.toHaveTextContent("\"transcript\"");
    expect(rawJson).not.toHaveTextContent(privateTranscript);
  });

  it("keeps the main chat voice button on Local ASR when Web Speech reports service unavailable", async () => {
    setLocalAsrReady();
    installAudioCaptureMock();
    installMediaDevicesMock("granted");
    const recognition = installSpeechRecognitionMock();
    render(<App />);

    await screen.findByRole("button", { name: "开始本地语音 / Start Local ASR" });
    act(() => {
      voiceInput.start({ onFinalTranscript: vi.fn() });
    });
    act(() => {
      recognition.instances[0].emitError("network");
    });

    const voiceInputSettings = screen.getByRole("group", { name: "语音输入设置" });
    await waitFor(() => expect(voiceInputSettings).toHaveTextContent("服务不可用"));
    expect(screen.getByRole("button", { name: "开始本地语音 / Start Local ASR" })).toBeEnabled();
    expect(screen.getByText("语音输入：本地语音识别可用")).toBeInTheDocument();
    expect(screen.queryByText("语音输入：语音识别服务不可用")).not.toBeInTheDocument();
  });

  it("falls back to Web Speech from the main chat voice button when Local ASR is not ready", async () => {
    installMediaDevicesMock("prompt");
    const recognition = installSpeechRecognitionMock();
    render(<App />);
    await screen.findByText("已连接");
    vi.mocked(fetch).mockClear();

    await userEvent.click(screen.getByRole("button", { name: "开始语音 / Start Voice" }));
    act(() => {
      recognition.instances[0].emitResult("Hollow Knight 怎么走", true);
    });

    expect(screen.getByLabelText("聊天输入")).toHaveValue("Hollow Knight 怎么走");
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/voice-input/local-asr/transcribe"),
      expect.objectContaining({ method: "POST" })
    );
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/chat"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("shows the main chat voice button as unavailable when Local ASR and Web Speech are both unavailable", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByText("语音输入：未配置本地 ASR，Web Speech 不可用")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "开始语音 / Start Voice" })).toBeDisabled();
  });

  it("shows Local ASR conversion fallback from the main chat voice button without filling input", async () => {
    setLocalAsrReady();
    localAsrTranscriptionResponseStore = {
      ...localAsrTranscriptionResponse,
      status: "local_asr_transcription_failed",
      available: false,
      display_message: "尚未配置音频转换工具",
      transcript: "",
      transcript_char_count: 0,
      conversion_status: "audio_conversion_not_configured",
      conversion_required: true,
      converted_mime_type: null,
      converter_configured: false,
      safe_converter_name: null
    };
    installAudioCaptureMock();
    render(<App />);
    await screen.findByText("已连接");

    await userEvent.click(await screen.findByRole("button", { name: "开始本地语音 / Start Local ASR" }));
    await userEvent.click(await screen.findByRole("button", { name: "停止本地转写录音 / Stop Local ASR Recording" }));

    await waitFor(() => expect(screen.getByText("语音输入：音频转换工具未配置")).toBeInTheDocument());
    expect(screen.getByLabelText("聊天输入")).toHaveValue("");
    expect(fetch).not.toHaveBeenCalledWith(expect.stringContaining("/api/chat"), expect.objectContaining({ method: "POST" }));
  });

  it("shows no-text and failed Local ASR fallbacks from the main chat voice button", async () => {
    setLocalAsrReady();
    localAsrTranscriptionResponseStore = {
      ...localAsrTranscriptionResponse,
      status: "local_asr_transcription_no_text",
      available: false,
      display_message: "没有识别到可用文本",
      transcript: "",
      transcript_char_count: 0
    };
    installAudioCaptureMock();
    render(<App />);
    await screen.findByText("已连接");

    await userEvent.click(await screen.findByRole("button", { name: "开始本地语音 / Start Local ASR" }));
    await userEvent.click(await screen.findByRole("button", { name: "停止本地转写录音 / Stop Local ASR Recording" }));

    await waitFor(() => expect(screen.getByText("语音输入：没有识别到可用文本")).toBeInTheDocument());
    expect(screen.getByLabelText("聊天输入")).toHaveValue("");

    localAsrTranscriptionResponseStore = {
      ...localAsrTranscriptionResponse,
      status: "local_asr_transcription_failed",
      available: false,
      display_message: "本地语音识别失败",
      transcript: "",
      transcript_char_count: 0,
      conversion_status: "audio_conversion_not_needed",
      conversion_required: false
    };

    await userEvent.click(await screen.findByRole("button", { name: "开始本地语音 / Start Local ASR" }));
    await userEvent.click(await screen.findByRole("button", { name: "停止本地转写录音 / Stop Local ASR Recording" }));

    await waitFor(() => expect(screen.getByText("语音输入：本地转写失败")).toBeInTheDocument());
    expect(screen.getByLabelText("聊天输入")).toHaveValue("");
  });

  it("starts SpeechRecognition when Voice Input is supported", async () => {
    installMediaDevicesMock("prompt");
    const recognition = installSpeechRecognitionMock();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "开始语音 / Start Voice" }));

    expect(recognition.instances).toHaveLength(1);
    expect(recognition.instances[0].lang).toBe("zh-CN");
    expect(recognition.instances[0].interimResults).toBe(true);
    expect(recognition.instances[0].start).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole("button", { name: "停止识别 / Stop Listening" })).toBeInTheDocument();
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "voice_input_started", language: "zh-CN" })])
    );
  });

  it("starts webkitSpeechRecognition when the prefixed API is supported", async () => {
    installMediaDevicesMock("prompt");
    const recognition = installSpeechRecognitionMock("webkit");
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "开始语音 / Start Voice" }));

    expect(recognition.instances).toHaveLength(1);
    expect(recognition.instances[0].start).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("语音识别功能：可用");
  });

  it("shows Voice Input unavailable fallback without crashing", async () => {
    render(<App />);

    await waitFor(() =>
      expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("当前运行环境不支持本地语音识别")
    );
    const voiceButton = screen.getByRole("button", { name: "开始语音 / Start Voice" });

    expect(voiceButton).toBeDisabled();
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("不可用");
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("你仍然可以使用系统听写输入到文本框");
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          type: "voice_input_unavailable",
          status: "当前运行环境不支持本地语音识别"
        })
      ])
    );
  });

  it("shows Voice Input start failure separately from unsupported", async () => {
    installMediaDevicesMock("prompt");
    const recognition = installSpeechRecognitionMock();
    recognition.startError = new Error("start failed");
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "开始语音 / Start Voice" }));

    expect(recognition.instances).toHaveLength(1);
    expect(recognition.instances[0].start).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("语音输入启动失败");
    expect(screen.getByText(/语音输入：语音输入启动失败/)).toBeInTheDocument();
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          type: "voice_input_error",
          reason: "start_failed",
          status: "语音输入启动失败"
        })
      ])
    );
  });

  it("fills final Voice Input transcript into the input without auto sending", async () => {
    installMediaDevicesMock("prompt");
    const recognition = installSpeechRecognitionMock();
    render(<App />);
    await screen.findByText("已连接");

    await userEvent.click(screen.getByRole("button", { name: "开始语音 / Start Voice" }));
    act(() => {
      recognition.instances[0].emitResult("Hollow Knight 里的 Hornet 怎么打？", true);
    });

    expect(screen.getByLabelText("聊天输入")).toHaveValue("Hollow Knight 里的 Hornet 怎么打？");
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/api/chat"),
      expect.objectContaining({ method: "POST" })
    );
    expect(screen.queryByText("Hollow Knight 里的 Hornet 怎么打？")).not.toBeInTheDocument();
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          type: "voice_input_completed",
          character_count: "Hollow Knight 里的 Hornet 怎么打？".length,
          is_final: true
        })
      ])
    );

    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    expect(await screen.findByText("Hollow Knight 里的 Hornet 怎么打？")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/chat"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("keeps interim Voice Input transcript out of chat, memory, retrieval, and game context", async () => {
    installMediaDevicesMock("prompt");
    const recognition = installSpeechRecognitionMock();
    render(<App />);
    await screen.findByText("已连接");
    vi.mocked(fetch).mockClear();

    await userEvent.click(screen.getByRole("button", { name: "开始语音 / Start Voice" }));
    act(() => {
      recognition.instances[0].emitResult("我还没确认", false);
    });

    expect(screen.getByLabelText("聊天输入")).toHaveValue("");
    expect(screen.getByText(/临时识别 5 字/)).toBeInTheDocument();
    const fetchCalls = vi.mocked(fetch).mock.calls;
    expect(fetchCalls.some(([url, init]) => String(url).includes("/api/chat") && init?.method === "POST")).toBe(false);
    expect(fetchCalls.some(([url]) => String(url).includes("/api/memory/pending"))).toBe(false);
    expect(fetchCalls.some(([url]) => String(url).includes("/api/debug/prompt-preview"))).toBe(false);
    expect(fetchCalls.some(([url]) => String(url).includes("/api/game/context"))).toBe(false);
  });

  it("shows readable Voice Input errors without raw reason codes", async () => {
    installMediaDevicesMock("prompt");
    const recognition = installSpeechRecognitionMock();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "开始语音 / Start Voice" }));
    act(() => {
      recognition.instances[0].emitError("not-allowed");
    });

    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("麦克风权限被拒绝");
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          type: "voice_input_error",
          reason: "permission_denied",
          status: "麦克风权限被拒绝"
        })
      ])
    );
    render(
      <EventStreamPanel
        events={eventBus.getRecentEvents(20)}
        open
        onOpenChange={() => undefined}
      />
    );
    const eventStreamTitles = screen.getAllByText("事件流 / Event Stream");
    const eventStream = eventStreamTitles[eventStreamTitles.length - 1].closest("details");
    expect(eventStream).toHaveTextContent("语音输入失败");
    expect(eventStream).toHaveTextContent("麦克风权限被拒绝");
    expect(eventStream).not.toHaveTextContent("permission_denied");
    expect(eventStream).not.toHaveTextContent("not-allowed");
  });

  it("shows Voice Input service unavailable as unavailable instead of available", async () => {
    installMediaDevicesMock("granted");
    const recognition = installSpeechRecognitionMock();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "开始语音 / Start Voice" }));
    act(() => {
      recognition.instances[0].emitError("network");
    });

    const voiceInputSettings = screen.getByRole("group", { name: "语音输入设置" });
    expect(voiceInputSettings).toHaveTextContent("服务不可用");
    expect(voiceInputSettings).toHaveTextContent("语音识别功能：服务不可用");
    expect(voiceInputSettings).toHaveTextContent("麦克风权限：已允许");
    expect(voiceInputSettings).toHaveTextContent("当前运行环境的语音识别服务不可用");
    expect(voiceInputSettings).toHaveTextContent("你仍然可以使用系统听写输入到文本框");
    expect(screen.getByText(/语音输入：未配置本地 ASR，Web Speech 服务不可用/)).toBeInTheDocument();
  });

  it("maps Voice Input no-speech and user stop errors to readable Chinese", async () => {
    installMediaDevicesMock("prompt");
    const recognition = installSpeechRecognitionMock();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "开始语音 / Start Voice" }));
    act(() => {
      recognition.instances[0].emitError("no-speech");
    });
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("没有识别到语音");

    await userEvent.click(screen.getByRole("button", { name: "开始语音 / Start Voice" }));
    act(() => {
      recognition.instances[1].emitError("aborted");
    });
    expect(screen.getByRole("group", { name: "语音输入设置" })).toHaveTextContent("用户停止");

    render(
      <EventStreamPanel
        events={eventBus.getRecentEvents(20)}
        open
        onOpenChange={() => undefined}
      />
    );
    const eventStreamTitles = screen.getAllByText("事件流 / Event Stream");
    const eventStream = eventStreamTitles[eventStreamTitles.length - 1].closest("details");
    expect(eventStream).toHaveTextContent("没有识别到语音");
    expect(eventStream).toHaveTextContent("用户停止");
    expect(eventStream).not.toHaveTextContent("no_speech");
    expect(eventStream).not.toHaveTextContent("aborted");
  });

  it("stops active Voice Output when Voice Input starts", async () => {
    const speech = installSpeechSynthesisMock([mockVoice("zh-CN")]);
    installMediaDevicesMock("prompt");
    installSpeechRecognitionMock();
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "测试语音 / Test Voice" }));
    await waitFor(() => expect(speech.speak).toHaveBeenCalledTimes(1));
    await userEvent.click(screen.getByRole("button", { name: "开始语音 / Start Voice" }));

    expect(speech.cancel).toHaveBeenCalledTimes(1);
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: "tts_stopped", reason: "user_stop" }),
        expect.objectContaining({ type: "voice_input_started" })
      ])
    );
  });

  it("shows Voice Input lifecycle summaries without full transcript in Event Stream", () => {
    render(
      <EventStreamPanel
        events={[
          { type: "voice_input_started", timestamp: new Date().toISOString(), language: "zh-CN" },
          {
            type: "voice_input_completed",
            timestamp: new Date().toISOString(),
            character_count: 21,
            is_final: true,
            language: "zh-CN"
          },
          {
            type: "voice_input_stopped",
            timestamp: new Date().toISOString(),
            reason: "user_stop",
            status: "用户停止",
            language: "zh-CN"
          },
          {
            type: "voice_input_error",
            timestamp: new Date().toISOString(),
            reason: "no_speech",
            status: "没有识别到语音",
            language: "zh-CN"
          },
          {
            type: "voice_input_unavailable",
            timestamp: new Date().toISOString(),
            reason: "not_supported",
            status: "当前运行环境不支持本地语音识别",
            language: "zh-CN"
          }
        ]}
        open
        onOpenChange={() => undefined}
      />
    );

    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    expect(eventStream).toHaveTextContent("语音输入开始");
    expect(eventStream).toHaveTextContent("语音输入完成");
    expect(eventStream).toHaveTextContent("识别文本 21 字");
    expect(eventStream).toHaveTextContent("语音输入已停止");
    expect(eventStream).toHaveTextContent("语音输入失败");
    expect(eventStream).toHaveTextContent("语音输入不可用");
    expect(eventStream).not.toHaveTextContent("Hollow Knight 里的 Hornet 怎么打？");
    expect(eventStream).not.toHaveTextContent("user_stop");
    expect(eventStream).not.toHaveTextContent("no_speech");
    expect(eventStream).not.toHaveTextContent("not_supported");
    expect(eventStream).not.toHaveTextContent("raw_prompt");
    expect(eventStream).not.toHaveTextContent("DEEPSEEK_API_KEY");
    expect(eventStream).not.toHaveTextContent("services/backend/.env");
    expect(eventStream).not.toHaveTextContent("Authorization");
  });

  it("falls back to the system default voice when voices are empty", async () => {
    const speech = installSpeechSynthesisMock([]);
    appSettingsStore = { ...appSettingsStore, voice_output: "on" };
    render(<App />);

    expect(await screen.findByText(/等待系统语音列表/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");

    await waitFor(() => expect(speech.speak).toHaveBeenCalledTimes(1));
    expect(speech.speak.mock.calls[0][0]).toMatchObject({ lang: "zh-CN", voice: null });
  });

  it("emits TTS started only after the system reports playback started", () => {
    const speech = installSpeechSynthesisMock([mockVoice("zh-CN")]);

    expect(voiceOutput.speak("你好", { source: "test_voice" })).toBe(true);
    expect(voiceOutput.getStatus()).toMatchObject({ active: true, phase: "starting" });
    expect(eventBus.getRecentEvents(20)).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "tts_started" })])
    );

    act(() => {
      speech.speak.mock.calls[0][0].onstart?.({} as SpeechSynthesisEvent);
    });

    expect(voiceOutput.getStatus()).toMatchObject({ active: true, phase: "playing" });
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "tts_started", source: "test_voice" })])
    );

    act(() => {
      speech.speak.mock.calls[0][0].onend?.({} as SpeechSynthesisEvent);
    });

    expect(voiceOutput.getStatus()).toMatchObject({ active: false, phase: "idle" });
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "tts_completed", source: "test_voice" })])
    );
  });

  it("reports a readable TTS error when playback never starts", () => {
    vi.useFakeTimers();
    installSpeechSynthesisMock([mockVoice("zh-CN")]);

    expect(voiceOutput.speak("你好", { source: "test_voice" })).toBe(true);

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(voiceOutput.getStatus()).toMatchObject({
      active: false,
      phase: "idle",
      lastError: "语音没有开始，请检查系统声音输出或语音包"
    });
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          type: "tts_error",
          reason: "start_timeout",
          status: "语音没有开始，请检查系统声音输出或语音包",
          source: "test_voice"
        })
      ])
    );
  });

  it("emits TTS error from the system speech error callback", () => {
    const speech = installSpeechSynthesisMock([mockVoice("zh-CN")]);

    expect(voiceOutput.speak("你好", { source: "test_voice" })).toBe(true);
    act(() => {
      speech.speak.mock.calls[0][0].onerror?.({ error: "speech_error" } as unknown as SpeechSynthesisErrorEvent);
    });

    expect(voiceOutput.getStatus()).toMatchObject({ active: false, phase: "idle", lastError: "播放失败" });
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: "tts_error", reason: "speech_error", status: "播放失败", source: "test_voice" })
      ])
    );
  });

  it("speaks assistant replies when Voice Output is enabled", async () => {
    const speech = installSpeechSynthesisMock([
      mockVoice("en-US"),
      mockVoice("zh-Hans"),
      mockVoice("zh-CN")
    ]);
    appSettingsStore = { ...appSettingsStore, voice_output: "on", voice_rate: 1.2, voice_volume: 0.6 };
    render(<App />);

    expect(await screen.findByText(/优先使用中文语音/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");

    await waitFor(() => expect(speech.speak).toHaveBeenCalledTimes(1));
    expect(speech.speak.mock.calls[0][0]).toMatchObject({
      text: "别急着翻滚。先看动作。再试一次。",
      rate: 1.2,
      volume: 0.6,
      lang: "zh-CN",
      voice: expect.objectContaining({ lang: "zh-CN" })
    });
    expect(screen.getAllByRole("button", { name: "停止语音 / Stop Voice" }).length).toBeGreaterThan(0);
    expect(eventBus.getRecentEvents(20)).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "tts_started" })])
    );

    act(() => {
      speech.speak.mock.calls[0][0].onstart?.({} as SpeechSynthesisEvent);
    });

    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "tts_started", character_count: 16, source: "assistant_reply" })])
    );

    act(() => {
      speech.speak.mock.calls[0][0].onend?.({} as SpeechSynthesisEvent);
    });

    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "tts_completed", character_count: 16 })])
    );
  });

  it("keeps Voice Output enabled when older settings responses omit the field", async () => {
    const speech = installSpeechSynthesisMock();
    omitVoiceOutputFromSettings = true;
    render(<App />);

    await userEvent.selectOptions(await screen.findByLabelText("语音输出 / Voice Output"), "on");
    await waitFor(() => expect(screen.getByLabelText("语音输出 / Voice Output")).toHaveValue("on"));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ voice_output: "on" }) })
      )
    );
    fireEvent.change(screen.getByLabelText("语速 / Rate"), { target: { value: "1.3" } });
    await waitFor(() => expect(screen.getByLabelText("语速 / Rate")).toHaveValue("1.3"));
    fireEvent.change(screen.getByLabelText("音量 / Volume"), { target: { value: "0.5" } });
    await waitFor(() => expect(screen.getByLabelText("音量 / Volume")).toHaveValue("0.5"));

    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");

    await waitFor(() => expect(speech.speak).toHaveBeenCalledTimes(1));
    expect(speech.speak.mock.calls[0][0]).toMatchObject({ rate: 1.3, volume: 0.5 });
    act(() => {
      speech.speak.mock.calls[0][0].onstart?.({} as SpeechSynthesisEvent);
    });
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "tts_started", character_count: 16 })])
    );
  });

  it("does not repeat speech for the same assistant reply after a rerender", async () => {
    const speech = installSpeechSynthesisMock();
    appSettingsStore = { ...appSettingsStore, voice_output: "on" };
    const { rerender } = render(<App />);

    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");
    await waitFor(() => expect(speech.speak).toHaveBeenCalledTimes(1));

    rerender(<App />);

    await waitFor(() => expect(speech.speak).toHaveBeenCalledTimes(1));
  });

  it("stops active speech from the Stop Voice control", async () => {
    const speech = installSpeechSynthesisMock();
    appSettingsStore = { ...appSettingsStore, voice_output: "on" };
    render(<App />);

    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");
    await waitFor(() => expect(speech.speak).toHaveBeenCalledTimes(1));

    await userEvent.click(screen.getAllByRole("button", { name: "停止语音 / Stop Voice" })[0]);

    expect(speech.cancel).toHaveBeenCalledTimes(1);
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "tts_stopped", reason: "user_stop" })])
    );
  });

  it("sending a new user message cancels active speech", async () => {
    const speech = installSpeechSynthesisMock();
    appSettingsStore = { ...appSettingsStore, voice_output: "on" };
    render(<App />);

    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");
    await waitFor(() => expect(speech.speak).toHaveBeenCalledTimes(1));

    await userEvent.type(screen.getByLabelText("聊天输入"), "再说一遍");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));

    expect(speech.cancel).toHaveBeenCalledTimes(1);
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "tts_stopped", reason: "new_message" })])
    );
  });

  it("disabling Voice Output cancels active speech", async () => {
    const speech = installSpeechSynthesisMock();
    appSettingsStore = { ...appSettingsStore, voice_output: "on" };
    render(<App />);

    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");
    await waitFor(() => expect(speech.speak).toHaveBeenCalledTimes(1));

    await userEvent.selectOptions(screen.getByLabelText("语音输出 / Voice Output"), "off");

    await waitFor(() => expect(speech.cancel).toHaveBeenCalledTimes(1));
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "tts_stopped", reason: "disabled" })])
    );
  });

  it("shows TTS lifecycle summaries without full assistant text in Event Stream", async () => {
    render(
      <EventStreamPanel
        events={[
          { type: "tts_started", timestamp: new Date().toISOString(), character_count: 16 },
          { type: "tts_completed", timestamp: new Date().toISOString(), character_count: 16, source: "test_voice" },
          { type: "tts_stopped", timestamp: new Date().toISOString(), character_count: 16, reason: "user_stop" },
          { type: "tts_stopped", timestamp: new Date().toISOString(), character_count: 16, reason: "new_message" },
          { type: "tts_stopped", timestamp: new Date().toISOString(), character_count: 16, reason: "disabled" },
          {
            type: "tts_error",
            timestamp: new Date().toISOString(),
            character_count: 16,
            reason: "unavailable",
            status: "当前环境不支持"
          }
        ]}
        open
        onOpenChange={() => undefined}
      />
    );
    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    expect(eventStream).not.toBeNull();
    expect(eventStream).toHaveTextContent("语音开始播放");
    expect(eventStream).toHaveTextContent("语音播放完成");
    expect(eventStream).toHaveTextContent("语音已停止");
    expect(eventStream).toHaveTextContent("测试语音");
    expect(eventStream).toHaveTextContent("新消息打断");
    expect(eventStream).toHaveTextContent("已关闭");
    expect(eventStream).toHaveTextContent("语音播放失败");
    expect(eventStream).toHaveTextContent("16 字");
    expect(eventStream).not.toHaveTextContent("user_stop");
    expect(eventStream).not.toHaveTextContent("new_message");
    expect(eventStream).not.toHaveTextContent("disabled");
    expect(eventStream).not.toHaveTextContent("unavailable");
    expect(eventStream).not.toHaveTextContent("test_voice");
    expect(eventStream).not.toHaveTextContent("你好，我是 Rei。语音输出测试。");
    expect(eventStream).not.toHaveTextContent("别急着翻滚。先看动作。再试一次。");
    expect(eventStream).not.toHaveTextContent("raw_prompt");
    expect(eventStream).not.toHaveTextContent("DEEPSEEK_API_KEY");
    expect(eventStream).not.toHaveTextContent("services/backend/.env");
  });

  it("emits pending memory creation only after a chat operation discovers new pending memory", async () => {
    let chatCompleted = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith("/api/memory/pending")) {
          return Response.json(chatCompleted ? pendingMemories : []);
        }
        if (url.endsWith("/api/chat") && init?.method === "POST") {
          chatCompleted = true;
          return Response.json(chatResponse);
        }
        return defaultFetchResponse(url, init);
      })
    );

    render(<App />);
    await screen.findByText("已连接");
    expect(eventBus.getRecentEvents(20).some((event) => event.type === "pending_memory_created")).toBe(false);

    await userEvent.type(screen.getByLabelText("聊天输入"), "我不喜欢长篇攻略");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("玩家不喜欢长篇攻略");

    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          type: "pending_memory_created",
          memory_type: "user_preference",
          text: "玩家不喜欢长篇攻略"
        })
      ])
    );
  });

  it("renders Event Stream collapsed by default and shows sanitized recent events", async () => {
    render(<App />);
    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");

    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    expect(eventStream).not.toBeNull();
    expect(eventStream).not.toHaveAttribute("open");
    expect(screen.getByText("原始 JSON")).toBeInTheDocument();

    fireEvent.click(screen.getByText("事件流 / Event Stream"));

    expect(eventStream).toHaveAttribute("open");
    await waitFor(() =>
      expect(within(eventStream as HTMLElement).getByRole("list", { name: "事件流列表" })).toBeInTheDocument()
    );
    expect(eventStream).toHaveTextContent("用户发送消息");
    expect(eventStream).toHaveTextContent("Rei 显示回复片段");
    expect(eventStream).toHaveTextContent("使用游戏知识");
    expect(eventStream).toHaveTextContent("已使用本地知识");
    expect(eventStream).toHaveTextContent(/用户消息 \d+ 字/);
    expect(eventStream).not.toHaveTextContent("user_message_sent");
    expect(eventStream).not.toHaveTextContent("assistant_reply_segment_shown");
    expect(eventStream).not.toHaveTextContent("bundled");
    expect(eventStream).not.toHaveTextContent("Margit 怎么打？");
    expect(eventStream).not.toHaveTextContent("别急着翻滚。先看动作。再试一次。");
    expect(eventStream).not.toHaveTextContent("DEEPSEEK_API_KEY");
    expect(eventStream).not.toHaveTextContent("raw_prompt");
    expect(eventStream).not.toHaveTextContent("services/backend/.env");
  });

  it("shows readable knowledge retrieval reasons in Event Stream", () => {
    render(
      <EventStreamPanel
        events={[
          {
            type: "knowledge_used",
            timestamp: new Date().toISOString(),
            game: "艾尔登法环",
            topics: ["相关性不足，未使用", "这次不是游戏知识问题"]
          },
          {
            type: "knowledge_used",
            timestamp: new Date().toISOString(),
            topics: ["未命中本地知识"]
          }
        ]}
        open
        onOpenChange={() => undefined}
      />
    );

    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    expect(eventStream).toHaveTextContent("使用游戏知识");
    expect(eventStream).toHaveTextContent("艾尔登法环 / 相关性不足，未使用、这次不是游戏知识问题");
    expect(eventStream).toHaveTextContent("未命中本地知识");
    expect(eventStream).not.toHaveTextContent("无 / 未命中本地知识");
    expect(eventStream).not.toHaveTextContent("below_threshold");
    expect(eventStream).not.toHaveTextContent("not_game_related");
    expect(eventStream).not.toHaveTextContent("raw_prompt");
    expect(eventStream).not.toHaveTextContent("DEEPSEEK_API_KEY");
  });

  it("sanitizes Overlay error summaries in Event Stream", () => {
    render(
      <EventStreamPanel
        events={[
          {
            type: "overlay_error",
            timestamp: new Date().toISOString(),
            reason: "raw stderr from /Users/aragoto/Library/Application Support/ReiLink/.env with API key"
          }
        ]}
        open
        onOpenChange={() => undefined}
      />
    );

    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    expect(eventStream).toHaveTextContent("悬浮层失败");
    expect(eventStream).not.toHaveTextContent("raw stderr");
    expect(eventStream).not.toHaveTextContent("/Users/aragoto");
    expect(eventStream).not.toHaveTextContent("Application Support");
    expect(eventStream).not.toHaveTextContent(".env");
    expect(eventStream).not.toHaveTextContent("API key");
  });

  it("shows a safe Overlay suppression summary in Event Stream", () => {
    render(
      <EventStreamPanel
        events={[
          {
            type: "overlay_visibility_suppressed",
            timestamp: new Date().toISOString(),
            reason: "main_window_active"
          }
        ]}
        open
        onOpenChange={() => undefined}
      />
    );

    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    expect(eventStream).toHaveTextContent("悬浮层暂时隐藏");
    expect(eventStream).toHaveTextContent("主窗口前台或 macOS 安全模式，悬浮层暂时隐藏");
    expect(eventStream).not.toHaveTextContent("main_window_active");
    expect(eventStream).not.toHaveTextContent(".env");
    expect(eventStream).not.toHaveTextContent("/Users/aragoto");
    expect(eventStream).not.toHaveTextContent("raw stderr");
  });

  it("shows an empty Event Stream state when there are no events", () => {
    render(<EventStreamPanel events={[]} open onOpenChange={() => undefined} />);

    expect(screen.getByText("事件流 / Event Stream")).toBeInTheDocument();
    expect(screen.getByText("暂无事件")).toBeInTheDocument();
  });

  it("shows, updates, sanitizes, and clears the Session Timeline", async () => {
    render(<App />);
    await screen.findByText("已连接");

    const timeline = screen.getByText("Session Timeline / 本局时间线").closest("details");
    expect(timeline).not.toBeNull();
    expect(timeline).not.toHaveAttribute("open");

    fireEvent.click(screen.getByText("Session Timeline / 本局时间线"));
    expect(timeline).toHaveAttribute("open");
    await waitFor(() => expect(screen.getByText("本局还没有记录到关键变化。")).toBeInTheDocument());

    act(() => {
      eventBus.emit({
        type: "user_message_sent",
        timestamp: new Date().toISOString(),
        text: "我在打 Margit"
      });
      eventBus.emit({
        type: "game_context_changed",
        timestamp: new Date().toISOString(),
        game: "Elden Ring",
        source: "detector"
      });
      eventBus.emit({
        type: "game_session_changed",
        timestamp: new Date().toISOString(),
        game: "Elden Ring",
        current_boss: "Margit",
        activity: "boss_cleared",
        death_count: 2,
        frustration_count: 1,
        last_cleared_boss: "Margit"
      });
      eventBus.emit({
        type: "knowledge_used",
        timestamp: new Date().toISOString(),
        game: "艾尔登法环",
        topics: ["已使用本地知识", "Margit phase 2 tips /Users/aragoto/Desktop/ReiLink/services/backend/.env raw prompt"]
      });
      eventBus.emit({
        type: "proactive_message_shown",
        timestamp: new Date().toISOString(),
        trigger_type: "repeated_death",
        text: "没关系吧？完整 proactive 文本不应该进入 timeline。"
      });
      eventBus.emit({
        type: "pending_memory_accepted",
        timestamp: new Date().toISOString(),
        memory_id: "pending-1"
      });
      eventBus.emit({
        type: "pending_memory_ignored",
        timestamp: new Date().toISOString(),
        memory_id: "pending-1"
      });
    });

    await waitFor(() => expect(timeline).toHaveTextContent("切换游戏：Elden Ring"));
    expect(timeline).toHaveTextContent("检测到 Boss：Margit");
    expect(timeline).toHaveTextContent("死亡次数更新：2");
    expect(timeline).toHaveTextContent("挫败状态升高：1");
    expect(timeline).toHaveTextContent("击败 Boss：Margit");
    expect(timeline).toHaveTextContent("使用知识：艾尔登法环 / Margit phase 2 tips");
    expect(timeline).toHaveTextContent("主动陪伴已显示：反复死亡");
    expect(timeline).toHaveTextContent("记忆已接受");
    expect(timeline).toHaveTextContent("记忆已忽略");
    expect(timeline).not.toHaveTextContent("/Users/aragoto");
    expect(timeline).not.toHaveTextContent(".env");
    expect(timeline).not.toHaveTextContent("raw prompt");
    expect(timeline).not.toHaveTextContent("没关系吧");
    expect(timeline).not.toHaveTextContent("pending-1");

    fireEvent.click(screen.getByText("事件流 / Event Stream"));
    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    await waitFor(() => expect(eventStream).toHaveTextContent("游戏状态变化"));
    expect(eventStream).toHaveTextContent("使用游戏知识");

    fireEvent.click(screen.getByRole("button", { name: "清空时间线" }));
    expect(timeline).toHaveTextContent("本局还没有记录到关键变化。");
  });

  it("updates Event Stream when interaction events are emitted", async () => {
    render(<App />);
    await screen.findByText("已连接");
    fireEvent.click(screen.getByText("事件流 / Event Stream"));

    act(() => {
      eventBus.emit({
        type: "user_message_sent",
        timestamp: new Date().toISOString(),
        text: "我现在卡在女武神"
      });
      eventBus.emit({
        type: "assistant_reply_segment_shown",
        timestamp: new Date().toISOString(),
        segment_index: 0,
        text: "先别贪刀。"
      });
      eventBus.emit({
        type: "runtime_status_changed",
        timestamp: new Date().toISOString(),
        backend_source: "bundled_binary",
        knowledge_source: "bundled"
      });
      eventBus.emit({
        type: "backend_status_changed",
        timestamp: new Date().toISOString(),
        status: "starting"
      });
    });

    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    expect(eventStream).not.toBeNull();
    await waitFor(() => expect(eventStream).toHaveTextContent("用户发送消息"));
    expect(eventStream).toHaveTextContent("Rei 显示回复片段");
    expect(eventStream).toHaveTextContent("运行来源变化");
    expect(eventStream).toHaveTextContent("内置后端 / 内置知识资源");
    expect(eventStream).not.toHaveTextContent("bundled_binary");
    expect(eventStream).toHaveTextContent("后端状态变化");
    expect(eventStream).toHaveTextContent("正在启动");
    expect(eventStream).not.toHaveTextContent("starting");
    expect(eventStream).toHaveTextContent(/用户消息 \d+ 字/);
    expect(eventStream).not.toHaveTextContent("我现在卡在女武神");
    expect(eventStream).toHaveTextContent("第 1 段 / 5 字");
    expect(eventStream).not.toHaveTextContent("先别贪刀。");
  });

  it("shows only the latest 20 Event Stream rows", async () => {
    render(<App />);
    await screen.findByText("已连接");

    act(() => {
      for (let index = 0; index < 25; index += 1) {
        eventBus.emit({
          type: "user_message_sent",
          timestamp: new Date(Date.UTC(2026, 5, 1, 9, index)).toISOString(),
          text: `event-${index}`
        });
      }
    });

    fireEvent.click(screen.getByText("事件流 / Event Stream"));

    const eventStream = screen.getByText("事件流 / Event Stream").closest("details");
    expect(eventStream).not.toBeNull();
    await waitFor(() =>
      expect(within(eventStream as HTMLElement).getAllByRole("listitem")).toHaveLength(20)
    );
    const rows = within(eventStream as HTMLElement).getAllByRole("listitem");
    expect(rows).toHaveLength(20);
    expect(eventStream).not.toHaveTextContent("event-4");
    expect(eventStream).not.toHaveTextContent("event-5");
    expect(eventStream).not.toHaveTextContent("event-24");
    expect(rows[0]).toHaveTextContent("用户发送消息");
    expect(rows[19]).toHaveTextContent("用户发送消息");
  });

  it("forces chat scroll to bottom when the user sends a message", async () => {
    render(<App />);
    const messageLog = await screen.findByRole("log", { name: "聊天消息列表" });
    setChatScroll(messageLog, { scrollHeight: 1400, clientHeight: 400, scrollTop: 120 });
    scrollToMock.mockClear();

    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));

    await waitFor(() => expect(scrollToMock).toHaveBeenCalled());
    expect(scrollToMock).toHaveBeenCalledWith(expect.objectContaining({ top: 1400, behavior: "smooth" }));
    await screen.findByText("别急着翻滚。先看动作。再试一次。");
    expect(screen.getByLabelText("聊天输入")).not.toBeDisabled();
  });

  it("does not force scroll when a proactive message arrives while reading history", async () => {
    vi.useFakeTimers();
    appSettingsStore = { ...appSettings, proactive_companion: "on" };
    proactiveStatusStore = {
      ...proactiveStatus,
      enabled: true,
      active_candidate_triggers: ["repeated_death"]
    };
    proactiveCheckStore = {
      should_send: true,
      trigger_type: "repeated_death",
      message: "没关系吧？",
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
    const messageLog = screen.getByRole("log", { name: "聊天消息列表" });
    setChatScroll(messageLog, { scrollHeight: 1400, clientHeight: 400, scrollTop: 200 });
    scrollToMock.mockClear();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });

    expect(screen.getByText("没关系吧？")).toBeInTheDocument();
    expect(scrollToMock).not.toHaveBeenCalled();
  });

  it("scrolls to bottom when a proactive message arrives near the bottom", async () => {
    vi.useFakeTimers();
    appSettingsStore = { ...appSettings, proactive_companion: "on" };
    proactiveStatusStore = {
      ...proactiveStatus,
      enabled: true,
      active_candidate_triggers: ["repeated_death"]
    };
    proactiveCheckStore = {
      should_send: true,
      trigger_type: "repeated_death",
      message: "没关系吧？",
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
    const messageLog = screen.getByRole("log", { name: "聊天消息列表" });
    setChatScroll(messageLog, { scrollHeight: 1400, clientHeight: 400, scrollTop: 920 });
    scrollToMock.mockClear();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });

    expect(screen.getByText("没关系吧？")).toBeInTheDocument();
    expect(scrollToMock).toHaveBeenCalledWith(expect.objectContaining({ top: 1400, behavior: "smooth" }));
  });

  it("shows localized model errors without raw exception text in chat", async () => {
    chatFailureResponse = () =>
      new Response(JSON.stringify({ detail: "DeepSeek API key missing. Set DEEPSEEK_API_KEY." }), {
        status: 400,
        headers: { "Content-Type": "application/json" }
      });

    render(<App />);
    await userEvent.type(await screen.findByLabelText("聊天输入"), "你好");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));

    const chatPanel = screen.getByRole("region", { name: "聊天面板" });
    await waitFor(() => expect(within(chatPanel).getAllByText("模型 API Key 未配置").length).toBeGreaterThan(0));
    expect(within(chatPanel).queryByText(/DeepSeek API key missing/)).not.toBeInTheDocument();
    expect(screen.getByText("原始 JSON").closest("details")).not.toHaveAttribute("open");
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
      message: "没关系吧？",
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

    const proactiveMessage = screen.getByText("没关系吧？");
    const bubble = proactiveMessage.closest("article");
    expect(screen.getByText(/主动 · 反复死亡/)).toBeInTheDocument();
    expect(bubble).toHaveClass("messageBubble", "assistant", "proactive");
    expect(bubble).not.toHaveClass("system");
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          type: "proactive_message_shown",
          trigger_type: "repeated_death",
          text: "没关系吧？"
        })
      ])
    );
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
        const setup = setupStatusResponse(url);
        if (setup) return Promise.resolve(setup);
        if (url.endsWith("/api/health")) return Promise.resolve(Response.json({ status: "ok" }));
        if (url.endsWith("/api/local-data/status")) return Promise.resolve(Response.json(localDataStatus));
        {
          const localAsrSettingsValue = localAsrSettingsResponse(url, init);
          if (localAsrSettingsValue) return Promise.resolve(localAsrSettingsValue);
        }
        if (url.endsWith("/api/voice-input/local-asr/status")) {
          return Promise.resolve(Response.json(localAsrStatusStore));
        }
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
        const setup = setupStatusResponse(url);
        if (setup) return Promise.resolve(setup);
        if (url.endsWith("/api/health")) return Promise.resolve(Response.json({ status: "ok" }));
        if (url.endsWith("/api/local-data/status")) return Promise.resolve(Response.json(localDataStatus));
        {
          const localAsrSettingsValue = localAsrSettingsResponse(url, init);
          if (localAsrSettingsValue) return Promise.resolve(localAsrSettingsValue);
        }
        if (url.endsWith("/api/voice-input/local-asr/status")) {
          return Promise.resolve(Response.json(localAsrStatusStore));
        }
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
        const setup = setupStatusResponse(url);
        if (setup) return Promise.resolve(setup);
        if (url.endsWith("/api/health")) return Promise.resolve(Response.json({ status: "ok" }));
        if (url.endsWith("/api/local-data/status")) return Promise.resolve(Response.json(localDataStatus));
        {
          const localAsrSettingsValue = localAsrSettingsResponse(url, init);
          if (localAsrSettingsValue) return Promise.resolve(localAsrSettingsValue);
        }
        if (url.endsWith("/api/voice-input/local-asr/status")) {
          return Promise.resolve(Response.json(localAsrStatusStore));
        }
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
    expect(screen.getByRole("status", { name: "后端状态提示" })).toHaveTextContent("后端未连接");
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
    expect(screen.getAllByText("检索结果").length).toBeGreaterThan(0);
    expect(screen.getAllByText("未使用原因").length).toBeGreaterThan(0);
    expect(screen.getAllByText("已使用本地知识").length).toBeGreaterThan(0);
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
    expect(screen.getAllByText("检索结果").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Elden Ring").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Boss 攻略").length).toBeGreaterThan(0);
    expect(screen.getByText("记忆摘要")).toBeInTheDocument();
    expect(screen.getByText("注入记忆")).toBeInTheDocument();
    expect(screen.getByText("跳过记忆")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "待确认记忆" })).toBeInTheDocument();
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
        const setup = setupStatusResponse(url);
        if (setup) return setup;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/local-data/status")) return Response.json(localDataStatus);
        {
          const localAsrSettingsValue = localAsrSettingsResponse(url, init);
          if (localAsrSettingsValue) return localAsrSettingsValue;
        }
        if (url.endsWith("/api/voice-input/local-asr/status")) return Response.json(localAsrStatusStore);
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
        const setup = setupStatusResponse(url);
        if (setup) return setup;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/local-data/status")) return Response.json(localDataStatus);
        {
          const localAsrSettingsValue = localAsrSettingsResponse(url, init);
          if (localAsrSettingsValue) return localAsrSettingsValue;
        }
        if (url.endsWith("/api/voice-input/local-asr/status")) return Response.json(localAsrStatusStore);
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
        const setup = setupStatusResponse(url);
        if (setup) return setup;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/local-data/status")) return Response.json(localDataStatus);
        {
          const localAsrSettingsValue = localAsrSettingsResponse(url, init);
          if (localAsrSettingsValue) return localAsrSettingsValue;
        }
        if (url.endsWith("/api/voice-input/local-asr/status")) return Response.json(localAsrStatusStore);
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
        const setup = setupStatusResponse(url);
        if (setup) return setup;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/local-data/status")) return Response.json(localDataStatus);
        {
          const localAsrSettingsValue = localAsrSettingsResponse(url, init);
          if (localAsrSettingsValue) return localAsrSettingsValue;
        }
        if (url.endsWith("/api/voice-input/local-asr/status")) return Response.json(localAsrStatusStore);
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
        const setup = setupStatusResponse(url);
        if (setup) return setup;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/local-data/status")) return Response.json(localDataStatus);
        {
          const localAsrSettingsValue = localAsrSettingsResponse(url, init);
          if (localAsrSettingsValue) return localAsrSettingsValue;
        }
        if (url.endsWith("/api/voice-input/local-asr/status")) return Response.json(localAsrStatusStore);
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
        const setup = setupStatusResponse(url);
        if (setup) return setup;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/local-data/status")) return Response.json(localDataStatus);
        {
          const localAsrSettingsValue = localAsrSettingsResponse(url, init);
          if (localAsrSettingsValue) return localAsrSettingsValue;
        }
        if (url.endsWith("/api/voice-input/local-asr/status")) return Response.json(localAsrStatusStore);
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

  it("emits pending memory accept and ignore events from the memory panel", async () => {
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "保存" }));

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/memory/pending/pending-1/accept"),
        expect.objectContaining({ method: "POST" })
      )
    );
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "pending_memory_accepted", memory_id: "pending-1" })])
    );

    await userEvent.click(screen.getByRole("button", { name: "忽略" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/memory/pending/pending-1/ignore"),
        expect.objectContaining({ method: "POST" })
      )
    );
    expect(eventBus.getRecentEvents(20)).toEqual(
      expect.arrayContaining([expect.objectContaining({ type: "pending_memory_ignored", memory_id: "pending-1" })])
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
        const setup = setupStatusResponse(url);
        if (setup) return setup;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/local-data/status")) return Response.json(localDataStatus);
        {
          const localAsrSettingsValue = localAsrSettingsResponse(url, init);
          if (localAsrSettingsValue) return localAsrSettingsValue;
        }
        if (url.endsWith("/api/voice-input/local-asr/status")) return Response.json(localAsrStatusStore);
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
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<App />);
    await screen.findByRole("button", { name: /调试面板/i });
    const debugActions = screen.getByRole("heading", { name: "调试操作" }).closest("section");
    expect(debugActions).not.toBeNull();

    await userEvent.click(within(debugActions as HTMLElement).getByRole("button", { name: "重置游戏状态" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/debug/game-session/reset"),
        expect.objectContaining({ method: "POST" })
      )
    );

    await userEvent.click(within(debugActions as HTMLElement).getByRole("button", { name: "重置记忆" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/memory/reset"),
        expect.objectContaining({ method: "POST" })
      )
    );

    await userEvent.click(within(debugActions as HTMLElement).getByRole("button", { name: "清空待确认记忆" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/memory/pending/clear"),
        expect.objectContaining({ method: "POST" })
      )
    );
  });
});
