import {
  Bot,
  Brain,
  Bug,
  ChevronDown,
  ChevronUp,
  Database,
  FileText,
  FolderOpen,
  Gamepad2,
  KeyRound,
  MessageSquare,
  Mic,
  RefreshCw,
  Send,
  Settings,
  Sparkles,
  Volume2,
  VolumeX,
  X
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  api,
  ApiRequestError,
  AppSettings,
  AudioProbeResponse,
  ChatDebugResponse,
  GameContextResponse,
  GameDetectionResponse,
  GameSessionDebugResponse,
  GameStatus,
  LocalAsrProbeResponse,
  LocalAsrSettings,
  LocalAsrSettingsUpdate,
  LocalAsrStatus,
  LocalAsrTranscriptionResponse,
  LocalDataStatus,
  MemoryDebugResponse,
  PendingMemory,
  PromptPreviewResponse,
  ProactiveStatusResponse,
  ProviderDebugResponse,
  SemanticExtractionDebugResponse,
  SetupStatus,
  UserProfileMemory
} from "../shared/api";
import type { ReiLinkEvent } from "../shared/events";
import { sanitizeOverlayText, type OverlayContentUpdate, type OverlayMessageSource } from "../shared/overlay";
import type { BackendRuntimeStatus } from "../shared/runtime";
import { audioCapture, MAX_RECORDING_DURATION_MS, type AudioCaptureStatus } from "./audioCapture";
import { eventBus } from "./eventBus";
import { voiceInput, type VoiceInputStatus } from "./voiceInput";
import { voiceOutput, type VoiceOutputStatus, type VoiceStopReason } from "./voiceOutput";

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: string;
  pending?: boolean;
  messageType?: "chat" | "proactive";
  triggerType?: string;
};

type DemoResetAction =
  | "reset-onboarding"
  | "clear-chat"
  | "reset-game-session"
  | "clear-pending"
  | "reset-memory"
  | "reset-proactive"
  | "reset-demo";

type LocalAsrTranscriptionPhase = "idle" | "recording" | "transcribing";
type MainVoiceInputProvider = "local_asr" | "web_speech" | "unavailable";
type LocalAsrSettingsDraft = {
  local_asr_binary_path: string;
  local_asr_model_path: string;
  audio_converter_binary_path: string;
};

const LOCAL_ASR_UI_LANGUAGE = "zh-CN";

const idleStatus: GameStatus = {
  game_id: null,
  game_name: null,
  process_name: null,
  status: "idle",
  confidence: 0,
  tags: []
};

const emptyGameDetection: GameDetectionResponse = {
  status: "idle",
  detected_game_id: null,
  display_name: null,
  process_name: null,
  match_confidence: 0,
  match_source: "none",
  knowledge_game_id: null,
  detected_at: new Date(0).toISOString()
};

const emptyGameContext: GameContextResponse = {
  active_game_id: null,
  active_game_display_name: null,
  active_source: "none",
  manual_override: {
    enabled: false,
    game_id: null,
    display_name: null,
    set_at: null,
    source: "user"
  },
  detected_game: emptyGameDetection,
  session_game: null,
  previous_game: null,
  game_switched: false,
  user_message_game_id: null,
  user_message_game_display_name: null,
  support_status: null,
  knowledge_available: false,
  fallback_reason: "no_game_detected",
  warnings: [],
  available_games: []
};

const emptyProfile: UserProfileMemory = {
  user_name: null,
  favorite_game: null,
  preferred_tone: null,
  likes_teasing: null,
  skill_level: null,
  current_boss: null,
  repeated_struggles: [],
  emotional_notes: [],
  last_seen_at: null,
  memory_updated_at: {}
};

const emptyMemoryDebug: MemoryDebugResponse = {
  prompt_order: [],
  memory_written: false,
  current_boss: null,
  emotional_note: null,
  recent_episode_count: 0,
  items: []
};

const emptyChatDebug: ChatDebugResponse = {
  intent: null,
  selected_model: null,
  model_used: null,
  main_reply_model: null,
  model_route_mode: null,
  route_reason: null,
  route_intent: null,
  estimated_complexity: null,
  fallback_reason: null,
  thinking_enabled: false,
  reasoning_effort: null,
  prompt_tokens_estimate: 0,
  llm_latency_ms: 0,
  provider_latency_ms: 0,
  memory_latency_ms: 0,
  total_latency_ms: 0,
  response_latency_ms: 0,
  request_started_at: null,
  reply_segments_count: 0,
  segmenter_mode: null,
  semantic_extraction_called: false,
  semantic_extraction_model: null,
  semantic_extraction_latency_ms: 0,
  semantic_extraction_parse_error: null,
  knowledge_matched: false,
  knowledge_game_id: null,
  knowledge_game_display_name: null,
  knowledge_match_source: null,
  knowledge_path: null,
  manifest_path: null,
  manifest_status: "unknown",
  knowledge_pack_version: "unknown",
  knowledge_pack_language: "unknown",
  knowledge_pack_status: "unknown",
  coverage: [],
  last_updated: "unknown",
  knowledge_supported_games_count: 0,
  knowledge_fallback_reason: null,
  knowledge_confidence: 0,
  active_game_id: null,
  active_game_display_name: null,
  active_source: null,
  support_status: null,
  knowledge_available: false,
  matched_topics: [],
  snippets_count: 0,
  snippet_titles: [],
  snippet_previews: [],
  matched_terms: [],
  result_scores: [],
  knowledge_used_in_prompt: false,
  knowledge_retrieval_status: "not_found",
  knowledge_not_used_reason: null,
  knowledge_retrieval_min_score: 8
};

const emptyGameSessionDebug: GameSessionDebugResponse = {
  current_game: null,
  current_boss: null,
  last_boss: null,
  last_attempted_boss: null,
  last_cleared_boss: null,
  current_activity: null,
  recent_game_topics: [],
  boss_history: [],
  frustration_count: 0,
  death_count: 0,
  last_user_intent: null,
  last_game_intent: null,
  last_updated_at: null
};

const emptyPromptPreview: PromptPreviewResponse = {
  persona_mode: "unknown",
  current_user_message: null,
  prompt_order: [],
  model_route_summary: {},
  game_context_summary: {},
  session_focus_summary: {},
  game_state_summary: {},
  knowledge_summary: {},
  memory_summary: {},
  final_context_summary: {},
  warnings: []
};

const emptySemanticExtractionDebug: SemanticExtractionDebugResponse = {
  latest_user_message: null,
  rule_result: null,
  rule_confidence: 0,
  llm_called: false,
  semantic_extraction_model: null,
  semantic_extraction_latency_ms: 0,
  provider_latency_ms: 0,
  llm_result: null,
  final_decision: null,
  skip_reason: null,
  latency_ms: 0,
  parse_error: null
};

const emptyProviderDebug: ProviderDebugResponse = {
  provider: "unknown",
  model: null,
  base_url: null,
  api_key_loaded: false,
  configured_provider: "unknown",
  fallback_to_mock: false,
  env_file_loaded: false,
  env_file_path: "",
  persona_mode: "unknown",
  model_route_mode: "auto",
  deepseek_model_fast: "deepseek-v4-flash",
  deepseek_model_pro: "deepseek-v4-pro",
  selected_model: null,
  main_reply_model: null,
  route_reason: null,
  route_intent: null,
  estimated_complexity: null,
  provider_latency_ms: 0,
  semantic_extraction_model: null,
  fallback_reason: null
};

const emptySetupStatus: SetupStatus = {
  backend_ready: false,
  provider_configured: false,
  provider: "deepseek",
  api_key_loaded: false,
  base_url: "https://api.deepseek.com",
  model_preference: "auto",
  persona_mode: "minimal",
  memory_ready: false,
  knowledge_ready: false,
  needs_setup: true,
  missing_items: ["DEEPSEEK_API_KEY"],
  fast_model: "deepseek-v4-flash",
  pro_model: "deepseek-v4-pro"
};

const emptyLocalDataStatus: LocalDataStatus = {
  data_dir: "",
  memory_dir: "",
  session_dir: "",
  settings_dir: "",
  logs_dir: "",
  knowledge_dir: null,
  knowledge_source: "missing",
  data_dir_exists: false,
  memory_files_count: 0,
  session_files_count: 0,
  pending_memory_count: 0,
  using_bundled_knowledge: false,
  writable: false
};

const emptyLocalAsrStatus: LocalAsrStatus = {
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

const emptyLocalAsrSettings: LocalAsrSettings = {
  configured: false,
  binary_configured: false,
  model_configured: false,
  converter_configured: false,
  safe_binary_name: null,
  safe_model_name: null,
  safe_converter_name: null,
  source: "none"
};

const emptyLocalAsrSettingsDraft: LocalAsrSettingsDraft = {
  local_asr_binary_path: "",
  local_asr_model_path: "",
  audio_converter_binary_path: ""
};

const emptyLocalAsrTranscription: LocalAsrTranscriptionResponse = {
  status: "local_asr_transcription_not_ready",
  available: false,
  display_message: "本地语音识别未配置",
  transcript: "",
  transcript_char_count: 0,
  language: "zh",
  transcript_normalized_to_simplified: false,
  duration_ms: 0,
  size_bytes: 0,
  mime_type: null,
  audio_format: null,
  conversion_status: "audio_conversion_not_needed",
  conversion_required: false,
  converted_mime_type: null,
  converter_configured: false,
  safe_converter_name: null,
  temporary_file_cleaned: false,
  temporary_input_cleaned: false,
  temporary_converted_cleaned: false,
  binary_name: null,
  model_name: null
};

const emptyBackendRuntimeStatus: BackendRuntimeStatus = {
  backend_auto_start_enabled: true,
  backend_app_mode: "dev",
  backend_binary_exists: false,
  backend_binary_path: null,
  bundled_backend_binary_path: null,
  bundled_backend_exists: false,
  backend_started_by_app: false,
  backend_started_from: "none",
  backend_start_error: null,
  backend_status: "checking",
  backend_runtime_mode: "auto",
  backend_project_root: null,
  backend_root: null,
  backend_python_path: null,
  backend_health_url: "http://127.0.0.1:8000/api/health",
  backend_retry_count: 0,
  knowledge_path: null,
  knowledge_source: "missing",
  user_data_dir: ""
};

const emptyProactiveStatus: ProactiveStatusResponse = {
  enabled: false,
  sensitivity: "low",
  enabled_at: null,
  last_user_activity_at: null,
  idle_for_seconds: 0,
  idle_threshold_seconds: 0,
  initial_grace_remaining_seconds: 0,
  requires_user_activity_after_proactive: false,
  last_triggered_at: null,
  last_triggered_type: "none",
  next_possible_trigger_at: null,
  block_reason: "disabled",
  active_candidate_triggers: [],
  cooldown_remaining_seconds: 0,
  last_trigger_reason: null
};

const defaultAppSettings: AppSettings = {
  persona_mode: "guarded",
  debug_panel: "show",
  memory_enabled: true,
  pending_memory_mode: "manual",
  response_length: "normal",
  model_preference: "auto",
  proactive_companion: "off",
  proactive_sensitivity: "low",
  auto_game_detection: "on",
  overlay_enabled: "off",
  voice_output: "off",
  voice_rate: 1,
  voice_volume: 1,
  onboarding_completed: false,
  onboarding_last_seen_at: null
};

const hasAppSetting = (settings: Partial<AppSettings>, key: keyof AppSettings) =>
  Object.prototype.hasOwnProperty.call(settings, key);

const normalizeAppSettings = (
  settings: Partial<AppSettings>,
  fallback: Partial<AppSettings> = {}
): AppSettings => ({
  ...defaultAppSettings,
  ...fallback,
  ...settings
});

const voiceSettingFallback = (settings: Partial<AppSettings>, previous: AppSettings, patch: Partial<AppSettings> = {}) => ({
  overlay_enabled: hasAppSetting(settings, "overlay_enabled") ? settings.overlay_enabled : patch.overlay_enabled ?? previous.overlay_enabled,
  voice_output: hasAppSetting(settings, "voice_output") ? settings.voice_output : patch.voice_output ?? previous.voice_output,
  voice_rate: hasAppSetting(settings, "voice_rate") ? settings.voice_rate : patch.voice_rate ?? previous.voice_rate,
  voice_volume: hasAppSetting(settings, "voice_volume") ? settings.voice_volume : patch.voice_volume ?? previous.voice_volume
});

export const INTERIM_PLACEHOLDERS = ["……", "……嗯", "嗯……"];
const PLACEHOLDER_DELAY_MS = 3000;
const PROACTIVE_CHECK_INTERVAL_MS = 30000;
const AUTO_SCROLL_THRESHOLD_PX = 120;
const EVENT_STREAM_LIMIT = 20;
const TEST_VOICE_TEXT = "你好，我是 Rei。语音输出测试。";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const nextSegmentDelay = () => 500 + Math.floor(Math.random() * 401);

const pickPlaceholder = () => INTERIM_PLACEHOLDERS[Math.floor(Math.random() * INTERIM_PLACEHOLDERS.length)];

const eventTimestamp = () => new Date().toISOString();

const eventSignature = (...parts: unknown[]) => JSON.stringify(parts);

const asRecord = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};

const asArray = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

const labelMap: Record<string, string> = {
  activity: "当前活动",
  active_candidate_triggers: "候选触发器",
  active_game_display_name: "当前游戏",
  active_game_id: "当前游戏 ID",
  active_source: "当前来源",
  block_reason: "阻断原因",
  boss_history: "Boss 记录",
  complexity: "复杂度",
  confidence: "规则置信度",
  cooldown_remaining_seconds: "冷却剩余",
  coverage: "覆盖范围",
  current_boss: "当前 Boss",
  current_game: "当前游戏",
  current_session: "当前会话",
  current_session_context: "当前会话",
  current_user_message: "当前用户消息",
  death_count: "死亡次数",
  detected_at: "检测时间",
  detected_game: "检测到的游戏",
  detected_game_id: "检测游戏 ID",
  detected_knowledge_game_id: "知识库游戏 ID",
  detector_status: "检测状态",
  enabled: "是否开启",
  enabled_at: "开启时间",
  fallback_reason: "兜底原因",
  final_decision: "最终判断",
  final_event: "最终游戏事件",
  final_memory: "最终记忆",
  freshness: "状态新鲜度",
  frustration: "挫败次数",
  frustration_count: "挫败次数",
  game_state: "游戏状态摘要",
  game_id: "游戏 ID",
  game_switched: "发生游戏切换",
  idle_for_seconds: "已空闲时间",
  idle_threshold_seconds: "空闲触发阈值",
  initial_grace_remaining_seconds: "初始等待剩余",
  last_attempted: "最近挑战",
  last_cleared: "最近通过",
  last_trigger_reason: "上次触发原因",
  last_triggered_at: "上次触发时间",
  last_triggered_type: "上次触发类型",
  last_updated: "最后更新",
  last_user_activity_at: "最近用户活动",
  latency_ms: "耗时",
  latest_user: "最近用户消息",
  latest_user_message: "最近用户消息",
  knowledge: "游戏知识",
  knowledge_available: "知识库状态",
  knowledge_confidence: "知识命中信心",
  knowledge_fallback_reason: "知识兜底原因",
  knowledge_game_display_name: "匹配游戏",
  knowledge_game_id: "匹配游戏 ID",
  knowledge_match_source: "匹配来源",
  knowledge_matched: "知识命中",
  knowledge_pack_language: "语言",
  knowledge_pack_status: "知识包状态",
  knowledge_pack_version: "知识包版本",
  knowledge_path: "知识文件",
  knowledge_summary: "游戏知识摘要",
  knowledge_supported_games_count: "已支持游戏数",
  knowledge_used_in_prompt: "已注入回复上下文",
  knowledge_retrieval_status: "检索结果",
  knowledge_not_used_reason: "未使用原因",
  knowledge_retrieval_min_score: "最低命中分数",
  auto_game_detection: "自动游戏检测",
  voice_output: "语音输出",
  voice_rate: "语速",
  voice_volume: "音量",
  automatic_detected_result: "自动检测结果",
  llm_called: "是否调用 LLM",
  llm_event: "LLM 游戏事件",
  llm_memory: "LLM 记忆",
  llm_result: "LLM 判断",
  main_reply_model: "回复模型",
  memory: "记忆摘要",
  manual_override: "手动选择",
  manifest_path: "知识包清单文件",
  manifest_status: "知识包清单",
  model: "模型",
  model_route_mode: "路由模式",
  match_confidence: "匹配置信度",
  match_source: "匹配来源",
  matched_game_display_name: "匹配游戏",
  matched_game_id: "匹配游戏 ID",
  matched_topics: "相关主题",
  matched_terms: "命中词",
  next_possible_trigger_at: "下次可能触发",
  new_message: "新消息打断",
  parse_error: "解析错误",
  persona: "人格",
  persona_mode: "人格模式",
  previous_game: "上一个游戏",
  prompt_order: "上下文顺序",
  process_name: "进程名",
  provider_latency_ms: "模型耗时",
  requires_user_activity_after_proactive: "等待用户回应",
  response_latency_ms: "回复耗时",
  route_intent: "意图类型",
  route_reason: "路由原因",
  rule_result: "规则判断",
  semantic_model: "语义识别模型",
  selected_model: "选用模型",
  sensitivity: "主动灵敏度",
  session_game: "会话游戏",
  session_focus: "会话焦点",
  session_focus_summary: "会话焦点",
  skip_reason: "跳过原因",
  snippet_titles: "命中的知识标题",
  snippet_previews: "知识片段预览",
  result_scores: "命中分数",
  snippets_count: "命中知识条数",
  support_status: "支持状态",
  supported_games_count: "已支持游戏数",
  summary: "摘要"
};

const valueMap: Record<string, string> = {
  accepted: "已保存",
  auto: "自动",
  boss_attempt: "挑战中",
  boss_cleared: "已通过",
  boss_failed: "挑战失败",
  casual_chat: "闲聊",
  casual_or_short_reply: "日常短回复",
  conflict_with_fresh_game_state: "与当前游戏状态冲突",
  conversation: "对话",
  cooldown: "冷却中",
  checking: "检查中",
  connected: "已连接",
  current: "当前",
  disabled: "关闭",
  eligible: "可触发",
  enabled: "开启",
  beginner_tip: "新手建议",
  boss: "Boss",
  elden_ring: "Elden Ring",
  explicit_user_statement: "明确表达",
  fast: "快速",
  fresh: "新鲜",
  frustration_loop: "挫败循环",
  game_progress: "游戏进度",
  game_session: "游戏状态",
  elden_ring_boss_strategy: "Boss 攻略",
  elden_ring_general_help: "游戏帮助",
  elden_ring_location: "位置查询",
  boss_strategy: "Boss 攻略",
  delayed_attacks: "延迟攻击",
  preparation: "战前准备",
  summon: "召唤",
  location: "位置",
  loaded: "已加载",
  stormveil: "史东薇尔",
  malenia: "玛莲妮亚",
  waterfowl: "水鸟乱舞",
  dodge: "躲避",
  combat_pacing: "战斗节奏",
  stamina: "精力管理",
  guarded: "guarded（保守）",
  guide_preference: "攻略偏好",
  high: "高",
  hide: "隐藏",
  idle: "空闲",
  idle_silence: "空闲沉默",
  ignored: "已忽略",
  initial_grace: "初始等待中",
  late_night: "深夜提醒",
  low: "低",
  manual: "手动选择",
  user_switch: "用户切换",
  detector: "自动检测",
  session: "对话状态",
  medium: "中",
  "memory boss conflicts with fresh game state": "记忆里的 Boss 与当前游戏状态冲突",
  minimal: "minimal（自然）",
  no_candidate_trigger: "暂无可触发项",
  no_active_game: "尚未确定当前游戏",
  no_game_detected: "未检测到游戏",
  no_knowledge_match: "没有可用知识命中",
  no_supported_knowledge: "未支持知识库",
  used: "已使用本地知识",
  below_threshold: "相关性不足，未使用",
  no_pack: "没有可用知识包",
  not_game_related: "这次不是游戏知识问题",
  unknown_game: "未接入知识库",
  none: "无",
  normal: "普通",
  not_connected: "未连接",
  disconnected: "未连接",
  external_backend_detected: "已检测到外部后端",
  external: "外部后端",
  configured_binary: "指定后端",
  bundled_binary: "内置后端",
  repo: "本地源码后端",
  bundled: "内置知识资源",
  missing: "缺失",
  mock: "模拟模型",
  mock_provider: "模拟模型回复",
  off: "关闭",
  on: "开启",
  pending: "待确认",
  persona: "人格",
  persona_preference: "互动偏好",
  playstyle: "玩法",
  playstyle_preference: "玩法偏好",
  pro: "高质量",
  profile: "长期记忆",
  recent_user_message: "刚刚发言",
  relationship_preference: "互动偏好",
  repeated_death: "反复死亡",
  running: "运行中",
  sample: "样例",
  short: "简短",
  simple_game_reminder: "简单游戏提醒",
  show: "显示",
  stale: "已过期",
  starting: "正在启动",
  failed: "启动失败",
  spawn_failed: "启动失败",
  health_timeout: "启动超时",
  port_occupied: "端口被占用",
  missing_project_root: "缺少项目目录",
  missing_venv: "缺少本地运行环境",
  not_found: "未找到运行环境",
  user_is_typing: "正在输入",
  user_preference: "用户偏好",
  user_stop: "用户停止",
  unavailable: "当前环境不支持",
  waiting_for_user_activity_after_proactive: "等待用户回应",
  weak: "较弱",
  current_game: "当前运行游戏",
  user_message: "对话识别",
  alias: "游戏名或内容别名",
  unsupported_game: "暂不支持这个游戏",
  unsupported_detected_game: "检测到的游戏暂未接入知识库",
  user_message_game_conflicts_with_manual_override: "用户消息疑似切换游戏，但手动选择优先",
  knowledge_disabled: "该游戏知识库已关闭",
  knowledge_file_missing: "知识文件不存在",
  manifest_invalid: "manifest 无效",
  manifest_missing: "manifest 缺失",
  mechanic: "机制",
  process: "本地进程",
  planned: "暂未支持",
  detected_only: "暂未支持",
  supported: "已支持",
  unsupported: "暂未支持",
  window_title: "窗口标题",
  unknown: "未知"
};

const formatDebugLabel = (key: string) => labelMap[key] ?? key;

const debugText = (value: unknown, fallback = "无"): string => {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "string") return valueMap[value] ?? value;
  if (typeof value === "number") return String(value);
  if (Array.isArray(value)) return value.map((item) => debugText(item)).join("、") || fallback;
  return JSON.stringify(value);
};

const debugTime = (value: string | null | undefined): string => {
  if (!value) return "无";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return debugText(value);
  return `${formatMessageTime(value)}（本地）`;
};

const knowledgeStatusText = (status: string | null | undefined, available: boolean, fallback?: string | null) => {
  if (available && status === "supported") return "已支持";
  if (fallback === "unknown_game") return "未接入知识库";
  if (fallback === "knowledge_disabled") return "已禁用";
  if (!status) return "未匹配";
  if (["planned", "detected_only", "unsupported"].includes(status)) return "暂未支持";
  return available ? "已支持" : "未匹配";
};

const fallbackModeText = (available: boolean, used: boolean, fallback?: string | null) => {
  if (used) return "使用知识库";
  if (fallback === "no_game_detected" || fallback === "no_active_game") return "未检测到游戏";
  if (available && !fallback) return "使用知识库";
  if (!available || fallback) return "仅使用模型回答";
  return "仅使用模型回答";
};

const knowledgeRetrievalStatusText = (status: unknown) => {
  const labels: Record<string, string> = {
    used: "已使用本地知识",
    not_found: "未命中本地知识",
    below_threshold: "相关性不足，未使用",
    no_pack: "没有可用知识包",
    not_game_related: "这次不是游戏知识问题"
  };
  return labels[String(status || "")] ?? "未命中本地知识";
};

