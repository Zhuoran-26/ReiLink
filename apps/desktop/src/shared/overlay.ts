export const OVERLAY_PLACEHOLDER_TEXT = "Rei 正安静待机。";
export const OVERLAY_MAX_MESSAGES = 3;
export const OVERLAY_MAX_MESSAGE_LENGTH = 96;

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
  /raw\s*(prompt|json|stdout|stderr)/gi,
  /transcript/gi,
  /\/users\/[^\s，。；,;]+/gi,
  /[a-z]:\\[^\s，。；,;]+/gi
];

const normalizeWhitespace = (value: string) => value.replace(/\s+/g, " ").trim();

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

export const createOverlayMessage = (
  update: OverlayContentUpdate,
  id: string,
  maxLength = OVERLAY_MAX_MESSAGE_LENGTH
): OverlayMessage => ({
  id,
  speaker: "Rei",
  text: sanitizeOverlayText(update.text, maxLength),
  source: update.source === "proactive" ? "proactive" : update.source === "placeholder" ? "placeholder" : "assistant_reply",
  timestamp: update.timestamp || new Date().toISOString()
});

export const createOverlayState = (
  enabled: boolean,
  visible: boolean,
  messages: OverlayMessage[],
  updatedAt: string | null = null
): OverlayState => ({
  enabled,
  visible,
  messages: messages.slice(-OVERLAY_MAX_MESSAGES),
  max_messages: OVERLAY_MAX_MESSAGES,
  max_message_length: OVERLAY_MAX_MESSAGE_LENGTH,
  updated_at: updatedAt
});
