import {
  Bot,
  Brain,
  Bug,
  ChevronDown,
  ChevronUp,
  Database,
  FileText,
  Gamepad2,
  KeyRound,
  MessageSquare,
  Mic,
  RefreshCw,
  Send,
  Settings,
  Sparkles,
  X
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  api,
  ApiRequestError,
  AppSettings,
  ChatDebugResponse,
  GameContextResponse,
  GameDetectionResponse,
  GameSessionDebugResponse,
  GameStatus,
  MemoryDebugResponse,
  PendingMemory,
  PromptPreviewResponse,
  ProactiveStatusResponse,
  ProviderDebugResponse,
  SemanticExtractionDebugResponse,
  SetupStatus,
  UserProfileMemory
} from "../shared/api";
import type { BackendRuntimeStatus } from "../shared/runtime";

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
  knowledge_used_in_prompt: false
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
  onboarding_completed: false,
  onboarding_last_seen_at: null
};

export const INTERIM_PLACEHOLDERS = ["……", "……嗯", "嗯……"];
const PLACEHOLDER_DELAY_MS = 3000;
const PROACTIVE_CHECK_INTERVAL_MS = 30000;
const AUTO_SCROLL_THRESHOLD_PX = 120;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const nextSegmentDelay = () => 500 + Math.floor(Math.random() * 401);