const knowledgeNotUsedReasonText = (reason: unknown) => {
  const labels: Record<string, string> = {
    no_game_detected: "未检测到游戏",
    no_active_game: "尚未确定当前游戏",
    no_knowledge_match: "没有可用知识命中",
    no_supported_knowledge: "未支持知识库",
    unknown_game: "未接入知识库",
    knowledge_disabled: "该游戏知识库已关闭",
    knowledge_file_missing: "知识文件不存在",
    below_threshold: "相关性不足，未使用",
    not_game_related: "这次不是游戏知识问题"
  };
  const key = String(reason || "");
  if (!key) return "无";
  return labels[key] ?? debugText(key);
};

const knowledgeEventTopics = (debug: ChatDebugResponse) => {
  if (debug.knowledge_used_in_prompt) {
    const labels = debug.matched_topics.length > 0 ? debug.matched_topics : debug.snippet_titles;
    return ["已使用本地知识", ...labels.slice(0, 2)];
  }
  return [
    knowledgeRetrievalStatusText(debug.knowledge_retrieval_status),
    knowledgeNotUsedReasonText(debug.knowledge_not_used_reason ?? debug.knowledge_fallback_reason)
  ].filter((item, index, items) => item !== "无" && items.indexOf(item) === index);
};

const formatDateKey = (date: Date) =>
  `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;

const formatMessageTime = (value: string | number | Date) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "时间未知";
  const now = new Date();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const time = date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
  if (formatDateKey(date) === formatDateKey(now)) return `今天 ${time}`;
  if (formatDateKey(date) === formatDateKey(yesterday)) return `昨天 ${time}`;
  const day = date.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).replace(/\//g, "-");
  return `${day} ${time}`;
};

const bossName = (value: unknown) => {
  const boss = asRecord(value);
  return debugText(boss.name ?? value);
};

const debugListText = (item: unknown): string => {
  const record = asRecord(item);
  const source = debugText(record.source, "");
  const field = record.field ? formatDebugLabel(String(record.field)) : "";
  const reason = debugText(record.reason, "");
  const text = debugText(record.text ?? record.summary ?? record.name ?? item);
  const meta = [source, field, reason].filter(Boolean).join(" / ");
  return meta ? `${meta}: ${text}` : text;
};

const truncateEventText = (value: string, maxLength = 64) =>
  value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;

const eventTextLength = (value: string) => `${value.length} 字`;

const voiceStopReasonText = (reason?: string) => {
  const labels: Record<string, string> = {
    user_stop: "用户停止",
    new_message: "新消息打断",
    disabled: "已关闭",
    unmount: "窗口关闭",
    new_reply: "新回复开始"
  };
  if (!reason) return "已停止";
  return labels[reason] ?? debugText(reason);
};

const voiceInputReasonText = (reason?: string, status?: string) => {
  if (status) return status;
  const labels: Record<string, string> = {
    not_supported: "当前运行环境不支持本地语音识别",
    permission_denied: "麦克风权限被拒绝",
    network: "语音识别服务不可用",
    no_speech: "没有识别到语音",
    aborted: "用户停止",
    audio_capture: "无法读取麦克风",
    start_failed: "语音输入启动失败",
    user_stop: "用户停止",
    unmount: "窗口关闭",
    unknown: "语音输入失败"
  };
  if (!reason) return "无";
  return labels[reason] ?? "语音输入失败";
};

const audioCaptureReasonText = (reason?: string, status?: string) => {
  const labels: Record<string, string> = {
    not_supported: "当前环境不支持录音",
    permission_denied: "麦克风权限被拒绝",
    recording_failed: "录音失败",
    user_stop: "用户停止",
    max_duration: "达到最长录音时间",
    unmount: "窗口关闭"
  };
  if (!reason && !status) return "无";
  return labels[reason ?? ""] ?? debugText(status ?? reason);
};

const audioBytesText = (sizeBytes: number) => {
  if (!Number.isFinite(sizeBytes) || sizeBytes <= 0) return "0 KB";
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  return `${(sizeBytes / 1024).toFixed(1)} KB`;
};

const audioFormatSummaryText = (mimeType: string | null | undefined) => {
  const value = typeof mimeType === "string" ? mimeType.split(";")[0]?.trim().toLowerCase() : "";
  if (!value) return "unknown";
  return /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/.test(value) ? value : "unknown";
};

const audioFormatConversionHint = (mimeType: string | null | undefined) => {
  const summary = audioFormatSummaryText(mimeType);
  if (["audio/wav", "audio/wave", "audio/x-wav"].includes(summary) || summary.includes("pcm")) return "";
  return "当前录音格式需要本地转换为 WAV";
};

const audioConversionStatusText = (status: LocalAsrTranscriptionResponse["conversion_status"] | null | undefined) => {
  const labels: Record<LocalAsrTranscriptionResponse["conversion_status"], string> = {
    audio_conversion_not_needed: "无需转换",
    audio_conversion_needed: "音频格式需要转换",
    audio_conversion_not_configured: "尚未配置音频转换工具",
    audio_conversion_succeeded: "音频已转换为 WAV",
    audio_conversion_failed: "音频转换失败",
    audio_conversion_timed_out: "音频转换超时",
    audio_conversion_invalid_input: "音频转换输入无效",
    audio_conversion_cleanup_failed: "音频转换清理失败"
  };
  return status ? labels[status] ?? debugText(status) : "无";
};

const voiceEventSourceText = (source?: "assistant_reply" | "test_voice") => {
  if (source === "test_voice") return "测试语音";
  return "";
};

const eventSummary = (event: ReiLinkEvent) => {
  switch (event.type) {
    case "user_message_sent":
      return truncateEventText(event.text);
    case "assistant_reply_started":
      return "开始生成回复";
    case "assistant_reply_segment_shown":
      return `第 ${event.segment_index + 1} 段 / ${eventTextLength(event.text)}`;
    case "assistant_reply_completed":
      return "回复显示完成";
    case "proactive_message_shown":
      return `${debugText(event.trigger_type)}: ${truncateEventText(event.text)}`;
    case "pending_memory_created":
      return `${debugText(event.memory_type)}: ${truncateEventText(event.text)}`;
    case "pending_memory_accepted":
      return event.memory_id;
    case "pending_memory_ignored":
      return event.memory_id;
    case "game_context_changed":
      return [debugText(event.game), debugText(event.source)].join(" / ");
    case "game_session_changed":
      return [debugText(event.game), debugText(event.current_boss), debugText(event.activity)].join(" / ");
    case "knowledge_used":
      return [event.game ? debugText(event.game) : "", debugText(event.topics)].filter(Boolean).join(" / ");
    case "model_routed":
      return `模型：${debugText(event.model)} / 原因：${debugText(event.route_reason)}`;
    case "backend_status_changed":
      return debugText(event.status);
    case "runtime_status_changed":
      return [debugText(event.backend_source), knowledgeSourceText(event.knowledge_source as BackendRuntimeStatus["knowledge_source"])].join(" / ");
    case "overlay_enabled_changed":
      return [event.enabled ? "已开启" : "已关闭", event.visible ? "窗口可见" : "窗口隐藏"].join(" / ");
    case "overlay_window_shown":
      return `显示 ${event.message_count} 条短消息`;
    case "overlay_window_hidden":
      return "悬浮层已隐藏";
    case "overlay_content_updated":
      return [
        event.source ? debugText(event.source) : "",
        `${event.character_count} 字`,
        `${event.message_count} 条`
      ].filter(Boolean).join(" / ");
    case "overlay_error":
      return debugText(event.reason);
    case "tts_started":
      return [voiceEventSourceText(event.source), `${event.character_count} 字`].filter(Boolean).join(" / ");
    case "tts_completed":
      return [voiceEventSourceText(event.source), `${event.character_count} 字`].filter(Boolean).join(" / ");
    case "tts_stopped":
      return [voiceEventSourceText(event.source), voiceStopReasonText(event.reason)].filter(Boolean).join(" / ");
    case "tts_error":
      return [voiceEventSourceText(event.source), event.status ? debugText(event.status) : debugText(event.reason)].filter(Boolean).join(" / ");
    case "voice_input_started":
      return [event.language ? `语言：${debugText(event.language)}` : ""].filter(Boolean).join(" / ") || "正在听";
    case "voice_input_completed":
      return [`识别文本 ${event.character_count} 字`, event.is_final ? "已填入输入框" : "", event.language ? `语言：${debugText(event.language)}` : ""].filter(Boolean).join(" / ");
    case "voice_input_stopped":
      return [voiceInputReasonText(event.reason, event.status), event.character_count ? `${event.character_count} 字` : "", event.language ? `语言：${debugText(event.language)}` : ""].filter(Boolean).join(" / ");
    case "voice_input_error":
      return [voiceInputReasonText(event.reason, event.status), event.character_count ? `${event.character_count} 字` : "", event.language ? `语言：${debugText(event.language)}` : ""].filter(Boolean).join(" / ");
    case "voice_input_unavailable":
      return [voiceInputReasonText(event.reason, event.status), event.language ? `语言：${debugText(event.language)}` : ""].filter(Boolean).join(" / ");
    case "audio_capture_started":
      return `最长 ${event.duration_ms ?? 0} ms`;
    case "audio_capture_completed":
      return [`${event.duration_ms} ms`, audioBytesText(event.size_bytes), audioFormatSummaryText(event.mime_type)].filter(Boolean).join(" / ");
    case "audio_capture_stopped":
      return [audioCaptureReasonText(event.reason), event.duration_ms ? `${event.duration_ms} ms` : ""].filter(Boolean).join(" / ");
    case "audio_capture_error":
      return audioCaptureReasonText(event.reason, event.status);
    case "audio_temp_file_cleaned":
      return [
        event.temporary_file_cleaned ? "已清理" : "未清理",
        event.duration_ms ? `${event.duration_ms} ms` : "",
        event.size_bytes ? audioBytesText(event.size_bytes) : "",
        audioFormatSummaryText(event.mime_type)
      ].filter(Boolean).join(" / ");
    case "local_asr_transcription_started":
      return [
        event.status ? debugText(event.status) : "正在本地转写",
        event.language ? `语言：${debugText(event.language)}` : "",
        event.duration_ms ? `${event.duration_ms} ms` : "",
        event.size_bytes ? audioBytesText(event.size_bytes) : "",
        audioFormatSummaryText(event.mime_type)
      ].filter(Boolean).join(" / ");
    case "local_asr_transcription_completed":
      return [
        `识别文本 ${event.character_count} 字`,
        event.language ? `语言：${debugText(event.language)}` : "",
        event.transcript_normalized_to_simplified ? "已规范为简体中文" : "",
        event.temporary_file_cleaned ? "已清理" : "未清理",
        event.duration_ms ? `${event.duration_ms} ms` : "",
        event.size_bytes ? audioBytesText(event.size_bytes) : "",
        audioFormatSummaryText(event.mime_type),
        event.conversion_status ? audioConversionStatusText(event.conversion_status) : "",
        event.converted_mime_type ? `转为 ${audioFormatSummaryText(event.converted_mime_type)}` : "",
        event.safe_converter_name ? `转换器：${debugText(event.safe_converter_name)}` : "",
        event.binary_name ? `程序：${debugText(event.binary_name)}` : "",
        event.model_name ? `模型：${debugText(event.model_name)}` : ""
      ].filter(Boolean).join(" / ");
    case "local_asr_transcription_error":
      return [
        debugText(event.reason ?? event.status),
        event.character_count ? `${event.character_count} 字` : "",
        event.language ? `语言：${debugText(event.language)}` : "",
        event.transcript_normalized_to_simplified ? "已规范为简体中文" : "",
        event.temporary_file_cleaned ? "已清理" : event.temporary_file_cleaned === false ? "未清理" : "",
        event.duration_ms ? `${event.duration_ms} ms` : "",
        event.size_bytes ? audioBytesText(event.size_bytes) : "",
        audioFormatSummaryText(event.mime_type),
        event.conversion_status ? audioConversionStatusText(event.conversion_status) : "",
        event.converted_mime_type ? `转为 ${audioFormatSummaryText(event.converted_mime_type)}` : "",
        event.safe_converter_name ? `转换器：${debugText(event.safe_converter_name)}` : "",
        event.binary_name ? `程序：${debugText(event.binary_name)}` : "",
        event.model_name ? `模型：${debugText(event.model_name)}` : ""
      ].filter(Boolean).join(" / ");
    default:
      return "event";
  }
};

const eventTypeText = (type: ReiLinkEvent["type"]) => {
  const labels: Record<ReiLinkEvent["type"], string> = {
    user_message_sent: "用户发送消息",
    assistant_reply_started: "Rei 开始回复",
    assistant_reply_segment_shown: "Rei 显示回复片段",
    assistant_reply_completed: "Rei 回复完成",
    proactive_message_shown: "主动消息显示",
    pending_memory_created: "发现待确认记忆",
    pending_memory_accepted: "记忆已保存",
    pending_memory_ignored: "记忆已忽略",
    game_context_changed: "游戏上下文变化",
    game_session_changed: "游戏状态变化",
    knowledge_used: "使用游戏知识",
    model_routed: "模型路由完成",
    backend_status_changed: "后端状态变化",
    runtime_status_changed: "运行来源变化",
    overlay_enabled_changed: "悬浮层开关变化",
    overlay_window_shown: "悬浮层显示",
    overlay_window_hidden: "悬浮层隐藏",
    overlay_content_updated: "悬浮层内容更新",
    overlay_error: "悬浮层失败",
    tts_started: "语音开始播放",
    tts_completed: "语音播放完成",
    tts_stopped: "语音已停止",
    tts_error: "语音播放失败",
    voice_input_started: "语音输入开始",
    voice_input_completed: "语音输入完成",
    voice_input_stopped: "语音输入已停止",
    voice_input_error: "语音输入失败",
    voice_input_unavailable: "语音输入不可用",
    audio_capture_started: "录音测试开始",
    audio_capture_completed: "录音测试完成",
    audio_capture_stopped: "录音已停止",
    audio_capture_error: "录音测试失败",
    audio_temp_file_cleaned: "临时音频已清理",
    local_asr_transcription_started: "本地语音识别开始",
    local_asr_transcription_completed: "本地语音识别完成",
    local_asr_transcription_error: "本地语音识别失败"
  };
  return labels[type];
};

const eventStreamTime = (timestamp: string) => {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "时间未知";
  return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
};

const voicePhaseText = (status: VoiceOutputStatus) => {
  if (!status.available) return "当前环境不支持本地语音输出";
  if (status.phase === "starting") return "正在准备播放";
  if (status.phase === "playing") return "正在播放";
  return "已停止";
};

const voiceInputPhaseText = (status: VoiceInputStatus) => {
  if (!status.supported) return "当前运行环境不支持本地语音识别";
  if (status.lastError) return status.lastError;
  if (status.phase === "listening") return "正在听 / Listening";
  if (status.phase === "recognizing") return "正在识别 / Recognizing";
  return "待命";
};

const voiceInputServiceUnavailable = (status: VoiceInputStatus) =>
  status.lastError === "语音识别服务不可用";

const voiceInputAvailabilityText = (status: VoiceInputStatus) => {
  if (voiceInputServiceUnavailable(status)) return "服务不可用";
  return status.supported ? "可用" : "不可用";
};

const voiceInputApiText = (status: VoiceInputStatus) => {
  if (voiceInputServiceUnavailable(status)) return "服务不可用";
  return status.diagnostics.recognitionApiAvailable ? "可用" : "不可用";
};

const voiceInputRuntimeText = (status: VoiceInputStatus) => {
  if (status.diagnostics.runtimeEnvironment === "packaged") return "打包应用";
  if (status.diagnostics.runtimeEnvironment === "dev") return "开发模式";
  return "未知";
};

const webSpeechVoiceInputAvailable = (status: VoiceInputStatus) =>
  status.supported && !voiceInputServiceUnavailable(status);

const mainVoiceInputProviderText = (provider: MainVoiceInputProvider) => {
  const labels: Record<MainVoiceInputProvider, string> = {
    local_asr: "local_asr",
    web_speech: "web_speech",
    unavailable: "unavailable"
  };
  return labels[provider];
};

const localAsrStatusText = (status: LocalAsrStatus) => {
  const labels: Record<LocalAsrStatus["status"], string> = {
    local_asr_not_configured: "未配置",
    local_asr_binary_missing: "缺少本地识别程序",
    local_asr_binary_not_executable: "识别程序不可执行",
    local_asr_model_missing: "缺少模型文件",
    local_asr_ready: "已就绪"
  };
  return labels[status.status] ?? "未配置";
};

const localAsrSourceText = (source: LocalAsrSettings["source"]) => {
  const labels: Record<LocalAsrSettings["source"], string> = {
    user_settings: "用户配置",
    env: "环境变量",
    none: "未配置"
  };
  return labels[source] ?? "未配置";
};

const localAsrSafeNameText = (name: string | null | undefined) => debugText(name, "未配置");

const localAsrSettingsSummaryText = (settings: LocalAsrSettings) =>
  [
    `识别程序：${localAsrSafeNameText(settings.safe_binary_name)}`,
    `模型：${localAsrSafeNameText(settings.safe_model_name)}`,
    `转换工具：${localAsrSafeNameText(settings.safe_converter_name)}`
  ].join("。");

const localAsrStatusDetail = (status: LocalAsrStatus) => {
  if (status.status === "local_asr_ready") return "本地语音识别配置已就绪。主聊天语音按钮会优先使用本地 ASR，转写后仍需手动发送。";
  if (status.status === "local_asr_binary_missing") return "未找到本地识别程序。主聊天语音按钮会回退到 Web Speech，或显示不可用。";
  if (status.status === "local_asr_binary_not_executable") return "本地识别程序不可执行。主聊天语音按钮会回退到 Web Speech，或显示不可用。";
  if (status.status === "local_asr_model_missing") return "未找到本地语音模型。主聊天语音按钮会回退到 Web Speech，或显示不可用。";
  return "未配置本地 ASR 时，主聊天语音按钮会回退到 Web Speech，或显示不可用。";
};

const mainVoiceInputLocalAsrUnavailableText = (status: LocalAsrStatus) => {
  const labels: Record<LocalAsrStatus["status"], string> = {
    local_asr_not_configured: "未配置本地 ASR",
    local_asr_binary_missing: "缺少本地识别程序",
    local_asr_binary_not_executable: "识别程序不可执行",
    local_asr_model_missing: "缺少本地语音模型",
    local_asr_ready: "本地语音识别可用"
  };
  return labels[status.status] ?? "未配置本地 ASR";
};

const selectMainVoiceInputProvider = (
  localStatus: LocalAsrStatus,
  webSpeechStatus: VoiceInputStatus
): MainVoiceInputProvider => {
  if (localStatus.status === "local_asr_ready") return "local_asr";
  if (webSpeechVoiceInputAvailable(webSpeechStatus)) return "web_speech";
  return "unavailable";
};

const mainVoiceInputLocalAsrStatusText = (
  phase: LocalAsrTranscriptionPhase,
  result: LocalAsrTranscriptionResponse | null,
  captureStatus: AudioCaptureStatus
) => {
  if (phase === "recording") return "正在录音";
  if (phase === "transcribing") return "正在本地转写";
  if (!captureStatus.supported) return "当前环境缺少麦克风录音能力";
  if (captureStatus.lastError) return captureStatus.lastError;
  if (!result) return "本地语音识别可用";
  if (result.conversion_status === "audio_conversion_not_configured") return "音频转换工具未配置";
  if (result.conversion_status === "audio_conversion_failed") return "音频转换失败";
  if (result.conversion_status === "audio_conversion_timed_out") return "音频转换超时";
  if (result.status === "local_asr_transcription_timed_out") return "本地语音识别超时，可以尝试更小模型或更短录音";
  const labels: Record<LocalAsrTranscriptionResponse["status"], string> = {
    local_asr_transcription_not_ready: "未配置本地 ASR",
    local_asr_transcription_started: "正在本地转写",
    local_asr_transcription_succeeded: "转写完成，请确认后发送",
    local_asr_transcription_failed: "本地转写失败",
    local_asr_transcription_timed_out: "本地语音识别超时，可以尝试更小模型或更短录音",
    local_asr_transcription_no_text: "没有识别到可用文本",
    local_asr_transcription_cleanup_failed: "临时音频清理失败",
    local_asr_transcription_error: "本地转写失败"
  };
  return labels[result.status] ?? "本地转写失败";
};

const mainVoiceInputUnavailableStatusText = (localStatus: LocalAsrStatus, webSpeechStatus: VoiceInputStatus) => {
  const localText = mainVoiceInputLocalAsrUnavailableText(localStatus);
  if (!webSpeechStatus.supported) return `${localText}，Web Speech 不可用`;
  if (voiceInputServiceUnavailable(webSpeechStatus)) return `${localText}，Web Speech 服务不可用`;
  if (webSpeechStatus.lastError) return webSpeechStatus.lastError;
  return localText;
};

const mainVoiceInputStatusText = (
  provider: MainVoiceInputProvider,
  webSpeechStatus: VoiceInputStatus,
  localStatus: LocalAsrStatus,
  localPhase: LocalAsrTranscriptionPhase,
  localResult: LocalAsrTranscriptionResponse | null,
  captureStatus: AudioCaptureStatus
) => {
  if (provider === "local_asr") return mainVoiceInputLocalAsrStatusText(localPhase, localResult, captureStatus);
  if (provider === "web_speech") return voiceInputPhaseText(webSpeechStatus);
  return mainVoiceInputUnavailableStatusText(localStatus, webSpeechStatus);
};

const mainVoiceInputButtonLabel = (provider: MainVoiceInputProvider, webSpeechStatus: VoiceInputStatus, localPhase: LocalAsrTranscriptionPhase) => {
  if (provider === "local_asr") {
    return localPhase === "recording" ? "停止本地转写录音 / Stop Local ASR Recording" : "开始本地语音 / Start Local ASR";
  }
  return webSpeechStatus.phase === "idle" ? "开始语音 / Start Voice" : "停止识别 / Stop Listening";
};

const mainVoiceInputButtonTitle = (
  provider: MainVoiceInputProvider,
  webSpeechStatus: VoiceInputStatus,
  localStatus: LocalAsrStatus,
  localPhase: LocalAsrTranscriptionPhase,
  localResult: LocalAsrTranscriptionResponse | null,
  captureStatus: AudioCaptureStatus
) => {
  if (provider === "local_asr") {
    if (localPhase === "recording") return "停止本地录音并开始转写";
    return mainVoiceInputLocalAsrStatusText(localPhase, localResult, captureStatus);
  }
  if (provider === "web_speech") return webSpeechStatus.phase === "idle" ? "开始语音输入" : "停止识别";
  return mainVoiceInputUnavailableStatusText(localStatus, webSpeechStatus);
};

const localAsrProbeStatusText = (probe: LocalAsrProbeResponse | null, checking: boolean, configReady: boolean) => {
  if (checking) return "正在检查";
  if (!configReady) return "配置未就绪";
  if (!probe) return "未检查";
  const labels: Record<LocalAsrProbeResponse["status"], string> = {
    local_asr_probe_not_ready: "配置未就绪",
    local_asr_probe_succeeded: "可以启动",
    local_asr_probe_failed: "启动失败",
    local_asr_probe_timed_out: "启动超时",
    local_asr_probe_error: "启动失败"
  };
  return labels[probe.status] ?? "未检查";
};

const localAsrProbeHint = (probe: LocalAsrProbeResponse | null, checking: boolean, configReady: boolean) => {
  if (checking) return "正在检查本地语音识别程序。不会录音，也不会转写。";
  if (!configReady) return "配置就绪后才能检查本地 ASR。";
  if (!probe) return "检查只确认识别程序能否启动，不代表已经可以转写语音。";
  return probe.display_message;
};

const audioProbeStatusText = (
  captureStatus: AudioCaptureStatus,
  uploading: boolean,
  result: AudioProbeResponse | null
) => {
  if (captureStatus.phase === "recording") return "正在录音";
  if (uploading) return "正在上传临时音频";
  if (!captureStatus.supported) return "当前环境不支持录音";
  if (captureStatus.lastError === "麦克风权限被拒绝") return "权限被拒绝";
  if (captureStatus.lastError) return "录音失败";
  if (!result) return "未测试";
  const labels: Record<AudioProbeResponse["status"], string> = {
    audio_probe_not_supported: "当前环境不支持录音",
    audio_probe_permission_denied: "权限被拒绝",
    audio_probe_recording_failed: "录音失败",
    audio_probe_upload_failed: "上传失败",
    audio_probe_succeeded: "录音测试完成",
    audio_probe_file_too_large: "录音文件过大",
    audio_probe_invalid_audio: "录音无效",
    audio_probe_cleanup_failed: "临时音频清理失败",
    audio_probe_error: "录音失败"
  };
  return labels[result.status] ?? "未测试";
};

const audioProbeHint = (captureStatus: AudioCaptureStatus, uploading: boolean, result: AudioProbeResponse | null) => {
  if (captureStatus.phase === "recording") return "正在录制短音频。不会转写，也不会自动发送。";
  if (uploading) return "正在上传到本机后端做临时文件清理测试。";
  if (captureStatus.lastError) return captureStatus.lastError;
  if (!captureStatus.supported) return "当前环境缺少麦克风录音能力。";
  if (!result) return `只测试麦克风录音和临时文件清理，不做语音识别。最长 ${Math.round(MAX_RECORDING_DURATION_MS / 1000)} 秒。`;
  return result.display_message;
};

const localAsrTranscriptionStatusText = (
  phase: LocalAsrTranscriptionPhase,
  result: LocalAsrTranscriptionResponse | null,
  configReady: boolean,
  captureStatus: AudioCaptureStatus
) => {
  if (phase === "recording") return "正在录音";
  if (phase === "transcribing") return "正在本地转写";
  if (!configReady) return "配置未就绪";
  if (!captureStatus.supported) return "当前环境不支持录音";
  if (!result) return "未转写";
  const labels: Record<LocalAsrTranscriptionResponse["status"], string> = {
    local_asr_transcription_not_ready: "配置未就绪",
    local_asr_transcription_started: "正在本地转写",
    local_asr_transcription_succeeded: "转写完成",
    local_asr_transcription_failed: "转写失败",
    local_asr_transcription_timed_out: "转写超时",
    local_asr_transcription_no_text: "没有识别到可用文本",
    local_asr_transcription_cleanup_failed: "临时音频清理失败",
    local_asr_transcription_error: "转写失败"
  };
  return labels[result.status] ?? "未转写";
};

const localAsrTranscriptionHint = (
  phase: LocalAsrTranscriptionPhase,
  result: LocalAsrTranscriptionResponse | null,
  configReady: boolean,
  captureStatus: AudioCaptureStatus,
  localStatus: LocalAsrStatus
) => {
  if (phase === "recording") return "正在录制短音频。完成后会交给本机后端转写。";
  if (phase === "transcribing") return "正在本机调用本地语音识别程序。不会自动发送。";
  if (!configReady) return localStatus.display_message;
  if (captureStatus.lastError) return captureStatus.lastError;
  if (!captureStatus.supported) return "当前环境缺少麦克风录音能力。";
  if (!result) return "录音并转写会把识别文本填入输入框，发送前仍可编辑或删除。";
  if (result.status === "local_asr_transcription_succeeded") return "转写完成，请确认后发送。文本已填入输入框，可编辑或删除，不会自动发送。";
  if (result.status === "local_asr_transcription_timed_out") return "本地语音识别超时，可以尝试更小模型或更短录音。不会自动发送。";
  if (result.conversion_status === "audio_conversion_not_configured") {
    return "当前录音格式需要转换为 WAV，尚未配置音频转换工具。不会上传音频，也不会自动发送。";
  }
  if (result.conversion_status === "audio_conversion_timed_out") return "音频格式转换超时。不会调用本地 ASR，也不会自动发送。";
  if (result.conversion_status === "audio_conversion_failed") return "音频格式转换失败。不会调用本地 ASR，也不会自动发送。";
  return result.display_message;
};

const appendTranscriptToInput = (current: string, transcript: string) => {
  const text = transcript.trim();
  if (!text) return current;
  if (!current.trim()) return text;
  return `${current.trimEnd()} ${text}`;
};

const safeProviderDebug = (debug: ProviderDebugResponse) => {
  const safeDebug: Partial<ProviderDebugResponse> = { ...debug };
  delete safeDebug.env_file_path;
  return safeDebug;
};

const safeBackendRuntimeDebug = (status: BackendRuntimeStatus) => ({
  backend_auto_start_enabled: status.backend_auto_start_enabled,
  backend_app_mode: status.backend_app_mode,
  backend_binary_exists: status.backend_binary_exists,
  bundled_backend_exists: status.bundled_backend_exists,
  backend_started_by_app: status.backend_started_by_app,
  backend_started_from: status.backend_started_from,
  backend_status: status.backend_status,
  backend_runtime_mode: status.backend_runtime_mode,
  backend_retry_count: status.backend_retry_count,
  knowledge_source: status.knowledge_source
});

export function EventStreamPanel({
  events,
  open,
  onOpenChange
}: {
  events: ReiLinkEvent[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <details
      className="debugSection eventStreamSection"
      onToggle={(event) => onOpenChange(event.currentTarget.open)}
      open={open}
    >
      <summary>
        <span>事件流 / Event Stream</span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </summary>
      {open && (
        <ol className="eventStreamList" aria-label="事件流列表">
          {events.map((event, index) => (
            <li key={`${event.timestamp}-${event.type}-${index}`}>
              <span className="eventStreamTime">{eventStreamTime(event.timestamp)}</span>
              <span className="eventStreamType" title={event.type}>{eventTypeText(event.type)}</span>
              <span className="eventStreamSummary">{eventSummary(event)}</span>
            </li>
          ))}
          {events.length === 0 && <li className="emptyDebugText eventStreamEmpty">暂无事件</li>}
        </ol>
      )}
    </details>
  );
}

const pendingEvidenceSummary = (memory: PendingMemory) => {
  const evidence = asRecord(memory.evidence);
  const userMessage = debugText(evidence.user_message, "");
  const gameState = debugText(evidence.game_state_summary, "");
  const parts = [
    userMessage ? `用户：${userMessage}` : "",
    gameState ? `游戏：${gameState}` : ""
  ].filter(Boolean);
  return parts.join(" / ") || "无";
};

const firstDefined = (...values: unknown[]) => values.find((value) => value !== null && value !== undefined && value !== "");

function BooleanBadge({ value }: { value: boolean }) {
  return <span className={`boolBadge ${value ? "true" : "false"}`}>{value ? "是" : "否"}</span>;
}

const formatSeconds = (value: number | null | undefined) => {
  const seconds = Math.max(0, Math.round(Number(value ?? 0)));
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)} 小时 ${Math.floor((seconds % 3600) / 60)} 分钟`;
  if (seconds >= 60) return `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`;
  return `${seconds} 秒`;
};

