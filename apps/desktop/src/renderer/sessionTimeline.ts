import type { ReiLinkEvent } from "../shared/events";

export const SESSION_TIMELINE_LIMIT = 50;
export const SESSION_TIMELINE_SUMMARY_MAX_LENGTH = 96;

export type SessionTimelineType =
  | "game_selected"
  | "boss_detected"
  | "death_count_changed"
  | "frustration_changed"
  | "boss_cleared"
  | "knowledge_used"
  | "proactive_shown"
  | "memory_accepted"
  | "memory_ignored";

export type SessionTimelineSource =
  | "game_context"
  | "game_session"
  | "knowledge"
  | "proactive"
  | "memory";

export type SessionTimelineItem = {
  id: string;
  timestamp: string;
  type: SessionTimelineType;
  source: SessionTimelineSource;
  summary: string;
};

const SENSITIVE_PATTERNS = [
  /api[_\s-]*key/gi,
  /authorization/gi,
  /\.env/gi,
  /raw\s*(prompt|json|stdout|stderr|exception)/gi,
  /stdout/gi,
  /stderr/gi,
  /transcript/gi,
  /\/(?:users|applications|volumes|tmp|private\/var)\/[^，。；,;\n\r]+/gi,
  /[a-z]:\\[^，。；,;\n\r]+/gi
];

const triggerLabels: Record<string, string> = {
  repeated_death: "反复死亡",
  frustration_loop: "挫败循环",
  idle_silence: "空闲沉默",
  late_night: "深夜提醒",
  none: "主动陪伴"
};

const normalizeWhitespace = (value: string) => value.replace(/\s+/g, " ").trim();

export const sanitizeSessionTimelineText = (
  value: unknown,
  maxLength = SESSION_TIMELINE_SUMMARY_MAX_LENGTH
) => {
  if (typeof value !== "string") return "";
  let text = normalizeWhitespace(value);
  for (const pattern of SENSITIVE_PATTERNS) {
    text = text.replace(pattern, "[已隐藏]");
  }
  if (text.length > maxLength) {
    text = `${text.slice(0, Math.max(0, maxLength - 1))}…`;
  }
  return text;
};

const createTimelineItem = (
  timestamp: string,
  type: SessionTimelineType,
  source: SessionTimelineSource,
  summary: string
): SessionTimelineItem | null => {
  const safeSummary = sanitizeSessionTimelineText(summary);
  if (!safeSummary) return null;
  return {
    id: `${timestamp}-${type}-${safeSummary}`,
    timestamp,
    type,
    source,
    summary: safeSummary
  };
};

const topicIsKnowledgeUsed = (topic: string) =>
  topic.includes("已使用本地知识") || topic.includes("使用本地知识");

const topicIsNotUsedReason = (topic: string) =>
  topic.includes("相关性不足") ||
  topic.includes("未命中") ||
  topic.includes("不是游戏知识") ||
  topic.includes("没有可用知识包");

export const sessionTimelineItemsFromEvent = (event: ReiLinkEvent): SessionTimelineItem[] => {
  const timestamp = event.timestamp;
  switch (event.type) {
    case "game_context_changed": {
      const game = sanitizeSessionTimelineText(event.game, 48);
      if (!game || game === "无") return [];
      const item = createTimelineItem(timestamp, "game_selected", "game_context", `切换游戏：${game}`);
      return item ? [item] : [];
    }
    case "game_session_changed": {
      const items: Array<SessionTimelineItem | null> = [];
      const currentBoss = sanitizeSessionTimelineText(event.current_boss, 48);
      const clearedBoss = sanitizeSessionTimelineText(event.last_cleared_boss, 48);
      if (currentBoss && currentBoss !== "无") {
        items.push(createTimelineItem(timestamp, "boss_detected", "game_session", `检测到 Boss：${currentBoss}`));
      }
      if (typeof event.death_count === "number" && Number.isFinite(event.death_count) && event.death_count > 0) {
        items.push(createTimelineItem(timestamp, "death_count_changed", "game_session", `死亡次数更新：${event.death_count}`));
      }
      if (typeof event.frustration_count === "number" && Number.isFinite(event.frustration_count) && event.frustration_count > 0) {
        items.push(createTimelineItem(timestamp, "frustration_changed", "game_session", `挫败状态升高：${event.frustration_count}`));
      }
      if (clearedBoss && clearedBoss !== "无") {
        items.push(createTimelineItem(timestamp, "boss_cleared", "game_session", `击败 Boss：${clearedBoss}`));
      } else if (event.activity === "boss_cleared" && currentBoss) {
        items.push(createTimelineItem(timestamp, "boss_cleared", "game_session", `击败 Boss：${currentBoss}`));
      }
      return items.filter((item): item is SessionTimelineItem => Boolean(item));
    }
    case "knowledge_used": {
      const topics = (event.topics ?? []).map((topic) => sanitizeSessionTimelineText(topic, 48)).filter(Boolean);
      const knowledgeWasUsed = topics.some(topicIsKnowledgeUsed) || (topics.length > 0 && !topics.every(topicIsNotUsedReason));
      if (!knowledgeWasUsed) return [];
      const game = sanitizeSessionTimelineText(event.game, 36);
      const topic = topics.find((value) => !topicIsKnowledgeUsed(value)) ?? "";
      const suffix = [game, topic].filter(Boolean).join(" / ");
      const item = createTimelineItem(timestamp, "knowledge_used", "knowledge", suffix ? `使用知识：${suffix}` : "使用知识");
      return item ? [item] : [];
    }
    case "proactive_message_shown": {
      const trigger = triggerLabels[event.trigger_type] ?? sanitizeSessionTimelineText(event.trigger_type, 32);
      const item = createTimelineItem(timestamp, "proactive_shown", "proactive", trigger ? `主动陪伴已显示：${trigger}` : "主动陪伴已显示");
      return item ? [item] : [];
    }
    case "pending_memory_accepted": {
      const item = createTimelineItem(timestamp, "memory_accepted", "memory", "记忆已接受");
      return item ? [item] : [];
    }
    case "pending_memory_ignored": {
      const item = createTimelineItem(timestamp, "memory_ignored", "memory", "记忆已忽略");
      return item ? [item] : [];
    }
    default:
      return [];
  }
};

export const appendSessionTimelineItems = (
  current: SessionTimelineItem[],
  incoming: SessionTimelineItem[],
  limit = SESSION_TIMELINE_LIMIT
) => {
  if (incoming.length === 0) return current;
  return [...current, ...incoming].slice(-limit);
};
