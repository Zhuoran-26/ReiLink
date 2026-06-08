export const OVERLAY_PLACEHOLDER_TEXT = "Rei 正安静待机。";
export const OVERLAY_MAX_MESSAGES = 3;
export const OVERLAY_MIN_MESSAGES = 1;
export const OVERLAY_DEFAULT_MESSAGE_COUNT = 2;
export const OVERLAY_MAX_MESSAGE_LENGTH = 96;
export const OVERLAY_MIN_OPACITY = 0.35;
export const OVERLAY_MAX_OPACITY = 0.95;
export const OVERLAY_DEFAULT_OPACITY = 0.72;
export const OVERLAY_DEFAULT_POSITION = "middle-right";
export const OVERLAY_POSITION_VALUES = [
  "top-right",
  "middle-right",
  "bottom-right",
  "top-left",
  "middle-left",
  "bottom-left"
] as const;

export type OverlayPosition = (typeof OVERLAY_POSITION_VALUES)[number];

export type OverlayConfig = {
  position: OverlayPosition;
  opacity: number;
  max_messages: number;
};

export type OverlayConfigUpdate = Partial<OverlayConfig>;

export type OverlayMessageSource = "assistant_reply" | "proactive" | "placeholder";

export type OverlayMessage = {
  id: string;
  speaker: "Rei";
  text: string;
  source: OverlayMessageSource;
  timestamp: string;
};

export type OverlayState = {
  enabled: boolean;
  visible: boolean;
  position: OverlayPosition;
  opacity: number;
  messages: OverlayMessage[];
  max_messages: number;
  max_message_length: number;
  updated_at: string | null;
};

export type OverlayContentUpdate = {
  text: string;
  source?: OverlayMessageSource;
  timestamp?: string;
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

const normalizeWhitespace = (value: string) => value.replace(/\s+/g, " ").trim();

export const isOverlayPosition = (value: unknown): value is OverlayPosition =>
  typeof value === "string" && (OVERLAY_POSITION_VALUES as readonly string[]).includes(value);

export const normalizeOverlayPosition = (value: unknown): OverlayPosition =>
  isOverlayPosition(value) ? value : OVERLAY_DEFAULT_POSITION;

export const normalizeOverlayOpacity = (value: unknown) => {
  const numeric = typeof value === "number" ? value : typeof value === "string" ? Number(value) : OVERLAY_DEFAULT_OPACITY;
  if (!Number.isFinite(numeric)) return OVERLAY_DEFAULT_OPACITY;
  const clamped = Math.min(OVERLAY_MAX_OPACITY, Math.max(OVERLAY_MIN_OPACITY, numeric));
  return Math.round(clamped * 100) / 100;
};

export const normalizeOverlayMessageCount = (value: unknown) => {
  const numeric = typeof value === "number" ? value : typeof value === "string" ? Number(value) : OVERLAY_DEFAULT_MESSAGE_COUNT;
  if (!Number.isFinite(numeric)) return OVERLAY_DEFAULT_MESSAGE_COUNT;
  return Math.min(OVERLAY_MAX_MESSAGES, Math.max(OVERLAY_MIN_MESSAGES, Math.round(numeric)));
};

export const normalizeOverlayConfig = (config: unknown = {}): OverlayConfig => {
  const record = typeof config === "object" && config !== null ? config as Record<string, unknown> : {};
  return {
    position: normalizeOverlayPosition(record.position),
    opacity: normalizeOverlayOpacity(record.opacity),
    max_messages: normalizeOverlayMessageCount(record.max_messages)
  };
};

export const truncateOverlayText = (value: string, maxLength = OVERLAY_MAX_MESSAGE_LENGTH) => {
  const normalized = normalizeWhitespace(value);
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, Math.max(0, maxLength - 1))}…`;
};

export const sanitizeOverlayText = (value: unknown, maxLength = OVERLAY_MAX_MESSAGE_LENGTH) => {
  if (typeof value !== "string") return OVERLAY_PLACEHOLDER_TEXT;
  let text = normalizeWhitespace(value);
  for (const pattern of SENSITIVE_PATTERNS) {
    text = text.replace(pattern, "[已隐藏]");
  }
  text = truncateOverlayText(text, maxLength);
  return text || OVERLAY_PLACEHOLDER_TEXT;
};

export const normalizeOverlayContentUpdate = (
  update: unknown,
  maxLength = OVERLAY_MAX_MESSAGE_LENGTH
): OverlayContentUpdate => {
  const record = typeof update === "object" && update !== null ? update as Record<string, unknown> : {};
  const source = record.source === "proactive" || record.source === "placeholder" ? record.source : "assistant_reply";
  const timestamp = typeof record.timestamp === "string" && record.timestamp.length <= 64 ? record.timestamp : undefined;
  return {
    text: sanitizeOverlayText(record.text, maxLength),
    source,
    timestamp
  };
};

export const createOverlayMessage = (
  update: OverlayContentUpdate,
  id: string,
  maxLength = OVERLAY_MAX_MESSAGE_LENGTH
): OverlayMessage => {
  const safeUpdate = normalizeOverlayContentUpdate(update, maxLength);
  return {
    id,
    speaker: "Rei",
    text: safeUpdate.text,
    source: safeUpdate.source ?? "assistant_reply",
    timestamp: safeUpdate.timestamp || new Date().toISOString()
  };
};

export const createOverlayState = (
  enabled: boolean,
  visible: boolean,
  messages: OverlayMessage[],
  updatedAt: string | null = null,
  config: OverlayConfigUpdate = {}
): OverlayState => {
  const safeConfig = normalizeOverlayConfig(config);
  return {
    enabled,
    visible,
    position: safeConfig.position,
    opacity: safeConfig.opacity,
    messages: messages.slice(-safeConfig.max_messages),
    max_messages: safeConfig.max_messages,
    max_message_length: OVERLAY_MAX_MESSAGE_LENGTH,
    updated_at: updatedAt
  };
};