const backendRuntimeStatusText = (status: BackendRuntimeStatus) => {
  if (status.backend_status === "connected") return "后端已连接";
  if (status.backend_status === "external_backend_detected") return "已检测到外部后端";
  if (status.backend_status === "starting") return "正在启动本地后端";
  if (status.backend_status === "checking") return "后端连接中";
  if (status.backend_status === "missing_project_root") return "未找到本地后端目录";
  if (status.backend_status === "missing_venv") return "未找到 backend venv";
  if (status.backend_status === "spawn_failed") return "后端启动失败";
  if (status.backend_status === "health_timeout") return "后端启动超时";
  if (status.backend_status === "port_occupied") return "端口 8000 已被占用";
  if (status.backend_status === "failed") return "后端启动失败";
  if (status.backend_status === "not_found") return "未找到后端运行环境";
  if (status.backend_status === "disabled") return "自动启动已关闭，请手动运行 make dev-backend";
  return "后端未连接";
};

const backendRuntimeSourceText = (status: BackendRuntimeStatus) => {
  if (status.backend_started_from === "external") return "外部后端";
  if (status.backend_started_from === "configured_binary") return "指定后端";
  if (status.backend_started_from === "bundled_binary") return "内置后端";
  if (status.backend_started_from === "repo") return "本地源码后端";
  return status.backend_started_by_app ? "桌面端启动" : "外部或未启动";
};

const knowledgeSourceText = (source: BackendRuntimeStatus["knowledge_source"]) => {
  if (source === "bundled") return "内置知识资源";
  if (source === "repo") return "本地源码知识";
  return "缺失";
};

const formatPromptOrder = (order: string[]) =>
  order.map((item) => formatDebugLabel(item)).join(" → ") || "无";

const semanticSummary = (value: unknown) => {
  const record = asRecord(value);
  const gameEvent = asRecord(record.game_event);
  const memoryCandidate = asRecord(record.memory_candidate);
  const parts = [
    gameEvent.type ? `游戏：${debugText(gameEvent.type)}` : "",
    memoryCandidate.type ? `记忆：${debugText(memoryCandidate.type)}` : ""
  ].filter(Boolean);
  return parts.join(" / ") || debugText(value);
};

const messageMetaText = (message: Message) => {
  const time = formatMessageTime(message.createdAt);
  if (message.messageType === "proactive") {
    return `${time} · 主动 · ${debugText(message.triggerType)}`;
  }
  return time;
};

const errorRawText = (error: unknown): string => {
  if (error instanceof ApiRequestError) {
    return error.rawBody || error.message || `HTTP ${error.status}`;
  }
  if (error instanceof Error) return error.message;
  return String(error);
};

const productErrorText = (error: unknown, fallback: string): string => {
  const raw = errorRawText(error);
  const normalized = raw.toLowerCase();
  if (/api key.*missing|missing.*api key|deepseek_api_key|openai_api_key/.test(normalized)) {
    return "模型 API Key 未配置";
  }
  if (/timeout|timed out|504/.test(normalized)) {
    return "模型响应超时";
  }
  if (
    /provider failed/.test(normalized) &&
    /connection|network|urlopen|temporary failure|name resolution|nodename|refused|unreachable|reset/.test(normalized)
  ) {
    return "模型服务连接失败";
  }
  if (/provider failed|provider returned|non-2xx|response body|http \d{3}|401|403|429/.test(normalized)) {
    return "模型服务返回错误，请检查配置";
  }
  if (/failed to fetch|networkerror|load failed|offline|econnrefused/.test(normalized)) {
    return "后端未连接";
  }
  return fallback;
};

