import {
  Bot,
  Brain,
  Bug,
  ChevronDown,
  ChevronUp,
  Database,
  Gamepad2,
  MessageSquare,
  Mic,
  RefreshCw,
  Send,
  Settings,
  Sparkles
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  api,
  AppSettings,
  ChatDebugResponse,
  GameSessionDebugResponse,
  GameStatus,
  MemoryDebugResponse,
  PendingMemory,
  PromptPreviewResponse,
  ProactiveStatusResponse,
  ProviderDebugResponse,
  SemanticExtractionDebugResponse,
  UserProfileMemory
} from "../shared/api";

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: string;
  pending?: boolean;
  messageType?: "chat" | "proactive";
  triggerType?: string;
};

const idleStatus: GameStatus = {
  game_id: null,
  game_name: null,
  process_name: null,
  status: "idle",
  confidence: 0,
  tags: []
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
  proactive_sensitivity: "low"
};

export const INTERIM_PLACEHOLDERS = ["……", "……嗯", "嗯……"];
const PLACEHOLDER_DELAY_MS = 3000;
const PROACTIVE_CHECK_INTERVAL_MS = 30000;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const nextSegmentDelay = () => 500 + Math.floor(Math.random() * 401);

const pickPlaceholder = () => INTERIM_PLACEHOLDERS[Math.floor(Math.random() * INTERIM_PLACEHOLDERS.length)];

const asRecord = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};

const asArray = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