const pickPlaceholder = () => INTERIM_PLACEHOLDERS[Math.floor(Math.random() * INTERIM_PLACEHOLDERS.length)];

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
  auto_game_detection: "自动游戏检测",
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
  next_possible_trigger_at: "下次可能触发",
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
  unknown_game: "未接入知识库",
  none: "无",
  normal: "普通",
  not_connected: "未连接",
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
  user_is_typing: "正在输入",
  user_preference: "用户偏好",
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
  if (status.backend_started_from === "configured_binary") return "指定 backend binary";
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
  const [backendRuntimeStatus, setBackendRuntimeStatus] = useState<BackendRuntimeStatus>(emptyBackendRuntimeStatus);
  const [backendRuntimeAvailable, setBackendRuntimeAvailable] = useState(false);
  const [pendingMemories, setPendingMemories] = useState<PendingMemory[]>([]);
  const [pendingMemoryBusyId, setPendingMemoryBusyId] = useState("");
  const [debugActionBusy, setDebugActionBusy] = useState("");
  const [appSettings, setAppSettings] = useState<AppSettings>(defaultAppSettings);
  const [settingsBusy, setSettingsBusy] = useState("");
  const [backendRuntimeBusy, setBackendRuntimeBusy] = useState(false);
  const [gameContextBusy, setGameContextBusy] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { id: "hello", role: "assistant", text: "我在。想问的时候就说。", createdAt: new Date().toISOString() }
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [debugOpen, setDebugOpen] = useState(true);
  const [promptPreviewOpen, setPromptPreviewOpen] = useState(false);
  const [setupHelpOpen, setSetupHelpOpen] = useState(false);
  const [demoDocHintOpen, setDemoDocHintOpen] = useState(false);
  const [demoResetFeedback, setDemoResetFeedback] = useState("");
  const [onboardingDismissedThisSession, setOnboardingDismissedThisSession] = useState(false);
  const [onboardingReopened, setOnboardingReopened] = useState(false);
  const [lastError, setLastError] = useState("");
  const [lastRawError, setLastRawError] = useState("");
  const [lastInterimPlaceholderShown, setLastInterimPlaceholderShown] = useState(false);
  const [lastResponseLatencyMs, setLastResponseLatencyMs] = useState(0);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const shouldAutoScrollRef = useRef(true);
  const forceNextScrollRef = useRef(true);

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

  const refreshStatus = useCallback(async () => {
    try {
      setLastError("");
      setLastRawError("");
      await api.health();
      const currentSetupStatus = await api.setupStatus();
      setBackendStatus("connected");
      setSetupStatus(currentSetupStatus);
      setAppSettings(await api.settings());
      setGameStatus(await api.gameStatus());
      const currentGameContext = await api.gameContext();
      setGameContext(currentGameContext);
      setGameDetection(currentGameContext.detected_game);
      setMemoryProfile(await api.memoryProfile());
      setMemoryDebug(await api.memoryDebug());
      setChatDebug(await api.chatDebug());
      setProviderDebug(await api.providerDebug());
      setProactiveStatus(await api.proactiveStatus());
      setGameSessionDebug(await api.gameSessionDebug());
      setSemanticDebug(await api.semanticExtractionDebug());
      setPromptPreview(await api.promptPreview());
      setPendingMemories(await api.pendingMemories());
    } catch (error) {
      setBackendStatus("disconnected");
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "后端未连接"));
    }
  }, []);

  const updateAppSettings = async (patch: Partial<AppSettings>) => {
    const busyKey = Object.keys(patch)[0] ?? "settings";
    setSettingsBusy(busyKey);
    try {
      setLastError("");
      setLastRawError("");
      const updated = await api.updateSettings(patch);
      setAppSettings(updated);
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

  const updateBackendAutoStart = async (enabled: boolean) => {
    const runtime = window.reilinkRuntime;
    if (!runtime) return;
    setBackendRuntimeBusy(true);
    try {
      setLastError("");
      setLastRawError("");
      setBackendRuntimeStatus(await runtime.setBackendAutoStart(enabled));
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "本地后端自动启动设置失败"));
    } finally {
      setBackendRuntimeBusy(false);
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
      if (status.backend_status === "connected") {
        void refreshStatus();
      }
    };
    void runtime.getBackendStatus().then(applyStatus).catch(() => {
      if (active) {
        setBackendRuntimeStatus({
          ...emptyBackendRuntimeStatus,
          backend_start_error: "无法读取本地后端运行状态。",
          backend_status: "failed"
        });
      }
    });
    const unsubscribe = runtime.onBackendStatus(applyStatus);
    return () => {
      active = false;
      unsubscribe();
    };
  }, [refreshStatus]);

  const checkProactive = useCallback(async () => {
    if (backendStatus !== "connected" || appSettings.proactive_companion !== "on" || sending) return;
    try {
      const response = await api.checkProactive("default", Boolean(input.trim()), backendStatus === "connected");
      if (response.should_send && response.message) {
        queueMessageAutoScroll();
        setMessages((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            text: response.message,
            createdAt: new Date().toISOString(),
            messageType: "proactive",
            triggerType: response.trigger_type
          }
        ]);
      }
      setProactiveStatus(await api.proactiveStatus());
    } catch (error) {
      setLastRawError(errorRawText(error));
      setLastError(productErrorText(error, "主动陪伴检查失败"));
    }
  }, [appSettings.proactive_companion, backendStatus, input, queueMessageAutoScroll, sending]);

  useEffect(() => {
    if (backendStatus !== "connected" || appSettings.proactive_companion !== "on") return undefined;
    const interval = window.setInterval(() => void checkProactive(), PROACTIVE_CHECK_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [appSettings.proactive_companion, backendStatus, checkProactive]);

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || sending) return;
    const userMessage: Message = { id: crypto.randomUUID(), role: "user", text: trimmed, createdAt: new Date().toISOString() };
    const placeholderId = crypto.randomUUID();
    let placeholderShown = false;
    const requestStartedAt = Date.now();
    setLastInterimPlaceholderShown(false);
    setLastError("");
    setLastRawError("");
    queueMessageAutoScroll(true);
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setSending(true);
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
      queueMessageAutoScroll();
      setMessages((current) => current.filter((message) => message.id !== placeholderId));
      const segments = response.reply_segments.length > 0 ? response.reply_segments : [response.reply];
      for (const [index, segment] of segments.entries()) {
        if (index > 0) {
          await sleep(nextSegmentDelay());
        }
        queueMessageAutoScroll();
        setMessages((current) => [
          ...current,
          { id: crypto.randomUUID(), role: "assistant", text: segment, createdAt: new Date().toISOString(), pending: false }
        ]);
      }
      setLastInterimPlaceholderShown(placeholderShown);
      await refreshStatus();
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
      } else {
        await api.ignorePendingMemory(id);
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
    setAppSettings(updated);
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
        setDemoResetFeedback("已重置游戏状态");
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
            <span className={`connection ${backendStatus}`}>{runtimeStatusLabel}</span>
            <button aria-label="刷新状态" className="iconButton soft" onClick={refreshStatus}>
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
              <button className="iconButton disabled" type="button" aria-label="按住说话实验功能" disabled>
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
              <div className="demoResetPanel" role="group" aria-label="演示与重置">
                <div className="demoResetHeader">
                  <div>
                    <span>演示与重置</span>
                    <strong>Demo & Reset</strong>
                  </div>
                </div>
                <div className="demoResetActions">
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
                    重置游戏状态
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
                    一键重置演示状态
                  </button>
                </div>
                <p className="settingHint">一键重置不会清空长期记忆。危险操作会先确认。</p>
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
                        <dt>{formatDebugLabel("snippets_count")}</dt>
                        <dd>{chatDebug.snippets_count}</dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("snippet_titles")}</dt>
                        <dd>{debugText(chatDebug.snippet_titles)}</dd>
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
                          provider_debug: providerDebug,
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
                          backend_runtime: backendRuntimeStatus,
                          settings: {
                            persona_mode: appSettings.persona_mode,
                            debug_panel: appSettings.debug_panel,
                            memory_enabled: appSettings.memory_enabled,
                            pending_memory_mode: appSettings.pending_memory_mode,
                            response_length: appSettings.response_length,
                            model_preference: appSettings.model_preference,
                            proactive_companion: appSettings.proactive_companion,
                            proactive_sensitivity: appSettings.proactive_sensitivity,
                            auto_game_detection: appSettings.auto_game_detection
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
                            knowledge_used_in_prompt: chatDebug.knowledge_used_in_prompt,
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
                      <dt>{formatDebugLabel("snippets_count")}</dt>
                      <dd>{debugText(knowledgeSummary.snippets_count)}</dd>
                    </div>
                    <div>
                      <dt>{formatDebugLabel("snippet_titles")}</dt>
                      <dd>{debugText(knowledgeSummary.snippet_titles)}</dd>
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