export function App() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "disconnected">("checking");
  const [gameStatus, setGameStatus] = useState<GameStatus>(idleStatus);
  const [gameDetection, setGameDetection] = useState<GameDetectionResponse>(emptyGameDetection);
  const [gameContext, setGameContext] = useState<GameContextResponse>(emptyGameContext);
  const [memoryProfile, setMemoryProfile] = useState<UserProfileMemory>(emptyProfile);
  const [memoryDebug, setMemoryDebug] = useState<MemoryDebugResponse>(emptyMemoryDebug);
  const [chatDebug, setChatDebug] = useState<ChatDebugResponse>(emptyChatDebug);
  const [providerDebug, setProviderDebug] = useState<ProviderDebugResponse>(emptyProviderDebug);
  const [proactiveStatus, setProactiveStatus] = useState<ProactiveStatusResponse>(emptyProactiveStatus);
  const [gameSessionDebug, setGameSessionDebug] = useState<GameSessionDebugResponse>(emptyGameSessionDebug);
  const [semanticDebug, setSemanticDebug] = useState<SemanticExtractionDebugResponse>(emptySemanticExtractionDebug);
  const [promptPreview, setPromptPreview] = useState<PromptPreviewResponse>(emptyPromptPreview);
  const [setupStatus, setSetupStatus] = useState<SetupStatus>(emptySetupStatus);
  const [localDataStatus, setLocalDataStatus] = useState<LocalDataStatus>(emptyLocalDataStatus);
  const [localAsrStatus, setLocalAsrStatus] = useState<LocalAsrStatus>(emptyLocalAsrStatus);
  const [localAsrSettings, setLocalAsrSettings] = useState<LocalAsrSettings>(emptyLocalAsrSettings);
  const [localAsrSettingsDraft, setLocalAsrSettingsDraft] = useState<LocalAsrSettingsDraft>(emptyLocalAsrSettingsDraft);
  const [localAsrSettingsBusy, setLocalAsrSettingsBusy] = useState("");
  const [localAsrSettingsMessage, setLocalAsrSettingsMessage] = useState("");
  const [localAsrProbe, setLocalAsrProbe] = useState<LocalAsrProbeResponse | null>(null);
  const [localAsrProbeChecking, setLocalAsrProbeChecking] = useState(false);
  const [audioCaptureStatus, setAudioCaptureStatus] = useState<AudioCaptureStatus>(() => audioCapture.getStatus());
  const [audioProbeResult, setAudioProbeResult] = useState<AudioProbeResponse | null>(null);
  const [audioProbeUploading, setAudioProbeUploading] = useState(false);
  const [localAsrTranscriptionResult, setLocalAsrTranscriptionResult] = useState<LocalAsrTranscriptionResponse | null>(null);
  const [localAsrTranscriptionPhase, setLocalAsrTranscriptionPhase] = useState<LocalAsrTranscriptionPhase>("idle");
  const [backendRuntimeStatus, setBackendRuntimeStatus] = useState<BackendRuntimeStatus>(emptyBackendRuntimeStatus);
  const [backendRuntimeAvailable, setBackendRuntimeAvailable] = useState(false);
  const [pendingMemories, setPendingMemories] = useState<PendingMemory[]>([]);
  const [pendingMemoryBusyId, setPendingMemoryBusyId] = useState("");
  const [debugActionBusy, setDebugActionBusy] = useState("");
  const [appSettings, setAppSettings] = useState<AppSettings>(defaultAppSettings);
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [settingsBusy, setSettingsBusy] = useState("");
  const [backendRuntimeBusy, setBackendRuntimeBusy] = useState(false);
  const [localDataBusy, setLocalDataBusy] = useState("");
  const [gameContextBusy, setGameContextBusy] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { id: "hello", role: "assistant", text: "我在。想问的时候就说。", createdAt: new Date().toISOString() }
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [debugOpen, setDebugOpen] = useState(true);
  const [promptPreviewOpen, setPromptPreviewOpen] = useState(false);
  const [eventStreamOpen, setEventStreamOpen] = useState(false);
  const [recentEvents, setRecentEvents] = useState<ReiLinkEvent[]>(() => eventBus.getRecentEvents(EVENT_STREAM_LIMIT));
  const [setupHelpOpen, setSetupHelpOpen] = useState(false);
  const [demoDocHintOpen, setDemoDocHintOpen] = useState(false);
  const [demoResetFeedback, setDemoResetFeedback] = useState("");
  const [onboardingDismissedThisSession, setOnboardingDismissedThisSession] = useState(false);
  const [onboardingReopened, setOnboardingReopened] = useState(false);
  const [lastError, setLastError] = useState("");
  const [lastRawError, setLastRawError] = useState("");
  const [lastInterimPlaceholderShown, setLastInterimPlaceholderShown] = useState(false);
  const [lastResponseLatencyMs, setLastResponseLatencyMs] = useState(0);
  const [voiceStatus, setVoiceStatus] = useState<VoiceOutputStatus>(() => voiceOutput.getStatus());
  const [voiceInputStatus, setVoiceInputStatus] = useState<VoiceInputStatus>(() => voiceInput.getStatus());
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const shouldAutoScrollRef = useRef(true);
  const forceNextScrollRef = useRef(true);
  const knownPendingMemoryIdsRef = useRef<Set<string>>(new Set());
  const lastBackendStatusEventRef = useRef<string | null>(null);
  const lastRuntimeStatusEventRef = useRef<string | null>(null);
  const lastGameContextEventRef = useRef<string | null>(null);
  const lastGameSessionEventRef = useRef<string | null>(null);
  const lastKnowledgeEventRef = useRef<string | null>(null);
  const lastModelRouteEventRef = useRef<string | null>(null);
  const lastOverlayEnabledRef = useRef<boolean | null>(null);
  const lastOverlayContentRef = useRef<OverlayContentUpdate | null>(null);
  const spokenAssistantReplyIdsRef = useRef<Set<string>>(new Set());

  const stopVoiceOutput = useCallback((reason: VoiceStopReason = "user_stop") => {
    voiceOutput.stop(reason);
  }, []);

  const testVoiceOutput = useCallback(() => {
    voiceOutput.speak(TEST_VOICE_TEXT, {
      rate: appSettings.voice_rate,
      volume: appSettings.voice_volume,
      source: "test_voice"
    });
  }, [appSettings.voice_rate, appSettings.voice_volume]);

  const startVoiceInput = useCallback(() => {
    voiceOutput.stop("user_stop");
    voiceInput.start({
      onFinalTranscript: (transcript) => {
        setInput((current) => appendTranscriptToInput(current, transcript));
      }
    });
  }, []);

  const stopVoiceInput = useCallback(() => {
    voiceInput.stop("user_stop");
  }, []);

  const isMessagesNearBottom = useCallback(() => {
    const element = messagesRef.current;
    if (!element) return true;
    return element.scrollHeight - element.scrollTop - element.clientHeight <= AUTO_SCROLL_THRESHOLD_PX;
  }, []);

  const queueMessageAutoScroll = useCallback((force = false) => {
    if (force) {
      forceNextScrollRef.current = true;
      shouldAutoScrollRef.current = true;
      return;
    }
    shouldAutoScrollRef.current = isMessagesNearBottom();
  }, [isMessagesNearBottom]);

  const scrollMessagesToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const element = messagesRef.current;
    if (!element) return;
    element.scrollTo({ top: element.scrollHeight, behavior });
  }, []);

  const handleMessagesScroll = useCallback(() => {
    shouldAutoScrollRef.current = isMessagesNearBottom();
  }, [isMessagesNearBottom]);

  const emitBackendStatusChanged = useCallback((status: string) => {
    if (lastBackendStatusEventRef.current === status) return;
    lastBackendStatusEventRef.current = status;
    eventBus.emit({ type: "backend_status_changed", timestamp: eventTimestamp(), status });
  }, []);

  const emitRuntimeStatusChanged = useCallback((status: BackendRuntimeStatus) => {
    const signature = eventSignature(status.backend_started_from, status.knowledge_source);
    if (lastRuntimeStatusEventRef.current === signature) return;
    lastRuntimeStatusEventRef.current = signature;
    eventBus.emit({
      type: "runtime_status_changed",
      timestamp: eventTimestamp(),
      backend_source: status.backend_started_from,
      knowledge_source: status.knowledge_source
    });
  }, []);

  const emitGameContextChanged = useCallback((currentGameContext: GameContextResponse) => {
    const game = currentGameContext.active_game_display_name ?? currentGameContext.active_game_id ?? undefined;
    const signature = eventSignature(
      game,
      currentGameContext.active_source,
      currentGameContext.support_status,
      currentGameContext.knowledge_available,
      currentGameContext.fallback_reason
    );
    if (lastGameContextEventRef.current === signature) return;
    lastGameContextEventRef.current = signature;
    eventBus.emit({
      type: "game_context_changed",
      timestamp: eventTimestamp(),
      game,
      source: currentGameContext.active_source
    });
  }, []);

  const emitGameSessionChanged = useCallback((currentGameSession: GameSessionDebugResponse) => {
    const currentBoss = currentGameSession.current_boss?.name;
    const signature = eventSignature(currentGameSession.current_game, currentBoss, currentGameSession.current_activity);
    if (lastGameSessionEventRef.current === signature) return;
    lastGameSessionEventRef.current = signature;
    eventBus.emit({
      type: "game_session_changed",
      timestamp: eventTimestamp(),
      game: currentGameSession.current_game ?? undefined,
      current_boss: currentBoss,
      activity: currentGameSession.current_activity ?? undefined
    });
  }, []);

  const emitKnowledgeUsed = useCallback((currentChatDebug: ChatDebugResponse) => {
    const topics = knowledgeEventTopics(currentChatDebug);
    const hasKnowledgeResult = currentChatDebug.knowledge_used_in_prompt ||
      currentChatDebug.knowledge_matched ||
      topics.length > 0 ||
      Boolean(currentChatDebug.request_started_at && (
        currentChatDebug.knowledge_available ||
        currentChatDebug.knowledge_retrieval_status !== "not_found" ||
        currentChatDebug.knowledge_fallback_reason
      ));
    if (!hasKnowledgeResult) return;

    const game = currentChatDebug.knowledge_game_display_name ??
      currentChatDebug.knowledge_game_id ??
      currentChatDebug.active_game_display_name ??
      currentChatDebug.active_game_id ??
      undefined;
    const signature = eventSignature(
      currentChatDebug.request_started_at,
      game,
      topics,
      currentChatDebug.knowledge_used_in_prompt,
      currentChatDebug.knowledge_matched,
      currentChatDebug.knowledge_retrieval_status,
      currentChatDebug.knowledge_not_used_reason
    );
    if (lastKnowledgeEventRef.current === signature) return;
    lastKnowledgeEventRef.current = signature;
    eventBus.emit({ type: "knowledge_used", timestamp: eventTimestamp(), game, topics });
  }, []);

  const emitModelRouted = useCallback((
    model: string | null | undefined,
    routeReason: string | null | undefined,
    requestKey?: string | null
  ) => {
    if (!model && !routeReason) return;
    const signature = eventSignature(requestKey ?? "", model, routeReason);
    if (lastModelRouteEventRef.current === signature) return;
    lastModelRouteEventRef.current = signature;
    eventBus.emit({
      type: "model_routed",
      timestamp: eventTimestamp(),
      model: model ?? undefined,
      route_reason: routeReason ?? undefined
    });
  }, []);

  const emitDebugSnapshotEvents = useCallback((
    currentGameContext: GameContextResponse,
    currentGameSession: GameSessionDebugResponse,
    currentChatDebug: ChatDebugResponse,
    currentProviderDebug: ProviderDebugResponse
  ) => {
    emitGameContextChanged(currentGameContext);
    emitGameSessionChanged(currentGameSession);
    emitKnowledgeUsed(currentChatDebug);
    emitModelRouted(
      currentChatDebug.main_reply_model ?? currentChatDebug.model_used ?? currentChatDebug.selected_model ?? currentProviderDebug.main_reply_model ?? currentProviderDebug.model ?? currentProviderDebug.selected_model,
      currentChatDebug.route_reason ?? currentProviderDebug.route_reason ?? currentChatDebug.fallback_reason ?? currentProviderDebug.fallback_reason,
      currentChatDebug.request_started_at
    );
  }, [emitGameContextChanged, emitGameSessionChanged, emitKnowledgeUsed, emitModelRouted]);

  const recordPendingMemories = useCallback((memories: PendingMemory[], emitCreated: boolean) => {
    const previousIds = knownPendingMemoryIdsRef.current;
    if (emitCreated) {
      for (const memory of memories) {
        if (!previousIds.has(memory.id)) {
          eventBus.emit({
            type: "pending_memory_created",
            timestamp: eventTimestamp(),
            memory_type: memory.type,
            text: memory.text
          });
        }
      }
    }
    knownPendingMemoryIdsRef.current = new Set(memories.map((memory) => memory.id));
    setPendingMemories(memories);
  }, []);

  const refreshStatus = useCallback(async (options: { emitPendingMemoryCreated?: boolean } = {}) => {
    try {
      setLastError("");
      setLastRawError("");
      await api.health();
      const currentSetupStatus = await api.setupStatus();
      setBackendStatus("connected");
      emitBackendStatusChanged("connected");
      setSetupStatus(currentSetupStatus);
      const currentSettings = await api.settings();
      setAppSettings((previous) =>
        normalizeAppSettings(
          currentSettings,
          voiceSettingFallback(currentSettings, previous)
        )
      );
      setSettingsLoaded(true);
      setLocalDataStatus(await api.localDataStatus());
      setLocalAsrSettings(await api.localAsrSettings());
      const currentLocalAsrStatus = await api.localAsrStatus();
      setLocalAsrStatus(currentLocalAsrStatus);
      if (currentLocalAsrStatus.status !== "local_asr_ready") setLocalAsrProbe(null);
      setGameStatus(await api.gameStatus());
      const currentGameContext = await api.gameContext();
      setGameContext(currentGameContext);
      setGameDetection(currentGameContext.detected_game);
      setMemoryProfile(await api.memoryProfile());
      setMemoryDebug(await api.memoryDebug());
      const currentChatDebug = await api.chatDebug();
      setChatDebug(currentChatDebug);
      const currentProviderDebug = await api.providerDebug();
      setProviderDebug(currentProviderDebug);
      setProactiveStatus(await api.proactiveStatus());
      const currentGameSessionDebug = await api.gameSessionDebug();
      setGameSessionDebug(currentGameSessionDebug);
      setSemanticDebug(await api.semanticExtractionDebug());
      setPromptPreview(await api.promptPreview());
      recordPendingMemories(await api.pendingMemories(), Boolean(options.emitPendingMemoryCreated));
      emitDebugSnapshotEvents(currentGameContext, currentGameSessionDebug, currentChatDebug, currentProviderDebug);
    } catch (error) {
      setBackendStatus("disconnected");
      setSettingsLoaded(false);
      emitBackendStatusChanged("disconnected");
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "后端未连接"));
    }
  }, [emitBackendStatusChanged, emitDebugSnapshotEvents, recordPendingMemories]);

  const updateAppSettings = async (patch: Partial<AppSettings>) => {
    const busyKey = Object.keys(patch)[0] ?? "settings";
    setSettingsBusy(busyKey);
    try {
      setLastError("");
      setLastRawError("");
      const updated = await api.updateSettings(patch);
      setAppSettings((previous) =>
        normalizeAppSettings(
          updated,
          voiceSettingFallback(updated, previous, patch)
        )
      );
      if (patch.debug_panel === "hide") {
        setDebugOpen(false);
        setPromptPreviewOpen(false);
      } else if (patch.debug_panel === "show") {
        setDebugOpen(true);
      }
      await refreshStatus();
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "设置更新失败"));
    } finally {
      setSettingsBusy("");
    }
  };

  const refreshLocalAsrSetup = async (message = "本地 ASR 状态已刷新") => {
    setLocalAsrSettingsBusy("refresh");
    try {
      setLastError("");
      setLastRawError("");
      const currentSettings = await api.localAsrSettings();
      const currentStatus = await api.localAsrStatus();
      setLocalAsrSettings(currentSettings);
      setLocalAsrStatus(currentStatus);
      if (currentStatus.status !== "local_asr_ready") setLocalAsrProbe(null);
      setLocalAsrSettingsMessage(message);
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "本地 ASR 配置刷新失败"));
    } finally {
      setLocalAsrSettingsBusy("");
    }
  };

  const saveLocalAsrSettings = async () => {
    const payload: LocalAsrSettingsUpdate = {};
    const binaryPath = localAsrSettingsDraft.local_asr_binary_path.trim();
    const modelPath = localAsrSettingsDraft.local_asr_model_path.trim();
    const converterPath = localAsrSettingsDraft.audio_converter_binary_path.trim();
    if (binaryPath) payload.local_asr_binary_path = binaryPath;
    if (modelPath) payload.local_asr_model_path = modelPath;
    if (converterPath) payload.audio_converter_binary_path = converterPath;
    if (Object.keys(payload).length === 0) {
      setLocalAsrSettingsMessage("请输入要保存的路径；清除请使用 Clear。");
      return;
    }
    setLocalAsrSettingsBusy("save");
    try {
      setLastError("");
      setLastRawError("");
      const updated = await api.updateLocalAsrSettings(payload);
      setLocalAsrSettings(updated);
      setLocalAsrSettingsDraft(emptyLocalAsrSettingsDraft);
      const currentStatus = await api.localAsrStatus();
      setLocalAsrStatus(currentStatus);
      if (currentStatus.status !== "local_asr_ready") setLocalAsrProbe(null);
      setLocalAsrSettingsMessage("本地 ASR 配置已保存");
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "本地 ASR 配置保存失败"));
    } finally {
      setLocalAsrSettingsBusy("");
    }
  };

  const clearLocalAsrSettings = async () => {
    setLocalAsrSettingsBusy("clear");
    try {
      setLastError("");
      setLastRawError("");
      const updated = await api.clearLocalAsrSettings();
      setLocalAsrSettings(updated);
      setLocalAsrSettingsDraft(emptyLocalAsrSettingsDraft);
      const currentStatus = await api.localAsrStatus();
      setLocalAsrStatus(currentStatus);
      if (currentStatus.status !== "local_asr_ready") setLocalAsrProbe(null);
      setLocalAsrSettingsMessage("本地 ASR 配置已清除");
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "本地 ASR 配置清除失败"));
    } finally {
      setLocalAsrSettingsBusy("");
    }
  };

  const checkLocalAsr = async () => {
    if (localAsrStatus.status !== "local_asr_ready" || localAsrProbeChecking) return;
    setLocalAsrProbeChecking(true);
    try {
      setLocalAsrProbe(await api.probeLocalAsr());
    } catch {
      setLocalAsrProbe({
        status: "local_asr_probe_error",
        available: false,
        display_message: "本地语音识别检查失败",
        binary_name: localAsrStatus.safe_binary_name,
        model_name: localAsrStatus.safe_model_name,
        duration_ms: 0
      });
    } finally {
      setLocalAsrProbeChecking(false);
    }
  };

  const runAudioCaptureProbe = async () => {
    if (audioCaptureStatus.phase === "recording") {
      audioCapture.stop("user_stop");
      return;
    }
    if (!audioCaptureStatus.supported || audioProbeUploading) return;
    setAudioProbeResult(null);
    await audioCapture.start({
      durationMs: 3000,
      onRecorded: (recording) => {
        setAudioProbeUploading(true);
        void api.probeAudio(recording.blob, recording.durationMs)
          .then((result) => {
            setAudioProbeResult(result);
            eventBus.emit({
              type: "audio_temp_file_cleaned",
              timestamp: new Date().toISOString(),
              duration_ms: result.duration_ms,
              size_bytes: result.size_bytes,
              mime_type: result.mime_type ?? undefined,
              temporary_file_cleaned: result.temporary_file_cleaned
            });
          })
          .catch(() => {
            setAudioProbeResult({
              status: "audio_probe_upload_failed",
              available: false,
              display_message: "录音上传失败",
              duration_ms: recording.durationMs,
              size_bytes: recording.sizeBytes,
              mime_type: recording.mimeType,
              temporary_file_cleaned: false
            });
            eventBus.emit({
              type: "audio_capture_error",
              timestamp: new Date().toISOString(),
              reason: "upload_failed",
              status: "录音上传失败"
            });
          })
          .finally(() => setAudioProbeUploading(false));
      }
    });
  };

  const runLocalAsrTranscription = async () => {
    if (localAsrTranscriptionPhase === "recording") {
      audioCapture.stop("user_stop");
      return;
    }
    if (
      localAsrStatus.status !== "local_asr_ready" ||
      !audioCaptureStatus.supported ||
      audioCaptureStatus.phase !== "idle" ||
      localAsrTranscriptionPhase !== "idle"
    ) {
      return;
    }
    voiceOutput.stop("user_stop");
    setLocalAsrTranscriptionResult(null);
    setLocalAsrTranscriptionPhase("recording");
    const started = await audioCapture.start({
      durationMs: 3000,
      onRecorded: (recording) => {
        setLocalAsrTranscriptionPhase("transcribing");
        eventBus.emit({
          type: "local_asr_transcription_started",
          timestamp: eventTimestamp(),
          status: "正在本地转写",
          language: LOCAL_ASR_UI_LANGUAGE,
          duration_ms: recording.durationMs,
          size_bytes: recording.sizeBytes,
          mime_type: recording.mimeType
        });
        void api.transcribeLocalAsr(recording.blob, recording.durationMs, LOCAL_ASR_UI_LANGUAGE)
          .then((result) => {
            setLocalAsrTranscriptionResult(result);
            if (result.status === "local_asr_transcription_succeeded" && result.transcript.trim()) {
              setInput((current) => appendTranscriptToInput(current, result.transcript));
              eventBus.emit({
                type: "local_asr_transcription_completed",
                timestamp: eventTimestamp(),
                status: result.status,
                character_count: result.transcript_char_count,
                language: result.language,
                transcript_normalized_to_simplified: result.transcript_normalized_to_simplified,
                duration_ms: result.duration_ms,
                size_bytes: result.size_bytes,
                mime_type: result.mime_type ?? undefined,
                audio_format: result.audio_format ?? undefined,
                conversion_status: result.conversion_status,
                conversion_required: result.conversion_required,
                converted_mime_type: result.converted_mime_type ?? undefined,
                converter_configured: result.converter_configured,
                safe_converter_name: result.safe_converter_name ?? undefined,
                temporary_file_cleaned: result.temporary_file_cleaned,
                temporary_input_cleaned: result.temporary_input_cleaned,
                temporary_converted_cleaned: result.temporary_converted_cleaned,
                binary_name: result.binary_name ?? undefined,
                model_name: result.model_name ?? undefined
              });
              return;
            }
            eventBus.emit({
              type: "local_asr_transcription_error",
              timestamp: eventTimestamp(),
              status: result.status,
              reason: result.display_message,
              character_count: result.transcript_char_count,
              language: result.language,
              transcript_normalized_to_simplified: result.transcript_normalized_to_simplified,
              duration_ms: result.duration_ms,
              size_bytes: result.size_bytes,
              mime_type: result.mime_type ?? undefined,
              audio_format: result.audio_format ?? undefined,
              conversion_status: result.conversion_status,
              conversion_required: result.conversion_required,
              converted_mime_type: result.converted_mime_type ?? undefined,
              converter_configured: result.converter_configured,
              safe_converter_name: result.safe_converter_name ?? undefined,
              temporary_file_cleaned: result.temporary_file_cleaned,
              temporary_input_cleaned: result.temporary_input_cleaned,
              temporary_converted_cleaned: result.temporary_converted_cleaned,
              binary_name: result.binary_name ?? undefined,
              model_name: result.model_name ?? undefined
            });
          })
          .catch(() => {
            const fallback: LocalAsrTranscriptionResponse = {
              ...emptyLocalAsrTranscription,
              status: "local_asr_transcription_error",
              display_message: "本地语音识别失败",
              duration_ms: recording.durationMs,
              size_bytes: recording.sizeBytes,
              mime_type: recording.mimeType,
              audio_format: recording.mimeType,
              conversion_status: audioFormatConversionHint(recording.mimeType)
                ? "audio_conversion_needed"
                : "audio_conversion_not_needed",
              conversion_required: Boolean(audioFormatConversionHint(recording.mimeType)),
              binary_name: localAsrStatus.safe_binary_name,
              model_name: localAsrStatus.safe_model_name
            };
            setLocalAsrTranscriptionResult(fallback);
            eventBus.emit({
              type: "local_asr_transcription_error",
              timestamp: eventTimestamp(),
              status: fallback.status,
              reason: fallback.display_message,
              language: fallback.language,
              transcript_normalized_to_simplified: fallback.transcript_normalized_to_simplified,
              duration_ms: fallback.duration_ms,
              size_bytes: fallback.size_bytes,
              mime_type: fallback.mime_type ?? undefined,
              audio_format: fallback.audio_format ?? undefined,
              conversion_status: fallback.conversion_status,
              conversion_required: fallback.conversion_required,
              converted_mime_type: fallback.converted_mime_type ?? undefined,
              converter_configured: fallback.converter_configured,
              safe_converter_name: fallback.safe_converter_name ?? undefined,
              temporary_file_cleaned: fallback.temporary_file_cleaned,
              temporary_input_cleaned: fallback.temporary_input_cleaned,
              temporary_converted_cleaned: fallback.temporary_converted_cleaned,
              binary_name: fallback.binary_name ?? undefined,
              model_name: fallback.model_name ?? undefined
            });
          })
          .finally(() => setLocalAsrTranscriptionPhase("idle"));
      }
    });
    if (!started) setLocalAsrTranscriptionPhase("idle");
  };

  const updateBackendAutoStart = async (enabled: boolean) => {
    const runtime = window.reilinkRuntime;
    if (!runtime) return;
    setBackendRuntimeBusy(true);
    try {
      setLastError("");
      setLastRawError("");
      const updated = await runtime.setBackendAutoStart(enabled);
      setBackendRuntimeStatus(updated);
      emitRuntimeStatusChanged(updated);
      emitBackendStatusChanged(updated.backend_status);
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "本地后端自动启动设置失败"));
    } finally {
      setBackendRuntimeBusy(false);
    }
  };

  const emitOverlayError = useCallback((reason: string) => {
    eventBus.emit({ type: "overlay_error", timestamp: eventTimestamp(), reason });
  }, []);

  const pushOverlayContent = useCallback(async (text: string, source: OverlayMessageSource) => {
    const update: OverlayContentUpdate = {
      text: sanitizeOverlayText(text),
      source,
      timestamp: eventTimestamp()
    };
    lastOverlayContentRef.current = update;
    if (appSettings.overlay_enabled !== "on") return;
    const runtime = window.reilinkRuntime;
    if (!runtime?.updateOverlayContent) return;
    try {
      const state = await runtime.updateOverlayContent(update);
      eventBus.emit({
        type: "overlay_content_updated",
        timestamp: eventTimestamp(),
        source,
        character_count: update.text.length,
        message_count: state.messages.length
      });
    } catch {
      emitOverlayError("overlay_content_update_failed");
    }
  }, [appSettings.overlay_enabled, emitOverlayError]);

  const openLocalDataDirectory = async () => {
    const runtime = window.reilinkRuntime;
    if (!runtime?.openLocalDataDir) {
      setLastError("当前桌面端不支持打开本地数据目录");
      return;
    }
    setLocalDataBusy("open-dir");
    try {
      setLastError("");
      setLastRawError("");
      const result = await runtime.openLocalDataDir();
      if (!result.ok) {
        throw new Error(result.error || "打开本地数据目录失败");
      }
      setDemoResetFeedback("已打开本地数据目录");
      await refreshStatus();
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "打开本地数据目录失败"));
    } finally {
      setLocalDataBusy("");
    }
  };

  const updateManualGameContext = async (gameId: string | null, action = "manual-game") => {
    setGameContextBusy(action);
    try {
      setLastError("");
      setLastRawError("");
      const updated = await api.setManualGameContext(gameId);
      setGameContext(updated);
      setGameDetection(updated.detected_game);
      await refreshStatus();
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "当前游戏更新失败"));
    } finally {
      setGameContextBusy("");
    }
  };

  const completeOnboarding = async () => {
    queueMessageAutoScroll(true);
    setOnboardingDismissedThisSession(true);
    setOnboardingReopened(false);
    setDemoDocHintOpen(false);
    await updateAppSettings({
      onboarding_completed: true,
      onboarding_last_seen_at: new Date().toISOString()
    });
  };

  const reopenOnboarding = () => {
    setOnboardingDismissedThisSession(false);
    setOnboardingReopened(true);
    setDemoDocHintOpen(false);
    const panel = document.getElementById("chat-panel");
    if (typeof panel?.scrollIntoView === "function") {
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  useEffect(() => {
    return eventBus.subscribe(() => {
      setRecentEvents(eventBus.getRecentEvents(EVENT_STREAM_LIMIT));
    });
  }, []);

  useEffect(() => {
    const unsubscribe = voiceOutput.subscribe(setVoiceStatus);
    return () => {
      unsubscribe();
      voiceOutput.stop("unmount");
    };
  }, []);

  useEffect(() => {
    const unsubscribe = voiceInput.subscribe(setVoiceInputStatus);
    void voiceInput.refreshDiagnostics();
    return () => {
      unsubscribe();
      voiceInput.stop("unmount");
    };
  }, []);

  useEffect(() => {
    const unsubscribe = audioCapture.subscribe(setAudioCaptureStatus);
    return () => {
      unsubscribe();
      audioCapture.stop("unmount");
    };
  }, []);

  useEffect(() => {
    if (appSettings.voice_output === "off") {
      voiceOutput.stop("disabled");
    }
  }, [appSettings.voice_output]);

  useEffect(() => {
    if (!settingsLoaded) return;
    const enabled = appSettings.overlay_enabled === "on";
    if (lastOverlayEnabledRef.current === enabled) return;
    lastOverlayEnabledRef.current = enabled;
    const runtime = window.reilinkRuntime;
    if (!runtime?.setOverlayEnabled) {
      if (enabled) emitOverlayError("overlay_runtime_unavailable");
      return;
    }
    void runtime.setOverlayEnabled(enabled).then(async (state) => {
      eventBus.emit({
        type: "overlay_enabled_changed",
        timestamp: eventTimestamp(),
        enabled,
        visible: state.visible
      });
      eventBus.emit(
        state.visible
          ? { type: "overlay_window_shown", timestamp: eventTimestamp(), message_count: state.messages.length }
          : { type: "overlay_window_hidden", timestamp: eventTimestamp() }
      );
      if (enabled && state.messages.length === 0 && lastOverlayContentRef.current && runtime.updateOverlayContent) {
        const updated = await runtime.updateOverlayContent(lastOverlayContentRef.current);
        eventBus.emit({
          type: "overlay_content_updated",
          timestamp: eventTimestamp(),
          source: lastOverlayContentRef.current.source,
          character_count: lastOverlayContentRef.current.text.length,
          message_count: updated.messages.length
        });
      }
    }).catch(() => emitOverlayError(enabled ? "overlay_show_failed" : "overlay_hide_failed"));
  }, [appSettings.overlay_enabled, emitOverlayError, settingsLoaded]);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  useEffect(() => {
    const runtime = window.reilinkRuntime;
    setBackendRuntimeAvailable(Boolean(runtime));
    if (!runtime) return undefined;

    let active = true;
    const applyStatus = (status: BackendRuntimeStatus) => {
      if (!active) return;
      setBackendRuntimeStatus(status);
      emitRuntimeStatusChanged(status);
      emitBackendStatusChanged(status.backend_status);
      if (status.backend_status === "connected") {
        void refreshStatus();
      }
    };
    void runtime.getBackendStatus().then(applyStatus).catch(() => {
      if (active) {
        const failedStatus: BackendRuntimeStatus = {
          ...emptyBackendRuntimeStatus,
          backend_start_error: "无法读取本地后端运行状态。",
          backend_status: "failed"
        };
        setBackendRuntimeStatus(failedStatus);
        emitRuntimeStatusChanged(failedStatus);
        emitBackendStatusChanged(failedStatus.backend_status);
      }
    });
    const unsubscribe = runtime.onBackendStatus(applyStatus);
    return () => {
      active = false;
      unsubscribe();
    };
  }, [emitBackendStatusChanged, emitRuntimeStatusChanged, refreshStatus]);

  const checkProactive = useCallback(async () => {
    if (backendStatus !== "connected" || appSettings.proactive_companion !== "on" || sending) return;
    try {
      const response = await api.checkProactive("default", Boolean(input.trim()), backendStatus === "connected");
      if (response.should_send && response.message) {
        const createdAt = new Date().toISOString();
        queueMessageAutoScroll();
        setMessages((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            text: response.message,
            createdAt,
            messageType: "proactive",
            triggerType: response.trigger_type
          }
        ]);
        eventBus.emit({
          type: "proactive_message_shown",
          timestamp: createdAt,
          trigger_type: response.trigger_type,
          text: response.message
        });
        void pushOverlayContent(response.message, "proactive");
      }
      setProactiveStatus(await api.proactiveStatus());
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "主动陪伴检查失败"));
    }
  }, [appSettings.proactive_companion, backendStatus, input, pushOverlayContent, queueMessageAutoScroll, sending]);

  useEffect(() => {
    if (backendStatus !== "connected" || appSettings.proactive_companion !== "on") return undefined;
    const interval = window.setInterval(() => void checkProactive(), PROACTIVE_CHECK_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [appSettings.proactive_companion, backendStatus, checkProactive]);

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;
    voiceOutput.stop("new_message");
    voiceInput.stop("user_stop");
    const userMessage: Message = { id: crypto.randomUUID(), role: "user", text: trimmed, createdAt: new Date().toISOString() };
    const placeholderId = crypto.randomUUID();
    const replyMessageId = crypto.randomUUID();
    let placeholderShown = false;
    const requestStartedAt = Date.now();
    setLastInterimPlaceholderShown(false);
    setLastError("");
    setLastRawError("");
    queueMessageAutoScroll(true);
    setMessages((current) => [...current, userMessage]);
    eventBus.emit({ type: "user_message_sent", timestamp: userMessage.createdAt, text: trimmed });
    setInput("");
    setSending(true);
    eventBus.emit({ type: "assistant_reply_started", timestamp: eventTimestamp(), message_id: replyMessageId });
    const placeholderTimer = window.setTimeout(() => {
      placeholderShown = true;
      setLastInterimPlaceholderShown(true);
      queueMessageAutoScroll();
      setMessages((current) => [
        ...current,
        { id: placeholderId, role: "assistant", text: pickPlaceholder(), createdAt: new Date().toISOString(), pending: true }
      ]);
    }, PLACEHOLDER_DELAY_MS);
    try {
      const response = await api.chat(trimmed);
      window.clearTimeout(placeholderTimer);
      setLastResponseLatencyMs(Date.now() - requestStartedAt);
      emitModelRouted(response.model_used, response.route_reason, response.request_started_at ?? String(requestStartedAt));
      queueMessageAutoScroll();
      setMessages((current) => current.filter((message) => message.id !== placeholderId));
      const segments = response.reply_segments.length > 0 ? response.reply_segments : [response.reply];
      for (const [index, segment] of segments.entries()) {
        if (index > 0) {
          await sleep(nextSegmentDelay());
        }
        const segmentCreatedAt = new Date().toISOString();
        queueMessageAutoScroll();
        setMessages((current) => [
          ...current,
          { id: crypto.randomUUID(), role: "assistant", text: segment, createdAt: segmentCreatedAt, pending: false }
        ]);
        eventBus.emit({
          type: "assistant_reply_segment_shown",
          timestamp: segmentCreatedAt,
          segment_index: index,
          text: segment
        });
      }
      eventBus.emit({ type: "assistant_reply_completed", timestamp: eventTimestamp(), message_id: replyMessageId });
      void pushOverlayContent(segments.join(" "), "assistant_reply");
      if (appSettings.voice_output === "on" && !spokenAssistantReplyIdsRef.current.has(replyMessageId)) {
        spokenAssistantReplyIdsRef.current.add(replyMessageId);
        voiceOutput.speak(segments.join("\n"), {
          rate: appSettings.voice_rate,
          volume: appSettings.voice_volume,
          source: "assistant_reply"
        });
      }
      setLastInterimPlaceholderShown(placeholderShown);
      await refreshStatus({ emitPendingMemoryCreated: true });
    } catch (error) {
      window.clearTimeout(placeholderTimer);
      setLastResponseLatencyMs(Date.now() - requestStartedAt);
      const reply = productErrorText(error, "模型服务返回错误，请检查配置");
      setLastRawError(errorRawText(error));
      setLastError(reply);
      queueMessageAutoScroll();
      setMessages((current) => [
        ...current.filter((message) => message.id !== placeholderId),
        { id: crypto.randomUUID(), role: "assistant", text: reply, createdAt: new Date().toISOString(), pending: false }
      ]);
      eventBus.emit({ type: "assistant_reply_completed", timestamp: eventTimestamp(), message_id: replyMessageId });
      setLastInterimPlaceholderShown(placeholderShown);
    } finally {
      setSending(false);
    }
  };

  const handlePendingMemory = async (id: string, action: "accept" | "ignore") => {
    setPendingMemoryBusyId(id);
    try {
      if (action === "accept") {
        await api.acceptPendingMemory(id);
        eventBus.emit({ type: "pending_memory_accepted", timestamp: eventTimestamp(), memory_id: id });
      } else {
        await api.ignorePendingMemory(id);
        eventBus.emit({ type: "pending_memory_ignored", timestamp: eventTimestamp(), memory_id: id });
      }
      await refreshStatus();
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "待确认记忆更新失败"));
    } finally {
      setPendingMemoryBusyId("");
    }
  };

  const handleDebugAction = async (
    action: "refresh" | "reset-game-session" | "reset-memory" | "clear-pending"
  ) => {
    if (action === "reset-memory" && !window.confirm("这会清空本地记忆，无法撤销。确定继续吗？")) {
      return;
    }
    setDebugActionBusy(action);
    try {
      setLastError("");
      setLastRawError("");
      if (action === "reset-game-session") {
        await api.resetGameSession();
      } else if (action === "reset-memory") {
        await api.resetMemory();
      } else if (action === "clear-pending") {
        await api.clearPendingMemories();
      }
      await refreshStatus();
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "调试操作失败"));
    } finally {
      setDebugActionBusy("");
    }
  };

  const resetOnboardingForDemo = async () => {
    const updated = await api.updateSettings({
      onboarding_completed: false,
      onboarding_last_seen_at: null
    });
    setAppSettings((previous) =>
      normalizeAppSettings(
        updated,
        voiceSettingFallback(updated, previous)
      )
    );
    setOnboardingDismissedThisSession(false);
    setOnboardingReopened(true);
    setDemoDocHintOpen(false);
  };

  const clearCurrentChat = () => {
    queueMessageAutoScroll(true);
    setMessages([]);
  };

  const handleDemoResetAction = async (action: DemoResetAction) => {
    if (
      action === "clear-chat" &&
      !window.confirm("这会清空当前聊天记录，无法撤销。确定继续吗？")
    ) {
      return;
    }
    if (
      action === "reset-memory" &&
      !window.confirm("这会清空本地记忆，无法撤销。确定继续吗？")
    ) {
      return;
    }
    if (
      action === "reset-demo" &&
      !window.confirm("这会清空当前聊天并重置演示状态，但不会清空长期记忆。确定继续吗？")
    ) {
      return;
    }

    setDebugActionBusy(`demo-${action}`);
    setDemoResetFeedback("");
    try {
      setLastError("");
      setLastRawError("");
      if (action === "reset-onboarding") {
        await resetOnboardingForDemo();
        await refreshStatus();
        setDemoResetFeedback("已恢复新手引导");
      } else if (action === "clear-chat") {
        clearCurrentChat();
        setDemoResetFeedback("已清空当前聊天记录");
      } else if (action === "reset-game-session") {
        await api.resetGameSession();
        await refreshStatus();
        setDemoResetFeedback("已清空会话状态");
      } else if (action === "clear-pending") {
        await api.clearPendingMemories();
        await refreshStatus();
        setDemoResetFeedback("已清空待确认记忆");
      } else if (action === "reset-memory") {
        await api.resetMemory();
        await refreshStatus();
        setDemoResetFeedback("已重置长期记忆");
      } else if (action === "reset-proactive") {
        await api.resetProactive();
        await refreshStatus();
        setDemoResetFeedback("已重置主动陪伴状态");
      } else if (action === "reset-demo") {
        clearCurrentChat();
        await api.resetGameSession();
        await api.clearPendingMemories();
        await api.resetProactive();
        await resetOnboardingForDemo();
        await refreshStatus();
        setDemoResetFeedback("已重置演示状态（未清空长期记忆）");
      }
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "演示重置操作失败"));
      setDemoResetFeedback("操作失败，请查看错误提示");
    } finally {
      setDebugActionBusy("");
    }
  };

  const statusLabel = useMemo(() => {
    if (backendStatus === "checking") return "检查中";
    return backendStatus === "connected" ? "已连接" : "未连接";
  }, [backendStatus]);

  const sessionFocusSummary = asRecord(promptPreview.session_focus_summary);
  const promptModelRoute = asRecord(promptPreview.model_route_summary);
  const promptGameContext = asRecord(promptPreview.game_context_summary);
  const promptGameState = asRecord(promptPreview.game_state_summary);
  const promptBossHistory = asArray(promptGameState.boss_history);
  const gameStateSummary = {
    current_game: firstDefined(promptGameState.current_game, gameSessionDebug.current_game),
    current_boss: firstDefined(promptGameState.current_boss, gameSessionDebug.current_boss),
    current_activity: firstDefined(promptGameState.current_activity, gameSessionDebug.current_activity),
    freshness: firstDefined(promptGameState.freshness, gameSessionDebug.current_boss?.freshness),
    death_count: firstDefined(promptGameState.death_count, gameSessionDebug.death_count),
    frustration_count: firstDefined(promptGameState.frustration_count, gameSessionDebug.frustration_count),
    last_attempted_boss: firstDefined(promptGameState.last_attempted_boss, gameSessionDebug.last_attempted_boss),
    last_cleared_boss: firstDefined(promptGameState.last_cleared_boss, gameSessionDebug.last_cleared_boss),
    boss_history: promptBossHistory.length > 0 ? promptBossHistory : gameSessionDebug.boss_history
  };
  const knowledgeSummary = asRecord(promptPreview.knowledge_summary);
  const memorySummary = asRecord(promptPreview.memory_summary);
  const injectedMemory = asArray(memorySummary.injected);
  const skippedMemory = asArray(memorySummary.skipped);
  const recentBossHistory = gameSessionDebug.boss_history.slice(0, 5);
  const debugPanelVisible = appSettings.debug_panel === "show";
  const displayGame = gameContext.active_game_display_name ?? gameSessionDebug.current_game ?? gameStatus.game_name ?? "idle";
  const displayBoss = gameSessionDebug.current_boss?.name ?? null;
  const localAsrConfigReady = localAsrStatus.status === "local_asr_ready";
  const localAsrTranscriptionBusy = localAsrTranscriptionPhase !== "idle";
  const localAsrTranscriptionButtonDisabled = !localAsrConfigReady ||
    !audioCaptureStatus.supported ||
    audioProbeUploading ||
    (audioCaptureStatus.phase !== "idle" && localAsrTranscriptionPhase !== "recording") ||
    localAsrTranscriptionPhase === "transcribing";
  const mainVoiceInputProvider = selectMainVoiceInputProvider(localAsrStatus, voiceInputStatus);
  const mainVoiceInputUsesLocalAsr = mainVoiceInputProvider === "local_asr";
  const mainVoiceInputUsesWebSpeech = mainVoiceInputProvider === "web_speech";
  const mainVoiceInputStatus = mainVoiceInputStatusText(
    mainVoiceInputProvider,
    voiceInputStatus,
    localAsrStatus,
    localAsrTranscriptionPhase,
    localAsrTranscriptionResult,
    audioCaptureStatus
  );
  const mainVoiceInputDisabled = mainVoiceInputUsesLocalAsr
    ? localAsrTranscriptionButtonDisabled
    : !mainVoiceInputUsesWebSpeech || !webSpeechVoiceInputAvailable(voiceInputStatus);
  const mainVoiceInputActive = mainVoiceInputUsesLocalAsr
    ? localAsrTranscriptionPhase !== "idle"
    : voiceInputStatus.phase !== "idle";
  const mainVoiceInputLabel = mainVoiceInputButtonLabel(
    mainVoiceInputProvider,
    voiceInputStatus,
    localAsrTranscriptionPhase
  );
  const mainVoiceInputTitle = mainVoiceInputButtonTitle(
    mainVoiceInputProvider,
    voiceInputStatus,
    localAsrStatus,
    localAsrTranscriptionPhase,
    localAsrTranscriptionResult,
    audioCaptureStatus
  );
  const detectionStatusText = gameDetection.status === "idle" ? "未检测到游戏" : debugText(gameDetection.status);
  const manualGameId = gameContext.manual_override.enabled ? gameContext.manual_override.game_id ?? "" : "";
  const detectedKnowledgeGameId = gameContext.detected_game.knowledge_game_id;
  const canUseDetectedGame = Boolean(
    detectedKnowledgeGameId && gameContext.available_games.some((game) => game.game_id === detectedKnowledgeGameId)
  );
  const detectedGameDisplay = gameContext.detected_game.display_name ?? (gameContext.detected_game.status === "idle" ? "未检测到游戏" : null);
  const userMessageGameDisplay = gameContext.user_message_game_display_name ?? (
    ["user_message", "alias"].includes(String(chatDebug.knowledge_match_source ?? ""))
      ? chatDebug.knowledge_game_display_name
      : null
  );
  const gameContextKnowledgeStatus = knowledgeStatusText(gameContext.support_status, gameContext.knowledge_available, gameContext.fallback_reason);
  const gameContextFallbackMode = fallbackModeText(gameContext.knowledge_available, false, gameContext.fallback_reason);
  const knowledgeFallbackMode = fallbackModeText(
    chatDebug.knowledge_available,
    chatDebug.knowledge_used_in_prompt,
    chatDebug.knowledge_fallback_reason
  );
  const supportedCatalogGames = gameContext.available_games.filter((game) => game.support_status === "supported" && game.knowledge_available);
  const plannedCatalogGames = gameContext.available_games.filter((game) => game.support_status !== "supported" || !game.knowledge_available);
  const companionName = "Rei";
  const companionSubtitle = "安静、冷淡的游戏陪伴";
  const runtimeState = backendRuntimeStatus.backend_status;
  const runtimeIsStarting = runtimeState === "checking" || runtimeState === "starting";
  const companionStatus = backendStatus === "connected" ? "在线" : runtimeIsStarting ? "启动中" : backendStatus === "checking" ? "检查中" : "离线";
  const runtimeStatusLabel = backendRuntimeAvailable ? backendRuntimeStatusText(backendRuntimeStatus) : statusLabel;
  const providerBackendStatusText = backendRuntimeAvailable ? backendRuntimeStatusText(backendRuntimeStatus) : (
    backendStatus === "connected" ? "后端已连接" : "后端未连接"
  );
  const backendRuntimeNotice = backendStatus !== "connected"
    ? {
        title: backendRuntimeAvailable ? backendRuntimeStatusText(backendRuntimeStatus) : "后端未连接",
        body: backendRuntimeAvailable
          ? backendRuntimeStatus.backend_start_error || (
              runtimeState === "starting"
                ? "ReiLink 正在尝试启动本地 FastAPI backend。"
                : "请确认本地 backend 可用，或在项目目录运行 make dev-backend。"
            )
          : "请在项目目录运行 make dev-backend 后刷新。"
      }
    : null;
  const setupNeedsAttention = backendStatus === "connected" && (setupStatus.needs_setup || !setupStatus.provider_configured);
  const onboardingVisible = backendStatus === "connected" && (
    (!appSettings.onboarding_completed && !onboardingDismissedThisSession) || onboardingReopened
  );
  const displayLocalDataStatus = {
    ...localDataStatus,
    data_dir: localDataStatus.data_dir || backendRuntimeStatus.user_data_dir,
    knowledge_dir: localDataStatus.knowledge_dir || backendRuntimeStatus.knowledge_path,
    knowledge_source: localDataStatus.knowledge_source !== "missing"
      ? localDataStatus.knowledge_source
      : backendRuntimeStatus.knowledge_source
  };
  const onboardingApiKeyText = setupStatus.api_key_loaded
    ? "当前 DeepSeek API Key 已加载。"
    : "当前 API Key 未配置，请先完成模型配置。";

  useEffect(() => {
    if (forceNextScrollRef.current || shouldAutoScrollRef.current) {
      scrollMessagesToBottom();
      forceNextScrollRef.current = false;
    }
  }, [messages, onboardingVisible, scrollMessagesToBottom]);

  const openSettingsPanel = () => {
    const panel = document.getElementById("settings-panel");
    if (typeof panel?.scrollIntoView === "function") {
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    const focusTarget = panel?.querySelector("select, button") as HTMLElement | null;
    focusTarget?.focus();
  };

  return (
    <main className="shell">
      <aside className="appSidebar" aria-label="应用导航">
        <div className="sidebarBrand">
          <Sparkles size={21} />
          <span>ReiLink</span>
        </div>

        <nav className="navMenu" aria-label="应用导航">
          <a className="navItem active" href="#chat-panel">
            <MessageSquare size={18} />
            <span>聊天</span>
          </a>
          <a className="navItem" href="#pending-memory-panel">
            <Database size={18} />
            <span>记忆</span>
          </a>
          <a className="navItem" href="#game-session-panel">
            <Gamepad2 size={18} />
            <span>游戏</span>
          </a>
          <a className="navItem" href="#settings-panel">
            <Settings size={18} />
            <span>设置</span>
          </a>
          <a className="navItem" href="#debug-panel">
            <Bug size={18} />
            <span>调试</span>
          </a>
        </nav>

        <div className="companionStatusCard">
          <div className="miniAvatar" aria-hidden="true">
            {companionName.slice(0, 1)}
          </div>
          <div>
            <span>当前角色</span>
            <strong>{companionName}</strong>
            <p>
              <span className={`statusDot ${backendStatus}`} />
              {companionStatus}
            </p>
          </div>
        </div>
      </aside>

      <section className="appWorkspace">
        <header className="workspaceHeader">
          <div className="companionIntro">
            <div className="companionAvatar" aria-hidden="true">
              {companionName.slice(0, 1)}
            </div>
            <div>
              <p className="eyebrow">陪伴角色</p>
              <h1>
                {companionName}
                <span className={`statusDot ${backendStatus}`} />
                <em>{companionStatus}</em>
              </h1>
              <p>{companionSubtitle}</p>
            </div>
          </div>
          <div className="statusStrip" aria-label="当前状态">
            <span className="topChip">
              <Brain size={15} />
              人格：{debugText(appSettings.persona_mode)}
            </span>
            <span className="topChip">
              <Bot size={15} />
              模型：{debugText(appSettings.model_preference)}
            </span>
            <span className="topChip">主动：{debugText(appSettings.proactive_companion)}</span>
            <span className="topChip">
              <Gamepad2 size={15} />
              游戏：{debugText(displayGame)}
            </span>
            <span className="topChip">Boss：{displayBoss ?? "空闲"}</span>
            {voiceStatus.active && (
              <button
                aria-label="停止语音 / Stop Voice"
                className="topChip stopVoiceButton"
                type="button"
                onClick={() => stopVoiceOutput("user_stop")}
              >
                <VolumeX size={15} />
                停止语音
              </button>
            )}
            <span className={`connection ${backendStatus}`}>{runtimeStatusLabel}</span>
            <button aria-label="刷新状态" className="iconButton soft" onClick={() => void refreshStatus()}>
              <RefreshCw size={17} />
            </button>
          </div>
        </header>

        <section className="workspaceGrid">
          <section className="chatColumn" aria-label="主聊天界面" id="chat-panel">
            <div className="timelineMarker">今天</div>

          <section className="chatPanel" aria-label="聊天面板">
            <div className="messages" role="log" aria-label="聊天消息列表" ref={messagesRef} onScroll={handleMessagesScroll}>
              {backendRuntimeNotice && (
                <section className="setupNotice backendRuntimeNotice" role="status" aria-label="后端状态提示">
                  <div className="setupNoticeHeader">
                    <RefreshCw size={18} />
                    <h2>{backendRuntimeNotice.title}</h2>
                  </div>
                  <p>{backendRuntimeNotice.body}</p>
                </section>
              )}
              {setupNeedsAttention && (
                <section className="setupNotice" role="status" aria-label="模型配置提示">
                  <div className="setupNoticeHeader">
                    <KeyRound size={18} />
                    <h2>需要完成模型配置</h2>
                  </div>
                  <p>ReiLink 需要 DeepSeek API Key 才能生成回复。请在本地 .env 中配置，或进入设置查看配置状态。</p>
                  <div className="setupNoticeActions">
                    <button className="smallButton" type="button" onClick={openSettingsPanel}>
                      <Settings size={15} />
                      打开设置
                    </button>
                    <button className="smallButton quiet" type="button" onClick={() => setSetupHelpOpen((open) => !open)}>
                      <FileText size={15} />
                      查看配置说明
                    </button>
                  </div>
                  {setupHelpOpen && (
                    <div className="setupHelp" id="provider-setup-help">
                      <p>在 `services/backend/.env` 中加入本地配置，保存后重启 backend。</p>
                      <pre>{`LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com`}</pre>
                    </div>
                  )}
                </section>
              )}
              {onboardingVisible && (
                <section className="onboardingCard" aria-label="新手引导">
                  <div className="onboardingHeader">
                    <div>
                      <p className="eyebrow">Quick Start</p>
                      <h2>快速开始 ReiLink</h2>
                    </div>
                    <button
                      className="iconButton soft"
                      type="button"
                      aria-label="关闭新手引导"
                      onClick={() => void completeOnboarding()}
                    >
                      <X size={16} />
                    </button>
                  </div>
                  <ol className="onboardingSteps">
                    <li>
                      <strong>配置模型服务</strong>
                      <span>{onboardingApiKeyText}</span>
                    </li>
                    <li>
                      <strong>选择当前游戏</strong>
                      <span>可以让 ReiLink 自动检测，也可以手动选择当前游戏。</span>
                    </li>
                    <li>
                      <strong>开始聊天</strong>
                      <span>试试：我现在卡在女武神 / 螳螂领主怎么打？</span>
                    </li>
                    <li>
                      <strong>确认记忆</strong>
                      <span>ReiLink 不会直接写入长期记忆，需要你手动保存。</span>
                    </li>
                    <li>
                      <strong>开启主动陪伴</strong>
                      <span>如果需要，可以开启主动陪伴；它会保持低频和克制。</span>
                    </li>
                    <li>
                      <strong>查看调试信息</strong>
                      <span>调试面板可以看到游戏状态、知识匹配和模型路由。</span>
                    </li>
                  </ol>
                  <div className="onboardingActions">
                    <button className="smallButton" type="button" onClick={() => void completeOnboarding()}>
                      <Sparkles size={15} />
                      开始使用
                    </button>
                    <button className="smallButton quiet" type="button" onClick={openSettingsPanel}>
                      <Settings size={15} />
                      打开设置
                    </button>
                    <button className="smallButton quiet" type="button" onClick={() => setDemoDocHintOpen((open) => !open)}>
                      <FileText size={15} />
                      查看 Demo 文档
                    </button>
                  </div>
                  {demoDocHintOpen && (
                    <p className="onboardingDocHint">Demo 文档在本地仓库：docs/DEMO_SCRIPT.md</p>
                  )}
                </section>
              )}
              {messages.map((message) => (
                <article
                  className={`messageBubble ${message.role}${message.pending ? " pending" : ""}${message.messageType === "proactive" ? " proactive" : ""}`}
                  key={message.id}
                >
                  <div className="messageHeader">
                    <span className="messageSpeaker">{message.role === "user" ? "你" : "Rei"}</span>
                    <small className="messageTime">{messageMetaText(message)}</small>
                  </div>
                  <p>{message.text}</p>
                </article>
              ))}
            </div>

            {lastError && <div className="errorNotice" role="status">{lastError}</div>}

            <form className="composer" onSubmit={sendMessage}>
              <button
                className={`iconButton voiceInputButton ${mainVoiceInputActive ? "active" : ""}`}
                type="button"
                aria-label={mainVoiceInputLabel}
                title={mainVoiceInputTitle}
                disabled={mainVoiceInputDisabled}
                onClick={() => {
                  if (mainVoiceInputUsesLocalAsr) {
                    void runLocalAsrTranscription();
                    return;
                  }
                  if (mainVoiceInputUsesWebSpeech) {
                    if (voiceInputStatus.phase === "idle") startVoiceInput();
                    else stopVoiceInput();
                  }
                }}
              >
                <Mic size={18} />
              </button>
              <input
                aria-label="聊天输入"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="问 Margit、路线、装备，或者随便说点什么。"
              />
              <button className="sendButton" type="submit" disabled={sending || !input.trim()}>
                <Send size={18} />
                <span>{sending ? "发送中" : "发送"}</span>
              </button>
              <div className="voiceInputInlineStatus" role="status">
                语音输入：{mainVoiceInputStatus}
                {voiceInputStatus.interimCharacterCount > 0 ? ` / 临时识别 ${voiceInputStatus.interimCharacterCount} 字` : ""}
              </div>
            </form>
          </section>
        </section>

        <aside className="infoRail" aria-label="信息侧栏">
          <section className="infoCard settingsPanel" aria-label="设置" id="settings-panel" style={{ order: 1 }}>
            <div className="cardHeader">
              <Settings size={17} />
              <h2>设置</h2>
            </div>
            <div className="settingRows">
              <label className="settingRow">
                <span>人格模式</span>
                <select
                  aria-label="人格模式"
                  disabled={settingsBusy !== ""}
                  value={appSettings.persona_mode}
                  onChange={(event) =>
                    void updateAppSettings({ persona_mode: event.target.value as AppSettings["persona_mode"] })
                  }
                >
                  <option value="minimal">minimal（自然）</option>
                  <option value="guarded">guarded（保守）</option>
                </select>
              </label>
              <label className="settingRow">
                <span>调试面板</span>
                <select
                  aria-label="调试面板"
                  disabled={settingsBusy !== ""}
                  value={appSettings.debug_panel}
                  onChange={(event) =>
                    void updateAppSettings({ debug_panel: event.target.value as AppSettings["debug_panel"] })
                  }
                >
                  <option value="show">显示</option>
                  <option value="hide">隐藏</option>
                </select>
              </label>
              <label className="settingRow">
                <span>记忆</span>
                <select
                  aria-label="记忆"
                  disabled={settingsBusy !== ""}
                  value={appSettings.memory_enabled ? "enabled" : "disabled"}
                  onChange={(event) => void updateAppSettings({ memory_enabled: event.target.value === "enabled" })}
                >
                  <option value="enabled">开启</option>
                  <option value="disabled">关闭</option>
                </select>
              </label>
              <label className="settingRow">
                <span>待确认记忆模式</span>
                <select aria-label="待确认记忆模式" disabled value={appSettings.pending_memory_mode}>
                  <option value="manual">手动</option>
                </select>
              </label>
              <label className="settingRow">
                <span>回复长度</span>
                <select
                  aria-label="回复长度"
                  disabled={settingsBusy !== ""}
                  value={appSettings.response_length}
                  onChange={(event) =>
                    void updateAppSettings({ response_length: event.target.value as AppSettings["response_length"] })
                  }
                >
                  <option value="short">简短</option>
                  <option value="normal">普通</option>
                </select>
              </label>
              <label className="settingRow">
                <span>模型偏好</span>
                <select
                  aria-label="模型偏好"
                  disabled={settingsBusy !== ""}
                  value={appSettings.model_preference}
                  onChange={(event) =>
                    void updateAppSettings({ model_preference: event.target.value as AppSettings["model_preference"] })
                  }
                >
                  <option value="auto">自动</option>
                  <option value="fast">快速</option>
                  <option value="pro">高质量</option>
                </select>
              </label>
              <div className="voiceOutputPanel" role="group" aria-label="Overlay 设置">
                <label className="settingRow">
                  <span>Overlay / 游戏悬浮层</span>
                  <select
                    aria-label="Overlay / 游戏悬浮层"
                    disabled={settingsBusy !== ""}
                    value={appSettings.overlay_enabled}
                    onChange={(event) =>
                      void updateAppSettings({ overlay_enabled: event.target.value as AppSettings["overlay_enabled"] })
                    }
                  >
                    <option value="off">关闭</option>
                    <option value="on">开启</option>
                  </select>
                </label>
                <p className="settingHint">默认关闭。开启后只显示 1～3 条 Rei 短消息，不接收输入。</p>
                <p className="settingHint">不显示调试信息、路径、密钥或完整回复。</p>
              </div>
              <div className="voiceOutputPanel" role="group" aria-label="语音输出设置">
                <label className="settingRow">
                  <span>语音输出 / Voice Output</span>
                  <select
                    aria-label="语音输出 / Voice Output"
                    disabled={settingsBusy !== "" || !voiceStatus.available}
                    value={appSettings.voice_output}
                    onChange={(event) =>
                      void updateAppSettings({ voice_output: event.target.value as AppSettings["voice_output"] })
                    }
                  >
                    <option value="off">关闭</option>
                    <option value="on">开启</option>
                  </select>
                </label>
                <p className="settingHint">
                  当前状态：{appSettings.voice_output === "on" ? "已开启" : "已关闭"}；本地语音：
                  {voiceStatus.available ? "可用" : "不可用"}。
                </p>
                <p className="settingHint">播放状态：{voicePhaseText(voiceStatus)}。</p>
                {voiceStatus.available && (
                  <p className="settingHint">
                    语音选择：{voiceStatus.hasChineseVoice ? "优先使用中文语音" : voiceStatus.hasVoices ? "使用系统默认语音" : "等待系统语音列表"}。
                  </p>
                )}
                {!voiceStatus.available && <p className="settingHint">当前环境不支持本地语音输出。</p>}
                <p className="settingHint">如果更换过系统语音包，请先点“测试语音”确认系统声音可用。</p>
                {voiceStatus.lastError && <p className="settingHint">{voiceStatus.lastError}</p>}
                <label className="settingRow">
                  <span>语速 / Rate</span>
                  <span className="rangeControl">
                    <input
                      aria-label="语速 / Rate"
                      disabled={settingsBusy !== ""}
                      max="1.3"
                      min="0.7"
                      step="0.1"
                      type="range"
                      value={appSettings.voice_rate}
                      onChange={(event) => void updateAppSettings({ voice_rate: Number(event.target.value) })}
                    />
                    <strong>{appSettings.voice_rate.toFixed(1)}</strong>
                  </span>
                </label>
                <label className="settingRow">
                  <span>音量 / Volume</span>
                  <span className="rangeControl">
                    <input
                      aria-label="音量 / Volume"
                      disabled={settingsBusy !== ""}
                      max="1"
                      min="0"
                      step="0.1"
                      type="range"
                      value={appSettings.voice_volume}
                      onChange={(event) => void updateAppSettings({ voice_volume: Number(event.target.value) })}
                    />
                    <strong>{appSettings.voice_volume.toFixed(1)}</strong>
                  </span>
                </label>
                {voiceStatus.active && (
                  <button
                    className="smallButton quiet"
                    type="button"
                    aria-label="停止语音 / Stop Voice"
                    onClick={() => stopVoiceOutput("user_stop")}
                  >
                    <VolumeX size={14} />
                    停止语音
                  </button>
                )}
                <button
                  className="smallButton quiet"
                  type="button"
                  aria-label="测试语音 / Test Voice"
                  disabled={!voiceStatus.available}
                  onClick={testVoiceOutput}
                >
                  <Volume2 size={14} />
                  测试语音
                </button>
              </div>
              <div className="voiceOutputPanel" role="group" aria-label="语音输入设置">
                <div className="settingRow static">
                  <span>语音输入 / Voice Input</span>
                  <strong>{voiceInputAvailabilityText(voiceInputStatus)}</strong>
                </div>
                <p className="settingHint">当前状态：{voiceInputPhaseText(voiceInputStatus)}。</p>
                <p className="settingHint">语言：{voiceInputStatus.language}。识别结果会先填入输入框，不会自动发送。</p>
                <p className="settingHint">
                  语音识别功能：{voiceInputApiText(voiceInputStatus)}。麦克风权限：{voiceInputStatus.diagnostics.microphonePermission}。运行环境：{voiceInputRuntimeText(voiceInputStatus)}。
                </p>
                {!voiceInputStatus.supported && (
                  <p className="settingHint">当前运行环境不支持本地语音识别。你仍然可以使用系统听写输入到文本框。</p>
                )}
                {voiceInputServiceUnavailable(voiceInputStatus) && (
                  <p className="settingHint">当前运行环境的语音识别服务不可用。你仍然可以使用系统听写输入到文本框。</p>
                )}
                {voiceInputStatus.lastTranscriptCharacterCount > 0 && (
                  <p className="settingHint">最近识别：{voiceInputStatus.lastTranscriptCharacterCount} 字。</p>
                )}
                {voiceInputStatus.lastError && <p className="settingHint">{voiceInputStatus.lastError}</p>}
                <div className="settingRow static">
                  <span>本地语音识别 / Local ASR</span>
                  <strong>{localAsrStatusText(localAsrStatus)}</strong>
                </div>
                <p className="settingHint">{localAsrStatus.display_message}</p>
                <p className="settingHint">{localAsrStatusDetail(localAsrStatus)}</p>
                <div className="localAsrSetupPanel" role="group" aria-label="本地 ASR 配置 / Local ASR Setup">
                  <div className="settingRow static">
                    <span>本地 ASR 配置 / Local ASR Setup</span>
                    <strong>{localAsrSourceText(localAsrSettings.source)}</strong>
                  </div>
                  <p className="settingHint">{localAsrSettingsSummaryText(localAsrSettings)}</p>
                  <label className="localAsrPathField">
                    <span>本地识别程序 / ASR Binary</span>
                    <input
                      aria-label="本地识别程序 / ASR Binary"
                      autoComplete="off"
                      disabled={localAsrSettingsBusy !== ""}
                      placeholder="/opt/homebrew/bin/whisper-cli"
                      spellCheck={false}
                      type="text"
                      value={localAsrSettingsDraft.local_asr_binary_path}
                      onChange={(event) =>
                        setLocalAsrSettingsDraft((current) => ({
                          ...current,
                          local_asr_binary_path: event.target.value
                        }))
                      }
                    />
                  </label>
                  <label className="localAsrPathField">
                    <span>模型文件 / Model File</span>
                    <input
                      aria-label="模型文件 / Model File"
                      autoComplete="off"
                      disabled={localAsrSettingsBusy !== ""}
                      placeholder="~/Library/Application Support/ReiLink/models/ggml-base.bin"
                      spellCheck={false}
                      type="text"
                      value={localAsrSettingsDraft.local_asr_model_path}
                      onChange={(event) =>
                        setLocalAsrSettingsDraft((current) => ({
                          ...current,
                          local_asr_model_path: event.target.value
                        }))
                      }
                    />
                  </label>
                  <label className="localAsrPathField">
                    <span>音频转换工具 / Audio Converter</span>
                    <input
                      aria-label="音频转换工具 / Audio Converter"
                      autoComplete="off"
                      disabled={localAsrSettingsBusy !== ""}
                      placeholder="/opt/homebrew/bin/ffmpeg"
                      spellCheck={false}
                      type="text"
                      value={localAsrSettingsDraft.audio_converter_binary_path}
                      onChange={(event) =>
                        setLocalAsrSettingsDraft((current) => ({
                          ...current,
                          audio_converter_binary_path: event.target.value
                        }))
                      }
                    />
                  </label>
                  <div className="localAsrSetupActions">
                    <button
                      className="smallButton quiet"
                      type="button"
                      aria-label="保存配置 / Save"
                      disabled={localAsrSettingsBusy !== ""}
                      onClick={() => void saveLocalAsrSettings()}
                    >
                      <FileText size={14} />
                      保存配置
                    </button>
                    <button
                      className="smallButton quiet"
                      type="button"
                      aria-label="清除配置 / Clear"
                      disabled={localAsrSettingsBusy !== ""}
                      onClick={() => void clearLocalAsrSettings()}
                    >
                      <X size={14} />
                      清除配置
                    </button>
                    <button
                      className="smallButton quiet"
                      type="button"
                      aria-label="重新检测 / Refresh Status"
                      disabled={localAsrSettingsBusy !== ""}
                      onClick={() => void refreshLocalAsrSetup()}
                    >
                      <RefreshCw size={14} />
                      重新检测
                    </button>
                  </div>
                  {localAsrSettingsMessage && <p className="settingHint">{localAsrSettingsMessage}</p>}
                </div>
                {(localAsrStatus.safe_binary_name || localAsrStatus.safe_model_name) && (
                  <p className="settingHint">
                    {localAsrStatus.safe_binary_name ? `识别程序：${debugText(localAsrStatus.safe_binary_name)}` : ""}
                    {localAsrStatus.safe_binary_name && localAsrStatus.safe_model_name ? "。" : ""}
                    {localAsrStatus.safe_model_name ? `模型：${debugText(localAsrStatus.safe_model_name)}` : ""}
                  </p>
                )}
                {localAsrStatus.safe_model_name && (
                  <p className="settingHint">
                    模型取舍：{debugText(localAsrStatus.safe_model_name)} 由用户自行配置，ReiLink 不内置模型。base 通常速度和准确率较均衡；tiny 更快但更不准，small / medium / large 可能更准但更慢或超时。
                  </p>
                )}
                <div className="settingRow static">
                  <span>本地 ASR 检查</span>
                  <strong>{localAsrProbeStatusText(localAsrProbe, localAsrProbeChecking, localAsrConfigReady)}</strong>
                </div>
                <p className="settingHint">{localAsrProbeHint(localAsrProbe, localAsrProbeChecking, localAsrConfigReady)}</p>
                {localAsrProbe && (
                  <p className="settingHint">
                    {localAsrProbe.duration_ms} ms
                    {localAsrProbe.binary_name ? `。识别程序：${debugText(localAsrProbe.binary_name)}` : ""}
                    {localAsrProbe.model_name ? `。模型：${debugText(localAsrProbe.model_name)}` : ""}
                  </p>
                )}
                <button
                  className="smallButton quiet"
                  type="button"
                  aria-label="检查本地 ASR / Check Local ASR"
                  disabled={!localAsrConfigReady || localAsrProbeChecking}
                  onClick={() => void checkLocalAsr()}
                >
                  <RefreshCw size={14} />
                  检查本地 ASR
                </button>
                <div className="settingRow static">
                  <span>本地转写测试 / Local Transcribe Test</span>
                  <strong>
                    {localAsrTranscriptionStatusText(
                      localAsrTranscriptionPhase,
                      localAsrTranscriptionResult,
                      localAsrConfigReady,
                      audioCaptureStatus
                    )}
                  </strong>
                </div>
                <p className="settingHint">
                  {localAsrTranscriptionHint(
                    localAsrTranscriptionPhase,
                    localAsrTranscriptionResult,
                    localAsrConfigReady,
                    audioCaptureStatus,
                    localAsrStatus
                  )}
                </p>
                {localAsrTranscriptionResult && (
                  <p className="settingHint">
                    {localAsrTranscriptionResult.transcript_char_count} 字
                    {`。语言：${debugText(localAsrTranscriptionResult.language)}`}
                    {localAsrTranscriptionResult.transcript_normalized_to_simplified ? "。已规范为简体中文" : ""}
                    {localAsrTranscriptionResult.duration_ms ? `。${localAsrTranscriptionResult.duration_ms} ms` : ""}
                    {localAsrTranscriptionResult.size_bytes ? `。${audioBytesText(localAsrTranscriptionResult.size_bytes)}` : ""}
                    {`。格式：${audioFormatSummaryText(localAsrTranscriptionResult.mime_type)}`}
                    {audioFormatConversionHint(localAsrTranscriptionResult.mime_type) ? `。${audioFormatConversionHint(localAsrTranscriptionResult.mime_type)}` : ""}
                    {`。转换：${audioConversionStatusText(localAsrTranscriptionResult.conversion_status)}`}
                    {localAsrTranscriptionResult.converted_mime_type ? `。目标格式：${audioFormatSummaryText(localAsrTranscriptionResult.converted_mime_type)}` : ""}
                    {`。转换工具：${localAsrTranscriptionResult.converter_configured ? "已配置" : "未配置"}`}
                    {localAsrTranscriptionResult.safe_converter_name ? `。转换器：${debugText(localAsrTranscriptionResult.safe_converter_name)}` : ""}
                    {`。临时音频已清理：${localAsrTranscriptionResult.temporary_file_cleaned ? "是" : "否"}`}
                    {`。原始音频已清理：${localAsrTranscriptionResult.temporary_input_cleaned ? "是" : "否"}`}
                    {`。转换音频已清理：${localAsrTranscriptionResult.temporary_converted_cleaned ? "是" : "否"}`}
                    {localAsrTranscriptionResult.binary_name ? `。识别程序：${debugText(localAsrTranscriptionResult.binary_name)}` : ""}
                    {localAsrTranscriptionResult.model_name ? `。模型：${debugText(localAsrTranscriptionResult.model_name)}` : ""}
                  </p>
                )}
                <button
                  className="smallButton quiet"
                  type="button"
                  aria-label={localAsrTranscriptionPhase === "recording" ? "停止本地转写录音 / Stop Local Transcribe Recording" : "录音并转写 / Record & Transcribe"}
                  disabled={localAsrTranscriptionButtonDisabled}
                  onClick={() => void runLocalAsrTranscription()}
                >
                  <Mic size={14} />
                  {localAsrTranscriptionPhase === "recording" ? "停止录音" : localAsrTranscriptionBusy ? "正在转写" : "录音并转写"}
                </button>
                <div className="settingRow static">
                  <span>录音测试 / Audio Capture Test</span>
                  <strong>{audioProbeStatusText(audioCaptureStatus, audioProbeUploading, audioProbeResult)}</strong>
                </div>
                <p className="settingHint">{audioProbeHint(audioCaptureStatus, audioProbeUploading, audioProbeResult)}</p>
                {audioProbeResult && (
                  <p className="settingHint">
                    {audioBytesText(audioProbeResult.size_bytes)}。临时音频已清理：{audioProbeResult.temporary_file_cleaned ? "是" : "否"}
                    {`。格式：${audioFormatSummaryText(audioProbeResult.mime_type)}`}
                    {audioFormatConversionHint(audioProbeResult.mime_type) ? `。${audioFormatConversionHint(audioProbeResult.mime_type)}` : ""}
                  </p>
                )}
                <button
                  className="smallButton quiet"
                  type="button"
                  aria-label={audioCaptureStatus.phase === "recording" ? "停止录音 / Stop Recording" : "测试录音 / Test Recording"}
                  disabled={audioProbeUploading || (!audioCaptureStatus.supported && audioCaptureStatus.phase !== "recording")}
                  onClick={() => void runAudioCaptureProbe()}
                >
                  <Mic size={14} />
                  {audioCaptureStatus.phase === "recording" ? "停止录音" : "测试录音"}
                </button>
              </div>
              <label className="settingRow">
                <span>自动启动本地后端</span>
                <select
                  aria-label="自动启动本地后端"
                  disabled={!backendRuntimeAvailable || backendRuntimeBusy}
                  value={backendRuntimeStatus.backend_auto_start_enabled ? "on" : "off"}
                  onChange={(event) => void updateBackendAutoStart(event.target.value === "on")}
                >
                  <option value="on">开启</option>
                  <option value="off">关闭</option>
                </select>
              </label>
              <div className="providerStatusPanel" role="group" aria-label="模型服务状态">
                <div className="providerStatusTitle">
                  <KeyRound size={15} />
                  <strong>模型服务状态</strong>
                </div>
                <dl className="debugFacts">
                  <div>
                    <dt>模型服务</dt>
                    <dd>DeepSeek</dd>
                  </div>
                  <div>
                    <dt>本地后端</dt>
                    <dd>{providerBackendStatusText}</dd>
                  </div>
                  <div>
                    <dt>启动来源</dt>
                    <dd>{backendRuntimeSourceText(backendRuntimeStatus)}</dd>
                  </div>
                  <div>
                    <dt>知识资源</dt>
                    <dd>{knowledgeSourceText(backendRuntimeStatus.knowledge_source)}</dd>
                  </div>
                  <div>
                    <dt>用户数据</dt>
                    <dd>{debugText(backendRuntimeStatus.user_data_dir, "未设置")}</dd>
                  </div>
                  {backendRuntimeStatus.backend_start_error ? (
                    <div>
                      <dt>后端错误</dt>
                      <dd>{backendRuntimeStatus.backend_start_error}</dd>
                    </div>
                  ) : null}
                  <div>
                    <dt>API Key</dt>
                    <dd>{setupStatus.api_key_loaded ? "已加载" : "未配置"}</dd>
                  </div>
                  <div>
                    <dt>Base URL</dt>
                    <dd>{debugText(setupStatus.base_url)}</dd>
                  </div>
                  <div>
                    <dt>模型偏好</dt>
                    <dd>{setupStatus.model_preference}</dd>
                  </div>
                  <div>
                    <dt>Fast Model</dt>
                    <dd>{debugText(setupStatus.fast_model)}</dd>
                  </div>
                  <div>
                    <dt>Pro Model</dt>
                    <dd>{debugText(setupStatus.pro_model)}</dd>
                  </div>
                </dl>
              </div>
              <div className="onboardingSettingsPanel" role="group" aria-label="新手引导设置">
                <div>
                  <span>新手引导</span>
                  <strong>{appSettings.onboarding_completed ? "已完成" : "未完成"}</strong>
                </div>
                <button className="smallButton quiet" type="button" aria-label="新手引导：重新查看" onClick={reopenOnboarding}>
                  重新查看
                </button>
              </div>
              <div className="localDataPanel demoResetPanel" role="group" aria-label="本地数据">
                <div className="demoResetHeader">
                  <div>
                    <span>本地数据</span>
                    <strong>Local Data</strong>
                  </div>
                </div>
                <dl className="debugFacts localDataFacts">
                  <div>
                    <dt>用户数据目录</dt>
                    <dd>{debugText(displayLocalDataStatus.data_dir, "未设置")}</dd>
                  </div>
                  <div>
                    <dt>记忆目录</dt>
                    <dd>{debugText(displayLocalDataStatus.memory_dir, "未设置")}</dd>
                  </div>
                  <div>
                    <dt>会话目录</dt>
                    <dd>{debugText(displayLocalDataStatus.session_dir, "未设置")}</dd>
                  </div>
                  <div>
                    <dt>设置目录</dt>
                    <dd>{debugText(displayLocalDataStatus.settings_dir, "未设置")}</dd>
                  </div>
                  <div>
                    <dt>日志目录</dt>
                    <dd>{debugText(displayLocalDataStatus.logs_dir, "未设置")}</dd>
                  </div>
                  <div>
                    <dt>知识资源</dt>
                    <dd>{knowledgeSourceText(displayLocalDataStatus.knowledge_source)}</dd>
                  </div>
                  <div>
                    <dt>知识目录</dt>
                    <dd>{debugText(displayLocalDataStatus.knowledge_dir, "未设置")}</dd>
                  </div>
                  <div>
                    <dt>数据目录状态</dt>
                    <dd>{displayLocalDataStatus.writable ? "可写" : "不可写"}</dd>
                  </div>
                  <div>
                    <dt>目录已创建</dt>
                    <dd>{displayLocalDataStatus.data_dir_exists ? "是" : "否"}</dd>
                  </div>
                  <div>
                    <dt>待确认记忆数</dt>
                    <dd>{displayLocalDataStatus.pending_memory_count}</dd>
                  </div>
                  <div>
                    <dt>记忆文件数</dt>
                    <dd>{displayLocalDataStatus.memory_files_count}</dd>
                  </div>
                  <div>
                    <dt>会话文件数</dt>
                    <dd>{displayLocalDataStatus.session_files_count}</dd>
                  </div>
                  <div>
                    <dt>后端来源</dt>
                    <dd>{backendRuntimeSourceText(backendRuntimeStatus)}</dd>
                  </div>
                  {backendRuntimeStatus.backend_start_error ? (
                    <div>
                      <dt>后端错误</dt>
                      <dd>{backendRuntimeStatus.backend_start_error}</dd>
                    </div>
                  ) : null}
                </dl>
                <div className="demoResetActions">
                  <button
                    className="smallButton"
                    type="button"
                    title="Open local data directory"
                    disabled={!backendRuntimeAvailable || localDataBusy !== ""}
                    onClick={() => void openLocalDataDirectory()}
                  >
                    <FolderOpen size={14} />
                    打开本地数据目录
                  </button>
                  <button
                    className="smallButton quiet"
                    type="button"
                    title="Reset onboarding"
                    disabled={debugActionBusy !== ""}
                    onClick={() => void handleDemoResetAction("reset-onboarding")}
                  >
                    <RefreshCw size={14} />
                    重置新手引导
                  </button>
                  <button
                    className="smallButton quiet danger"
                    type="button"
                    title="Clear current chat session"
                    disabled={debugActionBusy !== ""}
                    onClick={() => void handleDemoResetAction("clear-chat")}
                  >
                    <MessageSquare size={14} />
                    清空聊天记录
                  </button>
                  <button
                    className="smallButton quiet"
                    type="button"
                    title="Reset game session"
                    disabled={debugActionBusy !== ""}
                    onClick={() => void handleDemoResetAction("reset-game-session")}
                  >
                    <Gamepad2 size={14} />
                    清空会话状态
                  </button>
                  <button
                    className="smallButton quiet"
                    type="button"
                    title="Clear pending memories"
                    disabled={debugActionBusy !== ""}
                    onClick={() => void handleDemoResetAction("clear-pending")}
                  >
                    <Database size={14} />
                    清空待确认记忆
                  </button>
                  <button
                    className="smallButton quiet danger"
                    type="button"
                    title="Reset long-term memory"
                    disabled={debugActionBusy !== ""}
                    onClick={() => void handleDemoResetAction("reset-memory")}
                  >
                    <Database size={14} />
                    重置长期记忆
                  </button>
                  <button
                    className="smallButton quiet"
                    type="button"
                    title="Reset proactive runtime state"
                    disabled={debugActionBusy !== ""}
                    onClick={() => void handleDemoResetAction("reset-proactive")}
                  >
                    <Sparkles size={14} />
                    重置主动陪伴状态
                  </button>
                  <button
                    className="smallButton demoResetPrimary"
                    type="button"
                    title="Reset demo state without clearing long-term memory"
                    disabled={debugActionBusy !== ""}
                    onClick={() => void handleDemoResetAction("reset-demo")}
                  >
                    <RefreshCw size={14} />
                    重置演示状态
                  </button>
                </div>
                <p className="settingHint">重置演示状态不会清空长期记忆。危险操作会先确认。</p>
                {demoResetFeedback && (
                  <p className="demoResetFeedback" role="status">
                    {demoResetFeedback}
                  </p>
                )}
              </div>
              <label className="settingRow">
                <span>自动游戏检测</span>
                <select
                  aria-label="自动游戏检测"
                  disabled={settingsBusy !== ""}
                  value={appSettings.auto_game_detection}
                  onChange={(event) =>
                    void updateAppSettings({ auto_game_detection: event.target.value as AppSettings["auto_game_detection"] })
                  }
                >
                  <option value="on">开启</option>
                  <option value="off">关闭</option>
                </select>
              </label>
              <div className="gameContextControl" aria-label="当前游戏控制">
                <dl className="debugFacts">
                  <div>
                    <dt>{formatDebugLabel("current_game")}</dt>
                    <dd>{debugText(gameContext.active_game_display_name, "未选择")}</dd>
                  </div>
                  <div>
                    <dt>{formatDebugLabel("active_source")}</dt>
                    <dd>{debugText(gameContext.active_source)}</dd>
                  </div>
                  <div>
                    <dt>{formatDebugLabel("automatic_detected_result")}</dt>
                    <dd>{debugText(detectedGameDisplay, "未检测到游戏")}</dd>
                  </div>
                  <div>
                    <dt>{formatDebugLabel("knowledge_available")}</dt>
                    <dd>{gameContextKnowledgeStatus}</dd>
                  </div>
                  <div>
                    <dt>兜底方式</dt>
                    <dd>{gameContextFallbackMode}</dd>
                  </div>
                </dl>
                {!gameContext.knowledge_available && gameContext.active_game_display_name && (
                  <p className="settingHint">该游戏暂未接入本地知识库，Rei 会先根据通用模型回答。</p>
                )}
                <label className="settingRow">
                  <span>当前游戏</span>
                  <select
                    aria-label="当前游戏"
                    disabled={gameContextBusy !== ""}
                    value={manualGameId}
                    onChange={(event) => void updateManualGameContext(event.target.value || null)}
                  >
                    <option value="">跟随自动/对话</option>
                    {gameContext.available_games.map((game) => (
                      <option key={game.game_id} value={game.game_id}>
                        {game.display_name}（{knowledgeStatusText(game.support_status, game.knowledge_available)}）
                      </option>
                    ))}
                  </select>
                </label>
                <div className="debugActions">
                  <button
                    className="smallButton"
                    type="button"
                    disabled={gameContextBusy !== "" || !canUseDetectedGame}
                    onClick={() => void updateManualGameContext(detectedKnowledgeGameId ?? null, "use-detected-game")}
                  >
                    使用检测结果
                  </button>
                  <button
                    className="smallButton quiet"
                    type="button"
                    disabled={gameContextBusy !== "" || !gameContext.manual_override.enabled}
                    onClick={() => void updateManualGameContext(null, "clear-manual-game")}
                  >
                    清除手动选择
                  </button>
                </div>
                <div className="catalogSummary" aria-label="已支持游戏">
                  <div>
                    <strong>已支持</strong>
                    <span>{supportedCatalogGames.map((game) => game.display_name).join(" / ") || "无"}</span>
                  </div>
                  <div>
                    <strong>暂未接入知识库</strong>
                    <span>{plannedCatalogGames.map((game) => game.display_name).join(" / ") || "无"}</span>
                  </div>
                </div>
              </div>
              <label className="settingRow">
                <span>主动陪伴</span>
                <select
                  aria-label="主动陪伴"
                  disabled={settingsBusy !== ""}
                  value={appSettings.proactive_companion}
                  onChange={(event) =>
                    void updateAppSettings({ proactive_companion: event.target.value as AppSettings["proactive_companion"] })
                  }
                >
                  <option value="off">关闭</option>
                  <option value="on">开启</option>
                </select>
              </label>
              <label className="settingRow">
                <span>主动灵敏度</span>
                <select
                  aria-label="主动灵敏度"
                  disabled={settingsBusy !== "" || appSettings.proactive_companion === "off"}
                  value={appSettings.proactive_sensitivity}
                  onChange={(event) =>
                    void updateAppSettings({ proactive_sensitivity: event.target.value as AppSettings["proactive_sensitivity"] })
                  }
                >
                  <option value="low">低</option>
                  <option value="normal">普通</option>
                  <option value="high">高</option>
                </select>
              </label>
            </div>
            <p className="settingHint">
              本地保存到 settings.json，不包含密钥。自动游戏检测当前为{debugText(appSettings.auto_game_detection)}。
            </p>
          </section>

          <section className="infoCard pendingPanel" aria-label="待确认记忆" id="pending-memory-panel" style={{ order: 2 }}>
            <div className="cardHeader">
              <Database size={17} />
              <h2>待确认记忆</h2>
              <span className="countPill">{pendingMemories.length}</span>
            </div>
            <div className="pendingMemoryList">
              {pendingMemories.map((memory) => (
                <article className="pendingMemoryItem" key={memory.id}>
                  <p>{memory.text}</p>
                  <div className="pendingMemoryMeta">
                    <span>{debugText(memory.type)}</span>
                    <span>{debugText(memory.source)}</span>
                    <span>{memory.confidence.toFixed(2)}</span>
                  </div>
                  <p className="pendingMemoryEvidence">{pendingEvidenceSummary(memory)}</p>
                  <div className="pendingMemoryActions">
                    <button
                      className="smallButton"
                      type="button"
                      disabled={pendingMemoryBusyId === memory.id}
                      onClick={() => void handlePendingMemory(memory.id, "accept")}
                    >
                      保存
                    </button>
                    <button
                      className="smallButton quiet"
                      type="button"
                      disabled={pendingMemoryBusyId === memory.id}
                      onClick={() => void handlePendingMemory(memory.id, "ignore")}
                    >
                      忽略
                    </button>
                  </div>
                </article>
              ))}
              {pendingMemories.length === 0 && <p className="emptyDebugText">暂无待确认记忆</p>}
            </div>
          </section>

          <section className="infoCard gameSessionPanel" aria-label="游戏状态" id="game-session-panel" style={{ order: 3 }}>
            <div className="cardHeader">
              <Gamepad2 size={17} />
              <h2>游戏状态</h2>
            </div>
            <dl className="debugFacts">
              <div>
                <dt>{formatDebugLabel("current_game")}</dt>
                <dd>{debugText(gameSessionDebug.current_game)}</dd>
              </div>
              <div>
                <dt>{formatDebugLabel("current_boss")}</dt>
                <dd>{debugText(gameSessionDebug.current_boss?.name)}</dd>
              </div>
              <div>
                <dt>{formatDebugLabel("freshness")}</dt>
                <dd>{debugText(gameSessionDebug.current_boss?.freshness)}</dd>
              </div>
              <div>
                <dt>{formatDebugLabel("activity")}</dt>
                <dd>{debugText(gameSessionDebug.current_activity)}</dd>
              </div>
              <div>
                <dt>{formatDebugLabel("last_attempted")}</dt>
                <dd>{debugText(gameSessionDebug.last_attempted_boss)}</dd>
              </div>
              <div>
                <dt>{formatDebugLabel("last_cleared")}</dt>
                <dd>{debugText(gameSessionDebug.last_cleared_boss)}</dd>
              </div>
              <div>
                <dt>{formatDebugLabel("death_count")}</dt>
                <dd>{gameSessionDebug.death_count}</dd>
              </div>
              <div>
                <dt>{formatDebugLabel("frustration")}</dt>
                <dd>{gameSessionDebug.frustration_count}</dd>
              </div>
            </dl>
            <ul className="debugList compact" aria-label="Boss 记录">
              {recentBossHistory.map((boss, index) => (
                <li key={`${boss.name}-${boss.status}-${index}`}>
                  {boss.name} / {debugText(boss.status)} / {debugText(boss.freshness)}
                </li>
              ))}
              {recentBossHistory.length === 0 && <li>无</li>}
            </ul>
          </section>

          {debugPanelVisible && (
            <section className="infoCard foldPanel" aria-label="调试面板" id="debug-panel" style={{ order: 5 }}>
              <button
                className="foldHeader"
                aria-expanded={debugOpen}
                onClick={() => setDebugOpen((open) => !open)}
              >
                <span>调试面板</span>
                {debugOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
              {debugOpen && (
                <div className="debugPanel">
                  <section className="debugSection">
                    <h3>调试操作</h3>
                    <div className="debugActions">
                      <button
                        className="smallButton"
                        type="button"
                        disabled={debugActionBusy !== ""}
                        onClick={() => void handleDebugAction("refresh")}
                      >
                        刷新调试
                      </button>
                      <button
                        className="smallButton"
                        type="button"
                        disabled={debugActionBusy !== ""}
                        onClick={() => void handleDebugAction("reset-game-session")}
                      >
                        重置游戏状态
                      </button>
                      <button
                        className="smallButton"
                        type="button"
                        disabled={debugActionBusy !== ""}
                        onClick={() => void handleDebugAction("reset-memory")}
                      >
                        重置记忆
                      </button>
                      <button
                        className="smallButton"
                        type="button"
                        disabled={debugActionBusy !== ""}
                        onClick={() => void handleDebugAction("clear-pending")}
                      >
                        清空待确认记忆
                      </button>
                    </div>
                  </section>

                  <EventStreamPanel
                    events={recentEvents}
                    open={eventStreamOpen}
                    onOpenChange={setEventStreamOpen}
                  />

                  <section className="debugSection">
                    <h3>游戏上下文</h3>
                    <dl className="debugFacts">
                      <div>
                        <dt>{formatDebugLabel("current_game")}</dt>
                        <dd>{debugText(gameContext.active_game_display_name, "未选择")}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("active_source")}</dt>
                        <dd>{debugText(gameContext.active_source)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("previous_game")}</dt>
                        <dd>{debugText(gameContext.previous_game)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("game_switched")}</dt>
                        <dd>
                          <BooleanBadge value={gameContext.game_switched} />
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("manual_override")}</dt>
                        <dd>{debugText(gameContext.manual_override.enabled ? gameContext.manual_override.display_name : null)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("automatic_detected_result")}</dt>
                        <dd>{debugText(detectedGameDisplay, "未检测到游戏")}</dd>
                      </div>
                      <div>
                        <dt>对话识别结果</dt>
                        <dd>{debugText(userMessageGameDisplay)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_available")}</dt>
                        <dd>{gameContextKnowledgeStatus}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("support_status")}</dt>
                        <dd>{debugText(gameContext.support_status)}</dd>
                      </div>
                      <div>
                        <dt>兜底方式</dt>
                        <dd>{gameContextFallbackMode}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("fallback_reason")}</dt>
                        <dd className={gameContext.fallback_reason ? "debugError" : ""}>
                          {debugText(gameContext.fallback_reason)}
                        </dd>
                      </div>
                      <div>
                        <dt>提示</dt>
                        <dd className={gameContext.warnings.length ? "debugError" : ""}>
                          {debugText(gameContext.warnings)}
                        </dd>
                      </div>
                    </dl>
                  </section>

                  <section className="debugSection">
                    <h3>游戏检测</h3>
                    <dl className="debugFacts">
                      <div>
                        <dt>{formatDebugLabel("auto_game_detection")}</dt>
                        <dd>{debugText(appSettings.auto_game_detection)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("detector_status")}</dt>
                        <dd>{detectionStatusText}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("detected_game")}</dt>
                        <dd>{debugText(gameDetection.display_name)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("process_name")}</dt>
                        <dd>{debugText(gameDetection.process_name)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("match_source")}</dt>
                        <dd>{debugText(gameDetection.match_source)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("match_confidence")}</dt>
                        <dd>{Number(gameDetection.match_confidence ?? 0).toFixed(2)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("detected_knowledge_game_id")}</dt>
                        <dd>{debugText(gameDetection.knowledge_game_id)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("detected_at")}</dt>
                        <dd>{debugTime(gameDetection.detected_at)}</dd>
                      </div>
                    </dl>
                  </section>

                  <section className="debugSection">
                    <h3>主动陪伴</h3>
                    <dl className="debugFacts">
                      <div>
                        <dt>{formatDebugLabel("enabled")}</dt>
                        <dd>
                          <BooleanBadge value={proactiveStatus.enabled} />
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("sensitivity")}</dt>
                        <dd>{debugText(proactiveStatus.sensitivity)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("enabled_at")}</dt>
                        <dd>{debugTime(proactiveStatus.enabled_at)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("last_user_activity_at")}</dt>
                        <dd>{debugTime(proactiveStatus.last_user_activity_at)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("idle_for_seconds")}</dt>
                        <dd>{formatSeconds(proactiveStatus.idle_for_seconds)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("idle_threshold_seconds")}</dt>
                        <dd>{formatSeconds(proactiveStatus.idle_threshold_seconds)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("initial_grace_remaining_seconds")}</dt>
                        <dd>{formatSeconds(proactiveStatus.initial_grace_remaining_seconds)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("cooldown_remaining_seconds")}</dt>
                        <dd>{formatSeconds(proactiveStatus.cooldown_remaining_seconds)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("requires_user_activity_after_proactive")}</dt>
                        <dd>
                          <BooleanBadge value={proactiveStatus.requires_user_activity_after_proactive} />
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("next_possible_trigger_at")}</dt>
                        <dd>{debugTime(proactiveStatus.next_possible_trigger_at)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("block_reason")}</dt>
                        <dd>{debugText(proactiveStatus.block_reason)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("last_triggered_type")}</dt>
                        <dd>{debugText(proactiveStatus.last_triggered_type)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("last_triggered_at")}</dt>
                        <dd>{debugTime(proactiveStatus.last_triggered_at)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("active_candidate_triggers")}</dt>
                        <dd>{debugText(proactiveStatus.active_candidate_triggers)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("last_trigger_reason")}</dt>
                        <dd>{debugText(proactiveStatus.last_trigger_reason)}</dd>
                      </div>
                    </dl>
                  </section>

                  <section className="debugSection">
                    <h3>语音输入</h3>
                    <dl className="debugFacts">
                      <div>
                        <dt>主输入提供方</dt>
                        <dd>{mainVoiceInputProviderText(mainVoiceInputProvider)}</dd>
                      </div>
                      <div>
                        <dt>主输入状态</dt>
                        <dd>{mainVoiceInputStatus}</dd>
                      </div>
                      <div>
                        <dt>主输入可用</dt>
                        <dd><BooleanBadge value={!mainVoiceInputDisabled} /></dd>
                      </div>
                      <div>
                        <dt>本地语音识别</dt>
                        <dd>{voiceInputAvailabilityText(voiceInputStatus)}</dd>
                      </div>
                      <div>
                        <dt>语音识别功能</dt>
                        <dd>{voiceInputApiText(voiceInputStatus)}</dd>
                      </div>
                      <div>
                        <dt>麦克风权限</dt>
                        <dd>{voiceInputStatus.diagnostics.microphonePermission}</dd>
                      </div>
                      <div>
                        <dt>运行环境</dt>
                        <dd>{voiceInputRuntimeText(voiceInputStatus)}</dd>
                      </div>
                      <div>
                        <dt>启动状态</dt>
                        <dd>{debugText(voiceInputStatus.diagnostics.lastStartStatus)}</dd>
                      </div>
                      <div>
                        <dt>当前状态</dt>
                        <dd>{voiceInputPhaseText(voiceInputStatus)}</dd>
                      </div>
                      <div>
                        <dt>语言</dt>
                        <dd>{debugText(voiceInputStatus.language)}</dd>
                      </div>
                      <div>
                        <dt>最近识别字数</dt>
                        <dd>{voiceInputStatus.lastTranscriptCharacterCount}</dd>
                      </div>
                      <div>
                        <dt>临时识别字数</dt>
                        <dd>{voiceInputStatus.interimCharacterCount}</dd>
                      </div>
                      <div>
                        <dt>最近错误</dt>
                        <dd className={voiceInputStatus.lastError ? "debugError" : ""}>
                          {debugText(voiceInputStatus.lastError)}
                        </dd>
                      </div>
                      <div>
                        <dt>本地语音识别</dt>
                        <dd>{localAsrStatusText(localAsrStatus)}</dd>
                      </div>
                      <div>
                        <dt>本地识别说明</dt>
                        <dd>{debugText(localAsrStatus.display_message)}</dd>
                      </div>
                      <div>
                        <dt>识别程序</dt>
                        <dd>{debugText(localAsrStatus.safe_binary_name)}</dd>
                      </div>
                      <div>
                        <dt>模型文件</dt>
                        <dd>{debugText(localAsrStatus.safe_model_name)}</dd>
                      </div>
                      <div>
                        <dt>音频转换工具</dt>
                        <dd>{debugText(localAsrSettings.safe_converter_name ?? localAsrStatus.safe_converter_name)}</dd>
                      </div>
                      <div>
                        <dt>配置来源</dt>
                        <dd>{localAsrSourceText(localAsrSettings.source)}</dd>
                      </div>
                      <div>
                        <dt>配置摘要</dt>
                        <dd>{debugText(localAsrSettingsSummaryText(localAsrSettings))}</dd>
                      </div>
                      <div>
                        <dt>配置状态</dt>
                        <dd>
                          binary {localAsrStatus.binary_configured ? "已配置" : "未配置"} / model {localAsrStatus.model_configured ? "已配置" : "未配置"} / converter {localAsrSettings.converter_configured ? "已配置" : "未配置"}
                        </dd>
                      </div>
                      <div>
                        <dt>本地 ASR 检查</dt>
                        <dd>{localAsrProbeStatusText(localAsrProbe, localAsrProbeChecking, localAsrConfigReady)}</dd>
                      </div>
                      <div>
                        <dt>检查说明</dt>
                        <dd>{debugText(localAsrProbeHint(localAsrProbe, localAsrProbeChecking, localAsrConfigReady))}</dd>
                      </div>
                      <div>
                        <dt>检查耗时</dt>
                        <dd>{localAsrProbe ? `${localAsrProbe.duration_ms} ms` : "无"}</dd>
                      </div>
                      <div>
                        <dt>本地转写</dt>
                        <dd>
                          {localAsrTranscriptionStatusText(
                            localAsrTranscriptionPhase,
                            localAsrTranscriptionResult,
                            localAsrConfigReady,
                            audioCaptureStatus
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>本地转写说明</dt>
                        <dd>
                          {debugText(
                            localAsrTranscriptionHint(
                              localAsrTranscriptionPhase,
                              localAsrTranscriptionResult,
                              localAsrConfigReady,
                              audioCaptureStatus,
                              localAsrStatus
                            )
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>本地转写字数</dt>
                        <dd>{localAsrTranscriptionResult?.transcript_char_count ?? 0}</dd>
                      </div>
                      <div>
                        <dt>本地转写语言</dt>
                        <dd>{debugText(localAsrTranscriptionResult?.language)}</dd>
                      </div>
                      <div>
                        <dt>本地转写简体规范</dt>
                        <dd>{localAsrTranscriptionResult ? (localAsrTranscriptionResult.transcript_normalized_to_simplified ? "已规范为简体中文" : "未改写") : "无"}</dd>
                      </div>
                      <div>
                        <dt>本地转写时长</dt>
                        <dd>{localAsrTranscriptionResult ? `${localAsrTranscriptionResult.duration_ms} ms` : "无"}</dd>
                      </div>
                      <div>
                        <dt>本地转写大小</dt>
                        <dd>{localAsrTranscriptionResult ? audioBytesText(localAsrTranscriptionResult.size_bytes) : "无"}</dd>
                      </div>
                      <div>
                        <dt>本地转写格式</dt>
                        <dd>{localAsrTranscriptionResult ? audioFormatSummaryText(localAsrTranscriptionResult.mime_type) : "无"}</dd>
                      </div>
                      <div>
                        <dt>本地转写格式提示</dt>
                        <dd>{localAsrTranscriptionResult ? debugText(audioFormatConversionHint(localAsrTranscriptionResult.mime_type), "无") : "无"}</dd>
                      </div>
                      <div>
                        <dt>本地转写转换状态</dt>
                        <dd>{localAsrTranscriptionResult ? audioConversionStatusText(localAsrTranscriptionResult.conversion_status) : "无"}</dd>
                      </div>
                      <div>
                        <dt>本地转写目标格式</dt>
                        <dd>{localAsrTranscriptionResult ? debugText(localAsrTranscriptionResult.converted_mime_type, "无") : "无"}</dd>
                      </div>
                      <div>
                        <dt>本地转写转换工具</dt>
                        <dd>
                          {localAsrTranscriptionResult
                            ? `${localAsrTranscriptionResult.converter_configured ? "已配置" : "未配置"}${localAsrTranscriptionResult.safe_converter_name ? ` / ${debugText(localAsrTranscriptionResult.safe_converter_name)}` : ""}`
                            : "无"}
                        </dd>
                      </div>
                      <div>
                        <dt>本地转写临时音频清理</dt>
                        <dd>{localAsrTranscriptionResult ? (localAsrTranscriptionResult.temporary_file_cleaned ? "是" : "否") : "无"}</dd>
                      </div>
                      <div>
                        <dt>本地转写原始音频清理</dt>
                        <dd>{localAsrTranscriptionResult ? (localAsrTranscriptionResult.temporary_input_cleaned ? "是" : "否") : "无"}</dd>
                      </div>
                      <div>
                        <dt>本地转写转换音频清理</dt>
                        <dd>{localAsrTranscriptionResult ? (localAsrTranscriptionResult.temporary_converted_cleaned ? "是" : "否") : "无"}</dd>
                      </div>
                      <div>
                        <dt>录音测试</dt>
                        <dd>{audioProbeStatusText(audioCaptureStatus, audioProbeUploading, audioProbeResult)}</dd>
                      </div>
                      <div>
                        <dt>录音测试说明</dt>
                        <dd>{debugText(audioProbeHint(audioCaptureStatus, audioProbeUploading, audioProbeResult))}</dd>
                      </div>
                      <div>
                        <dt>录音时长</dt>
                        <dd>{audioProbeResult ? `${audioProbeResult.duration_ms} ms` : "无"}</dd>
                      </div>
                      <div>
                        <dt>录音大小</dt>
                        <dd>{audioProbeResult ? audioBytesText(audioProbeResult.size_bytes) : "无"}</dd>
                      </div>
                      <div>
                        <dt>录音格式</dt>
                        <dd>{audioProbeResult ? audioFormatSummaryText(audioProbeResult.mime_type) : "无"}</dd>
                      </div>
                      <div>
                        <dt>录音格式提示</dt>
                        <dd>{audioProbeResult ? debugText(audioFormatConversionHint(audioProbeResult.mime_type), "无") : "无"}</dd>
                      </div>
                      <div>
                        <dt>临时音频清理</dt>
                        <dd>{audioProbeResult ? (audioProbeResult.temporary_file_cleaned ? "是" : "否") : "无"}</dd>
                      </div>
                    </dl>
                  </section>

                  <section className="debugSection">
                    <h3>模型路由</h3>
                    <dl className="debugFacts">
                      <div>
                        <dt>{formatDebugLabel("selected_model")}</dt>
                        <dd>{debugText(chatDebug.selected_model ?? providerDebug.selected_model)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("model_route_mode")}</dt>
                        <dd>{debugText(chatDebug.model_route_mode ?? providerDebug.model_route_mode)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("route_reason")}</dt>
                        <dd>{debugText(chatDebug.route_reason ?? providerDebug.route_reason)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("route_intent")}</dt>
                        <dd>{debugText(chatDebug.route_intent ?? providerDebug.route_intent ?? chatDebug.intent)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("complexity")}</dt>
                        <dd>{debugText(chatDebug.estimated_complexity ?? providerDebug.estimated_complexity)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("provider_latency_ms")}</dt>
                        <dd>{Number(chatDebug.provider_latency_ms ?? providerDebug.provider_latency_ms ?? 0).toFixed(0)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("main_reply_model")}</dt>
                        <dd>{debugText(chatDebug.main_reply_model ?? providerDebug.main_reply_model)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("semantic_model")}</dt>
                        <dd>{debugText(chatDebug.semantic_extraction_model ?? providerDebug.semantic_extraction_model)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("fallback_reason")}</dt>
                        <dd className={chatDebug.fallback_reason || providerDebug.fallback_reason ? "debugError" : ""}>
                          {debugText(chatDebug.fallback_reason ?? providerDebug.fallback_reason)}
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("response_latency_ms")}</dt>
                        <dd>{Number(chatDebug.response_latency_ms || chatDebug.total_latency_ms || lastResponseLatencyMs || 0).toFixed(0)}</dd>
                      </div>
                    </dl>
                  </section>

                  <section className="debugSection">
                    <h3>游戏知识</h3>
                    <dl className="debugFacts">
                      <div>
                        <dt>{formatDebugLabel("active_game_id")}</dt>
                        <dd>{debugText(chatDebug.active_game_id ?? chatDebug.knowledge_game_id)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("active_source")}</dt>
                        <dd>{debugText(chatDebug.active_source ?? chatDebug.knowledge_match_source)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_available")}</dt>
                        <dd>
                          {knowledgeStatusText(
                            chatDebug.support_status,
                            chatDebug.knowledge_available,
                            chatDebug.knowledge_fallback_reason
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("support_status")}</dt>
                        <dd>{debugText(chatDebug.support_status)}</dd>
                      </div>
                      <div>
                        <dt>兜底方式</dt>
                        <dd>{knowledgeFallbackMode}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_supported_games_count")}</dt>
                        <dd>{chatDebug.knowledge_supported_games_count}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_matched")}</dt>
                        <dd>
                          <BooleanBadge value={chatDebug.knowledge_matched} />
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_retrieval_status")}</dt>
                        <dd>{knowledgeRetrievalStatusText(chatDebug.knowledge_retrieval_status)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_not_used_reason")}</dt>
                        <dd className={chatDebug.knowledge_not_used_reason ? "debugError" : ""}>
                          {knowledgeNotUsedReasonText(chatDebug.knowledge_not_used_reason)}
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_game_display_name")}</dt>
                        <dd>{debugText(chatDebug.knowledge_game_display_name)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_game_id")}</dt>
                        <dd>{debugText(chatDebug.knowledge_game_id)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_match_source")}</dt>
                        <dd>{debugText(chatDebug.knowledge_match_source)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_path")}</dt>
                        <dd>{debugText(chatDebug.knowledge_path)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("manifest_status")}</dt>
                        <dd className={chatDebug.manifest_status === "manifest_missing" ? "debugError" : ""}>
                          {debugText(chatDebug.manifest_status)}
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_pack_version")}</dt>
                        <dd>{debugText(chatDebug.knowledge_pack_version)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_pack_language")}</dt>
                        <dd>{debugText(chatDebug.knowledge_pack_language)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_pack_status")}</dt>
                        <dd>{debugText(chatDebug.knowledge_pack_status)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("coverage")}</dt>
                        <dd>{debugText(chatDebug.coverage)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("last_updated")}</dt>
                        <dd>{debugText(chatDebug.last_updated)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("matched_topics")}</dt>
                        <dd>{debugText(chatDebug.matched_topics)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("matched_terms")}</dt>
                        <dd>{debugText(chatDebug.matched_terms)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("snippets_count")}</dt>
                        <dd>{chatDebug.snippets_count}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("snippet_titles")}</dt>
                        <dd>{debugText(chatDebug.snippet_titles)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("snippet_previews")}</dt>
                        <dd>{debugText(chatDebug.snippet_previews)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("result_scores")}</dt>
                        <dd>{debugText(chatDebug.result_scores)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_used_in_prompt")}</dt>
                        <dd>
                          <BooleanBadge value={chatDebug.knowledge_used_in_prompt} />
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_confidence")}</dt>
                        <dd>{Number(chatDebug.knowledge_confidence ?? 0).toFixed(2)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_retrieval_min_score")}</dt>
                        <dd>{Number(chatDebug.knowledge_retrieval_min_score ?? 0).toFixed(0)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_fallback_reason")}</dt>
                        <dd className={chatDebug.knowledge_fallback_reason ? "debugError" : ""}>
                          {debugText(chatDebug.knowledge_fallback_reason)}
                        </dd>
                      </div>
                    </dl>
                  </section>

	                  <section className="debugSection">
	                    <h3>语义识别</h3>
	                    <dl className="debugFacts">
                      <div>
                        <dt>{formatDebugLabel("latest_user_message")}</dt>
                        <dd>{debugText(semanticDebug.latest_user_message)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("rule_result")}</dt>
                        <dd>
                          {semanticSummary(semanticDebug.rule_result)}
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("confidence")}</dt>
                        <dd>{Number(semanticDebug.rule_confidence ?? 0).toFixed(2)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("llm_called")}</dt>
                        <dd>
                          <BooleanBadge value={semanticDebug.llm_called} />
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("model")}</dt>
                        <dd>{debugText(semanticDebug.semantic_extraction_model)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("llm_result")}</dt>
                        <dd>{semanticSummary(semanticDebug.llm_result)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("final_decision")}</dt>
                        <dd>{semanticSummary(semanticDebug.final_decision)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("skip_reason")}</dt>
                        <dd>{debugText(semanticDebug.skip_reason)}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("parse_error")}</dt>
                        <dd className={semanticDebug.parse_error ? "debugError" : ""}>
                          {debugText(semanticDebug.parse_error)}
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("latency_ms")}</dt>
                        <dd>{Number(semanticDebug.semantic_extraction_latency_ms || semanticDebug.latency_ms || 0).toFixed(0)}</dd>
                      </div>
	                    </dl>
	                  </section>

	                  <details className="rawJsonDetails">
	                    <summary>原始 JSON</summary>
	                    <pre className="debugJson">
                      {JSON.stringify(
                        {
                          provider_debug: safeProviderDebug(providerDebug),
                          setup_status: setupStatus,
                          proactive: proactiveStatus,
                          game_context: gameContext,
                          game_detector: gameDetection,
                          game_session: gameSessionDebug,
                          semantic_extraction: semanticDebug,
                          memory_debug: memoryDebug,
                          memory_profile: memoryProfile,
                          pending_memory: pendingMemories,
                          prompt_preview: promptPreview,
                          backend_runtime: safeBackendRuntimeDebug(backendRuntimeStatus),
                          settings: {
                            persona_mode: appSettings.persona_mode,
                            debug_panel: appSettings.debug_panel,
                            memory_enabled: appSettings.memory_enabled,
                            pending_memory_mode: appSettings.pending_memory_mode,
                            response_length: appSettings.response_length,
                            model_preference: appSettings.model_preference,
                            proactive_companion: appSettings.proactive_companion,
                            proactive_sensitivity: appSettings.proactive_sensitivity,
                            auto_game_detection: appSettings.auto_game_detection,
                            overlay_enabled: appSettings.overlay_enabled,
                            voice_output: appSettings.voice_output,
                            voice_rate: appSettings.voice_rate,
                            voice_volume: appSettings.voice_volume
                          },
                          voice_input: {
                            main_provider: {
                              selected: mainVoiceInputProviderText(mainVoiceInputProvider),
                              status_text: mainVoiceInputStatus,
                              button_enabled: !mainVoiceInputDisabled,
                              local_asr_ready: localAsrConfigReady,
                              web_speech_available: webSpeechVoiceInputAvailable(voiceInputStatus),
                              audio_capture_supported: audioCaptureStatus.supported,
                              audio_capture_phase: audioCaptureStatus.phase,
                              local_asr_transcription_phase: localAsrTranscriptionPhase,
                              local_asr_transcription_status: localAsrTranscriptionResult?.status ?? null,
                              local_asr_language: localAsrTranscriptionResult?.language ?? null,
                              local_asr_transcript_normalized_to_simplified:
                                localAsrTranscriptionResult?.transcript_normalized_to_simplified ?? null,
                              local_asr_conversion_status: localAsrTranscriptionResult?.conversion_status ?? null,
                              local_asr_conversion_required: localAsrTranscriptionResult?.conversion_required ?? null,
                              local_asr_converter_configured: localAsrTranscriptionResult?.converter_configured ?? null
                            },
                            supported: voiceInputStatus.supported,
                            phase: voiceInputStatus.phase,
                            language: voiceInputStatus.language,
                            lastTranscriptCharacterCount: voiceInputStatus.lastTranscriptCharacterCount,
                            interimCharacterCount: voiceInputStatus.interimCharacterCount,
                            lastError: voiceInputStatus.lastError,
                            diagnostics: {
                              recognitionApiAvailable: voiceInputStatus.diagnostics.recognitionApiAvailable,
                              hasSpeechRecognition: voiceInputStatus.diagnostics.hasSpeechRecognition,
                              hasWebkitSpeechRecognition: voiceInputStatus.diagnostics.hasWebkitSpeechRecognition,
                              hasMediaDevices: voiceInputStatus.diagnostics.hasMediaDevices,
                              hasGetUserMedia: voiceInputStatus.diagnostics.hasGetUserMedia,
                              microphonePermission: voiceInputStatus.diagnostics.microphonePermission,
                              runtimeEnvironment: voiceInputRuntimeText(voiceInputStatus),
                              lastStartStatus: voiceInputStatus.diagnostics.lastStartStatus
                            }
                          },
                          local_asr: {
                            status: localAsrStatus.status,
                            available: localAsrStatus.available,
                            binary_configured: localAsrStatus.binary_configured,
                            binary_present: localAsrStatus.binary_present,
                            binary_executable: localAsrStatus.binary_executable,
                            model_configured: localAsrStatus.model_configured,
                            model_present: localAsrStatus.model_present,
                            converter_configured: localAsrStatus.converter_configured,
                            source: localAsrStatus.source,
                            display_message: localAsrStatus.display_message,
                            safe_binary_name: localAsrStatus.safe_binary_name,
                            safe_model_name: localAsrStatus.safe_model_name,
                            safe_converter_name: localAsrStatus.safe_converter_name,
                            settings: {
                              configured: localAsrSettings.configured,
                              binary_configured: localAsrSettings.binary_configured,
                              model_configured: localAsrSettings.model_configured,
                              converter_configured: localAsrSettings.converter_configured,
                              source: localAsrSettings.source,
                              safe_binary_name: localAsrSettings.safe_binary_name,
                              safe_model_name: localAsrSettings.safe_model_name,
                              safe_converter_name: localAsrSettings.safe_converter_name
                            },
                            probe: localAsrProbe
                              ? {
                                  status: localAsrProbe.status,
                                  available: localAsrProbe.available,
                                  display_message: localAsrProbe.display_message,
                                  binary_name: localAsrProbe.binary_name,
                                  model_name: localAsrProbe.model_name,
                                  duration_ms: localAsrProbe.duration_ms
                                }
                              : null,
                            transcription: localAsrTranscriptionResult
                              ? {
                                  status: localAsrTranscriptionResult.status,
                                  available: localAsrTranscriptionResult.available,
                                  display_message: localAsrTranscriptionResult.display_message,
                                  transcript_char_count: localAsrTranscriptionResult.transcript_char_count,
                                  language: localAsrTranscriptionResult.language,
                                  transcript_normalized_to_simplified:
                                    localAsrTranscriptionResult.transcript_normalized_to_simplified,
                                  duration_ms: localAsrTranscriptionResult.duration_ms,
                                  size_bytes: localAsrTranscriptionResult.size_bytes,
                                  mime_type: localAsrTranscriptionResult.mime_type,
                                  audio_format: localAsrTranscriptionResult.audio_format,
                                  format_summary: audioFormatSummaryText(localAsrTranscriptionResult.mime_type),
                                  format_warning: audioFormatConversionHint(localAsrTranscriptionResult.mime_type) || null,
                                  conversion_status: localAsrTranscriptionResult.conversion_status,
                                  conversion_summary: audioConversionStatusText(localAsrTranscriptionResult.conversion_status),
                                  conversion_required: localAsrTranscriptionResult.conversion_required,
                                  converted_mime_type: localAsrTranscriptionResult.converted_mime_type,
                                  converter_configured: localAsrTranscriptionResult.converter_configured,
                                  safe_converter_name: localAsrTranscriptionResult.safe_converter_name,
                                  temporary_file_cleaned: localAsrTranscriptionResult.temporary_file_cleaned,
                                  temporary_input_cleaned: localAsrTranscriptionResult.temporary_input_cleaned,
                                  temporary_converted_cleaned: localAsrTranscriptionResult.temporary_converted_cleaned,
                                  binary_name: localAsrTranscriptionResult.binary_name,
                                  model_name: localAsrTranscriptionResult.model_name
                                }
                              : null
                          },
                          audio_capture: {
                            supported: audioCaptureStatus.supported,
                            phase: audioCaptureStatus.phase,
                            last_error: audioCaptureStatus.lastError,
                            uploading: audioProbeUploading,
                            probe: audioProbeResult
                              ? {
                                  status: audioProbeResult.status,
                                  available: audioProbeResult.available,
                                  display_message: audioProbeResult.display_message,
                                  duration_ms: audioProbeResult.duration_ms,
                                  size_bytes: audioProbeResult.size_bytes,
                                  mime_type: audioProbeResult.mime_type,
                                  format_summary: audioFormatSummaryText(audioProbeResult.mime_type),
                                  format_warning: audioFormatConversionHint(audioProbeResult.mime_type) || null,
                                  temporary_file_cleaned: audioProbeResult.temporary_file_cleaned
                                }
                              : null
                          },
                          chat: {
                            intent: chatDebug.intent,
                            selected_model: chatDebug.selected_model,
                            model_route_mode: chatDebug.model_route_mode,
                            route_reason: chatDebug.route_reason,
                            route_intent: chatDebug.route_intent,
                            estimated_complexity: chatDebug.estimated_complexity,
                            provider_latency_ms: chatDebug.provider_latency_ms,
                            semantic_extraction_model: chatDebug.semantic_extraction_model,
                            main_reply_model: chatDebug.main_reply_model,
                            knowledge_matched: chatDebug.knowledge_matched,
                            active_game_id: chatDebug.active_game_id,
                            active_game_display_name: chatDebug.active_game_display_name,
                            active_source: chatDebug.active_source,
                            support_status: chatDebug.support_status,
                            knowledge_available: chatDebug.knowledge_available,
                            knowledge_game_id: chatDebug.knowledge_game_id,
                            knowledge_game_display_name: chatDebug.knowledge_game_display_name,
                            knowledge_match_source: chatDebug.knowledge_match_source,
                            knowledge_path: chatDebug.knowledge_path,
                            manifest_path: chatDebug.manifest_path,
                            manifest_status: chatDebug.manifest_status,
                            knowledge_pack_version: chatDebug.knowledge_pack_version,
                            knowledge_pack_language: chatDebug.knowledge_pack_language,
                            knowledge_pack_status: chatDebug.knowledge_pack_status,
                            coverage: chatDebug.coverage,
                            last_updated: chatDebug.last_updated,
                            knowledge_supported_games_count: chatDebug.knowledge_supported_games_count,
                            knowledge_fallback_reason: chatDebug.knowledge_fallback_reason,
                            knowledge_confidence: chatDebug.knowledge_confidence,
                            matched_topics: chatDebug.matched_topics,
                            snippets_count: chatDebug.snippets_count,
                            snippet_titles: chatDebug.snippet_titles,
                            snippet_previews: chatDebug.snippet_previews,
                            matched_terms: chatDebug.matched_terms,
                            result_scores: chatDebug.result_scores,
                            knowledge_used_in_prompt: chatDebug.knowledge_used_in_prompt,
                            knowledge_retrieval_status: chatDebug.knowledge_retrieval_status,
                            knowledge_not_used_reason: chatDebug.knowledge_not_used_reason,
                            knowledge_retrieval_min_score: chatDebug.knowledge_retrieval_min_score,
                            fallback_reason: chatDebug.fallback_reason,
                            last_latency_ms: chatDebug.total_latency_ms,
                            llm_latency_ms: chatDebug.llm_latency_ms,
                            memory_latency_ms: chatDebug.memory_latency_ms,
                            reasoning_enabled: chatDebug.thinking_enabled,
                            reasoning_effort: chatDebug.reasoning_effort,
                            reply_segments_count: chatDebug.reply_segments_count,
                            segmenter_mode: chatDebug.segmenter_mode,
                            last_interim_placeholder_shown: lastInterimPlaceholderShown,
                            last_response_latency_ms: lastResponseLatencyMs
                          },
                          lastError: lastError || null,
                          lastRawError: lastRawError || null
                        },
                        null,
                        2
                      )}
                    </pre>
                  </details>
                </div>
              )}
            </section>
          )}

          {debugPanelVisible && (
            <section className="infoCard foldPanel" aria-label="回复上下文预览" id="prompt-preview-panel" style={{ order: 4 }}>
              <button
                className="foldHeader"
                aria-expanded={promptPreviewOpen}
                onClick={() => setPromptPreviewOpen((open) => !open)}
              >
                <span>回复上下文预览</span>
                {promptPreviewOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
              {promptPreviewOpen && (
                <div className="debugPanel">
                  <dl className="debugFacts">
                    <div>
                      <dt>{formatDebugLabel("persona_mode")}</dt>
                      <dd>{debugText(promptPreview.persona_mode)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("current_user_message")}</dt>
                      <dd>{debugText(promptPreview.current_user_message)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("prompt_order")}</dt>
                      <dd>{formatPromptOrder(promptPreview.prompt_order)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("selected_model")}</dt>
                      <dd>{debugText(promptModelRoute.selected_model)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("route_reason")}</dt>
                      <dd>{debugText(promptModelRoute.route_reason)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("route_intent")}</dt>
                      <dd>{debugText(promptModelRoute.route_intent)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("complexity")}</dt>
                      <dd>{debugText(promptModelRoute.estimated_complexity)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("main_reply_model")}</dt>
                      <dd>{debugText(promptModelRoute.main_reply_model)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("provider_latency_ms")}</dt>
                      <dd>{debugText(promptModelRoute.provider_latency_ms)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("session_focus")}</dt>
                      <dd>{debugText(sessionFocusSummary.prompt_line ?? sessionFocusSummary.boss)}</dd>
                    </div>
                    <div>
                      <dt>游戏上下文</dt>
                      <dd>
                        {debugText(promptGameContext.active_game_display_name)} /{" "}
                        {debugText(promptGameContext.active_source)} /{" "}
                        {knowledgeStatusText(
                          String(promptGameContext.support_status || ""),
                          Boolean(promptGameContext.knowledge_available),
                          String(promptGameContext.fallback_reason || "")
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("previous_game")}</dt>
                      <dd>{debugText(promptGameContext.previous_game)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("game_switched")}</dt>
                      <dd>{debugText(promptGameContext.game_switched)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("game_state")}</dt>
                      <dd>
                        {debugText(gameStateSummary.current_game)} / {bossName(gameStateSummary.current_boss)} /{" "}
                        {debugText(gameStateSummary.current_activity)} / {debugText(gameStateSummary.freshness)}
                      </dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("knowledge_matched")}</dt>
                      <dd>{debugText(knowledgeSummary.knowledge_matched)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("knowledge_retrieval_status")}</dt>
                      <dd>{knowledgeRetrievalStatusText(knowledgeSummary.retrieval_status)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("knowledge_not_used_reason")}</dt>
                      <dd className={knowledgeSummary.not_used_reason ? "debugError" : ""}>
                        {knowledgeNotUsedReasonText(knowledgeSummary.not_used_reason)}
                      </dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("active_game_id")}</dt>
                      <dd>{debugText(knowledgeSummary.active_game_id ?? knowledgeSummary.game_id)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("active_source")}</dt>
                      <dd>{debugText(knowledgeSummary.active_source ?? knowledgeSummary.match_source)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("knowledge_available")}</dt>
                      <dd>
                        {knowledgeStatusText(
                          String(knowledgeSummary.support_status || ""),
                          Boolean(knowledgeSummary.knowledge_available),
                          String(knowledgeSummary.fallback_reason || "")
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("support_status")}</dt>
                      <dd>{debugText(knowledgeSummary.support_status)}</dd>
                    </div>
                    <div>
                      <dt>兜底方式</dt>
                      <dd>
                        {fallbackModeText(
                          Boolean(knowledgeSummary.knowledge_available),
                          Boolean(knowledgeSummary.knowledge_used_in_prompt),
                          String(knowledgeSummary.fallback_reason || "")
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("supported_games_count")}</dt>
                      <dd>{debugText(knowledgeSummary.supported_games_count)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("matched_game_display_name")}</dt>
                      <dd>{debugText(knowledgeSummary.matched_game_display_name)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("matched_game_id")}</dt>
                      <dd>{debugText(knowledgeSummary.matched_game_id ?? knowledgeSummary.game_id)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("match_source")}</dt>
                      <dd>{debugText(knowledgeSummary.match_source)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("knowledge_path")}</dt>
                      <dd>{debugText(knowledgeSummary.knowledge_path)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("manifest_status")}</dt>
                      <dd className={knowledgeSummary.manifest_status === "manifest_missing" ? "debugError" : ""}>
                        {debugText(knowledgeSummary.manifest_status)}
                      </dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("knowledge_pack_version")}</dt>
                      <dd>{debugText(knowledgeSummary.knowledge_pack_version)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("knowledge_pack_language")}</dt>
                      <dd>{debugText(knowledgeSummary.knowledge_pack_language)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("knowledge_pack_status")}</dt>
                      <dd>{debugText(knowledgeSummary.knowledge_pack_status)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("coverage")}</dt>
                      <dd>{debugText(knowledgeSummary.coverage)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("last_updated")}</dt>
                      <dd>{debugText(knowledgeSummary.last_updated)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("matched_topics")}</dt>
                      <dd>{debugText(knowledgeSummary.matched_topics)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("matched_terms")}</dt>
                      <dd>{debugText(knowledgeSummary.matched_terms)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("snippets_count")}</dt>
                      <dd>{debugText(knowledgeSummary.snippets_count)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("snippet_titles")}</dt>
                      <dd>{debugText(knowledgeSummary.snippet_titles)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("snippet_previews")}</dt>
                      <dd>{debugText(knowledgeSummary.snippet_previews)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("result_scores")}</dt>
                      <dd>{debugText(knowledgeSummary.result_scores)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("knowledge_used_in_prompt")}</dt>
                      <dd>{debugText(knowledgeSummary.knowledge_used_in_prompt)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("confidence")}</dt>
                      <dd>{debugText(knowledgeSummary.confidence)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("knowledge_retrieval_min_score")}</dt>
                      <dd>{debugText(knowledgeSummary.retrieval_min_score)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("fallback_reason")}</dt>
                      <dd className={knowledgeSummary.fallback_reason ? "debugError" : ""}>
                        {debugText(knowledgeSummary.fallback_reason)}
                      </dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("memory")}</dt>
                      <dd>
                        已注入 {injectedMemory.length} / 已跳过 {skippedMemory.length}
                      </dd>
                    </div>
                  </dl>
                  <div className="debugSubgroup">
                    <h4>注入记忆</h4>
                    <ul className="debugList">
                      {injectedMemory.map((item, index) => (
                        <li key={`${debugListText(item)}-${index}`}>{debugListText(item)}</li>
                      ))}
                      {injectedMemory.length === 0 && <li>无</li>}
                    </ul>
                  </div>
                  <div className="debugSubgroup">
                    <h4>跳过记忆</h4>
                    <ul className="debugList">
                      {skippedMemory.map((item, index) => (
                        <li key={`${debugListText(item)}-${index}`}>{debugListText(item)}</li>
                      ))}
                      {skippedMemory.length === 0 && <li>无</li>}
                    </ul>
                  </div>
                  <div className="debugSubgroup">
                    <h4>警告</h4>
                    <ul className="debugList">
                      {promptPreview.warnings.map((warning) => (
                        <li key={warning}>{debugText(warning)}</li>
                      ))}
                      {promptPreview.warnings.length === 0 && <li>无</li>}
                    </ul>
                  </div>
                </div>
              )}
            </section>
          )}
        </aside>
      </section>
      </section>
    </main>
  );
}