const labelMap: Record<string, string> = {
  activity: "当前活动",
  active_candidate_triggers: "候选触发器",
  block_reason: "阻断原因",
  boss_history: "Boss 记录",
  complexity: "复杂度",
  confidence: "规则置信度",
  cooldown_remaining_seconds: "冷却剩余",
  current_boss: "当前 Boss",
  current_game: "当前游戏",
  current_session: "当前会话",
  current_session_context: "当前会话",
  current_user_message: "当前用户消息",
  death_count: "死亡次数",
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
  game_id: "游戏",
  idle_for_seconds: "已空闲时间",
  idle_threshold_seconds: "空闲触发阈值",
  initial_grace_remaining_seconds: "初始等待剩余",
  last_attempted: "最近挑战",
  last_cleared: "最近通过",
  last_trigger_reason: "上次触发原因",
  last_triggered_at: "上次触发时间",
  last_triggered_type: "上次触发类型",
  last_user_activity_at: "最近用户活动",
  latency_ms: "耗时",
  latest_user: "最近用户消息",
  latest_user_message: "最近用户消息",
  knowledge: "游戏知识",
  knowledge_game_id: "游戏",
  knowledge_matched: "知识匹配",
  knowledge_summary: "游戏知识摘要",
  knowledge_used_in_prompt: "已用于 Prompt",
  llm_called: "是否调用 LLM",
  llm_event: "LLM 游戏事件",
  llm_memory: "LLM 记忆",
  llm_result: "LLM 判断",
  main_reply_model: "回复模型",
  memory: "记忆摘要",
  model: "模型",
  model_route_mode: "路由模式",
  matched_topics: "匹配主题",
  next_possible_trigger_at: "下次可能触发",
  parse_error: "解析错误",
  persona: "人格",
  persona_mode: "人格模式",
  prompt_order: "注入顺序",
  provider_latency_ms: "模型耗时",
  requires_user_activity_after_proactive: "等待用户回应",
  response_latency_ms: "回复耗时",
  route_intent: "意图类型",
  route_reason: "路由原因",
  rule_result: "规则判断",
  semantic_model: "语义识别模型",
  selected_model: "选用模型",
  sensitivity: "主动灵敏度",
  session_focus: "会话焦点",
  session_focus_summary: "会话焦点",
  skip_reason: "跳过原因",
  snippet_titles: "片段标题",
  snippets_count: "片段数量",
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
  manual: "手动",
  medium: "中",
  "memory boss conflicts with fresh game state": "记忆里的 Boss 与当前游戏状态冲突",
  minimal: "minimal（自然）",
  no_candidate_trigger: "暂无可触发项",
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
  short: "简短",
  simple_game_reminder: "简单游戏提醒",
  show: "显示",
  stale: "已过期",
  user_is_typing: "正在输入",
  user_preference: "用户偏好",
  waiting_for_user_activity_after_proactive: "等待用户回应",
  weak: "较弱"
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

export function App() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "disconnected">("checking");
  const [gameStatus, setGameStatus] = useState<GameStatus>(idleStatus);
  const [memoryProfile, setMemoryProfile] = useState<UserProfileMemory>(emptyProfile);
  const [memoryDebug, setMemoryDebug] = useState<MemoryDebugResponse>(emptyMemoryDebug);
  const [chatDebug, setChatDebug] = useState<ChatDebugResponse>(emptyChatDebug);
  const [providerDebug, setProviderDebug] = useState<ProviderDebugResponse>(emptyProviderDebug);
  const [proactiveStatus, setProactiveStatus] = useState<ProactiveStatusResponse>(emptyProactiveStatus);
  const [gameSessionDebug, setGameSessionDebug] = useState<GameSessionDebugResponse>(emptyGameSessionDebug);
  const [semanticDebug, setSemanticDebug] = useState<SemanticExtractionDebugResponse>(emptySemanticExtractionDebug);
  const [promptPreview, setPromptPreview] = useState<PromptPreviewResponse>(emptyPromptPreview);
  const [pendingMemories, setPendingMemories] = useState<PendingMemory[]>([]);
  const [pendingMemoryBusyId, setPendingMemoryBusyId] = useState("");
  const [debugActionBusy, setDebugActionBusy] = useState("");
  const [appSettings, setAppSettings] = useState<AppSettings>(defaultAppSettings);
  const [settingsBusy, setSettingsBusy] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { id: "hello", role: "assistant", text: "我在。想问的时候就说。", createdAt: new Date().toISOString() }
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [debugOpen, setDebugOpen] = useState(true);
  const [promptPreviewOpen, setPromptPreviewOpen] = useState(false);
  const [lastError, setLastError] = useState("");
  const [lastInterimPlaceholderShown, setLastInterimPlaceholderShown] = useState(false);
  const [lastResponseLatencyMs, setLastResponseLatencyMs] = useState(0);

  const refreshStatus = async () => {
    try {
      setLastError("");
      await api.health();
      setBackendStatus("connected");
      setAppSettings(await api.settings());
      setGameStatus(await api.gameStatus());
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
      setLastError(error instanceof Error ? error.message : "后端暂时连不上");
    }
  };

  const updateAppSettings = async (patch: Partial<AppSettings>) => {
    const busyKey = Object.keys(patch)[0] ?? "settings";
    setSettingsBusy(busyKey);
    try {
      setLastError("");
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
      setLastError(error instanceof Error ? error.message : "设置更新失败");
    } finally {
      setSettingsBusy("");
    }
  };

  useEffect(() => {
    void refreshStatus();
  }, []);

  const checkProactive = useCallback(async () => {
    if (backendStatus !== "connected" || appSettings.proactive_companion !== "on" || sending) return;
    try {
      const response = await api.checkProactive("default", Boolean(input.trim()), backendStatus === "connected");
      if (response.should_send && response.message) {
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
      setLastError(error instanceof Error ? error.message : "主动陪伴检查失败");
    }
  }, [appSettings.proactive_companion, backendStatus, input, sending]);

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
    setMessages((current) => [...current, userMessage]);
    setInput("");
    setSending(true);
    const placeholderTimer = window.setTimeout(() => {
      placeholderShown = true;
      setLastInterimPlaceholderShown(true);
      setMessages((current) => [
        ...current,
        { id: placeholderId, role: "assistant", text: pickPlaceholder(), createdAt: new Date().toISOString(), pending: true }
      ]);
    }, PLACEHOLDER_DELAY_MS);
    try {
      const response = await api.chat(trimmed);
      window.clearTimeout(placeholderTimer);
      setLastResponseLatencyMs(Date.now() - requestStartedAt);
      setMessages((current) => current.filter((message) => message.id !== placeholderId));
      const segments = response.reply_segments.length > 0 ? response.reply_segments : [response.reply];
      for (const [index, segment] of segments.entries()) {
        if (index > 0) {
          await sleep(nextSegmentDelay());
        }
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
      const errorMessage = error instanceof Error ? error.message : "发送失败";
      setLastError(errorMessage);
      const reply = /timeout|timed out|504|太慢/i.test(errorMessage)
        ? "线路太慢了。等一下再试。"
        : "线路有点安静。先检查后端。";
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
      setLastError(error instanceof Error ? error.message : "待确认记忆更新失败");
    } finally {
      setPendingMemoryBusyId("");
    }
  };

  const handleDebugAction = async (
    action: "refresh" | "reset-game-session" | "reset-memory" | "clear-pending"
  ) => {
    setDebugActionBusy(action);
    try {
      setLastError("");
      if (action === "reset-game-session") {
        await api.resetGameSession();
      } else if (action === "reset-memory") {
        await api.resetMemory();
      } else if (action === "clear-pending") {
        await api.clearPendingMemories();
      }
      await refreshStatus();
    } catch (error) {
      setLastError(error instanceof Error ? error.message : "调试操作失败");
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
  const displayGame = gameSessionDebug.current_game ?? gameStatus.game_name ?? "idle";
  const displayBoss = gameSessionDebug.current_boss?.name ?? null;
  const companionName = "Rei";
  const companionSubtitle = "安静、冷淡的游戏陪伴";
  const companionStatus = backendStatus === "connected" ? "在线" : backendStatus === "checking" ? "检查中" : "离线";

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
            <span className={`connection ${backendStatus}`}>{statusLabel}</span>
            <button aria-label="刷新状态" className="iconButton soft" onClick={refreshStatus}>
              <RefreshCw size={17} />
            </button>
          </div>
        </header>

        <section className="workspaceGrid">
          <section className="chatColumn" aria-label="主聊天界面" id="chat-panel">
            <div className="timelineMarker">今天</div>

          <section className="chatPanel" aria-label="聊天面板">
            <div className="messages">
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
          <section className="infoCard settingsPanel" aria-label="设置" id="settings-panel">
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
            <p className="settingHint">本地保存到 settings.json，不包含密钥。主动陪伴当前为{debugText(appSettings.proactive_companion)}。</p>
          </section>

          <section className="infoCard pendingPanel" aria-label="待确认记忆" id="pending-memory-panel">
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

          <section className="infoCard gameSessionPanel" aria-label="游戏状态" id="game-session-panel">
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
            <section className="infoCard foldPanel" aria-label="调试面板" id="debug-panel">
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
                        <dt>{formatDebugLabel("knowledge_matched")}</dt>
                        <dd>
                          <BooleanBadge value={chatDebug.knowledge_matched} />
                        </dd>
                      </div>
                      <div>
                        <dt>{formatDebugLabel("knowledge_game_id")}</dt>
                        <dd>{debugText(chatDebug.knowledge_game_id)}</dd>
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
                          proactive: proactiveStatus,
                          game_session: gameSessionDebug,
                          semantic_extraction: semanticDebug,
                          memory_debug: memoryDebug,
                          memory_profile: memoryProfile,
                          pending_memory: pendingMemories,
                          prompt_preview: promptPreview,
                          settings: appSettings,
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
                            knowledge_game_id: chatDebug.knowledge_game_id,
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
                          lastError: lastError || null
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
            <section className="infoCard foldPanel" aria-label="Prompt 预览" id="prompt-preview-panel">
              <button
                className="foldHeader"
                aria-expanded={promptPreviewOpen}
                onClick={() => setPromptPreviewOpen((open) => !open)}
              >
                <span>Prompt 预览</span>
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
                      <dt>{formatDebugLabel("knowledge_game_id")}</dt>
                      <dd>{debugText(knowledgeSummary.game_id)}</dd>
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
