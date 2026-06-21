import type { AppSettings } from "../shared/api";

export type VoiceReplySpeakSource = "assistant_reply" | "direct_conversation" | "proactive" | "memory_prompt" | "debug";
export type VoiceSpokenReplyMode = AppSettings["voice_spoken_reply_mode"];
export type VoiceSpeakSkippedReason =
  | "silent_mode"
  | "proactive_disabled"
  | "memory_prompt_disabled"
  | "debug_content"
  | "unsafe_content"
  | "structured_content"
  | "empty_spoken_text";

export type VoiceSpeakDecision = {
  shouldSpeak: boolean;
  spokenText: string;
  spokenMode: VoiceSpokenReplyMode;
  source: VoiceReplySpeakSource;
  profileId: AppSettings["voice_profile_id"];
  skippedReason?: VoiceSpeakSkippedReason;
  originalCharacterCount: number;
  spokenCharacterCount: number;
  sentenceCount: number;
  excerptCreated: boolean;
  maxSpokenChars: number;
  maxSpokenSentences: number;
};

export const VOICE_PROFILE_ID = "rei_calm";
export const VOICE_PROFILE_LABEL = "Rei Calm / Rei 冷静陪伴";
export const VOICE_PROFILE_DESCRIPTION = "控制说什么、说多长、什么时候不说；当前仍使用系统 speechSynthesis。";
export const VOICE_DEBUG_SPEAKING_ALLOWED = false;
export const VOICE_INTERRUPT_ON_NEW_RECORDING = true;
export const VOICE_TEST_VOICE_ALLOWED = true;

export const VOICE_SPOKEN_MODE_LABELS: Record<VoiceSpokenReplyMode, string> = {
  full: "全文播报",
  brief: "短版播报",
  silent: "静默"
};

const DEFAULT_MAX_SPOKEN_CHARS = 120;
const DEFAULT_MAX_SPOKEN_SENTENCES = 2;

const unsafeContentPattern =
  /(api[_ -]?key|authorization|bearer\s+[a-z0-9._-]+|\.env|raw prompt|prompt preview|semantic shadow|semantic trace|knowledge trace|persona pack summary|stdout|stderr|debug panel)/i;
const memoryInternalPattern = /(memory internal|memory prompt|pending memory evidence|confirmed memory raw|记忆内部|待确认记忆证据)/i;
const localPathPattern = /(\/Users\/|\/private\/|\/var\/folders\/|[A-Za-z]:\\)/;
const codeFencePattern = /```[\s\S]*?```/g;
const inlineCodePattern = /`[^`]*`/g;
const sentencePattern = /[^。？！!?…\n]+[。？！!?…]*/g;

const clampNumber = (value: number, min: number, max: number, fallback: number) => {
  if (typeof value !== "number" || Number.isNaN(value)) return fallback;
  return Math.min(max, Math.max(min, Math.round(value)));
};

export const voiceSpokenModeText = (mode: VoiceSpokenReplyMode) => VOICE_SPOKEN_MODE_LABELS[mode] ?? VOICE_SPOKEN_MODE_LABELS.brief;

export const voiceSpeakSkippedReasonText = (reason?: VoiceSpeakSkippedReason) => {
  const labels: Record<VoiceSpeakSkippedReason, string> = {
    silent_mode: "静默模式",
    proactive_disabled: "主动陪伴默认不播报",
    memory_prompt_disabled: "记忆确认默认不播报",
    debug_content: "调试内容不播报",
    unsafe_content: "内容包含敏感或内部信息",
    structured_content: "结构化内容不适合播报",
    empty_spoken_text: "没有可播报文本"
  };
  return reason ? labels[reason] : "未播报";
};

export const countNaturalSentences = (text: string) => splitNaturalSentences(text).length;

export function buildSpokenAssistantReply(
  text: string,
  settings: AppSettings,
  source: VoiceReplySpeakSource
): VoiceSpeakDecision {
  const originalText = text.trim();
  const originalCharacterCount = originalText.length;
  const profileId = settings.voice_profile_id;
  const maxSpokenChars = clampNumber(settings.voice_max_spoken_chars, 40, 280, DEFAULT_MAX_SPOKEN_CHARS);
  const maxSpokenSentences = clampNumber(settings.voice_max_spoken_sentences, 1, 4, DEFAULT_MAX_SPOKEN_SENTENCES);
  const spokenMode = modeForSource(settings, source);

  const baseDecision = {
    spokenMode,
    source,
    profileId,
    originalCharacterCount,
    maxSpokenChars,
    maxSpokenSentences
  };

  const skippedReason = skippedReasonForContent(originalText, source, settings);
  if (skippedReason) {
    return {
      ...baseDecision,
      shouldSpeak: false,
      spokenText: "",
      skippedReason,
      spokenCharacterCount: 0,
      sentenceCount: 0,
      excerptCreated: false
    };
  }

  if (spokenMode === "silent") {
    return {
      ...baseDecision,
      shouldSpeak: false,
      spokenText: "",
      skippedReason: "silent_mode",
      spokenCharacterCount: 0,
      sentenceCount: 0,
      excerptCreated: false
    };
  }

  const sanitizedText = sanitizeSpokenText(originalText);
  if (!sanitizedText) {
    return {
      ...baseDecision,
      shouldSpeak: false,
      spokenText: "",
      skippedReason: "empty_spoken_text",
      spokenCharacterCount: 0,
      sentenceCount: 0,
      excerptCreated: false
    };
  }

  if (spokenMode === "full") {
    const sentenceCount = countNaturalSentences(sanitizedText);
    return {
      ...baseDecision,
      shouldSpeak: true,
      spokenText: sanitizedText,
      spokenCharacterCount: sanitizedText.length,
      sentenceCount,
      excerptCreated: sanitizedText !== originalText
    };
  }

  const sentences = splitNaturalSentences(sanitizedText);
  const selectedSentences = sentences.length > 0 ? sentences.slice(0, maxSpokenSentences) : [sanitizedText];
  const selectedText = selectedSentences.join("").trim();
  const truncatedText = truncateSpokenText(selectedText, maxSpokenChars);
  const excerptCreated = sanitizedText !== truncatedText || selectedSentences.length < sentences.length;
  return {
    ...baseDecision,
    shouldSpeak: truncatedText.length > 0,
    spokenText: truncatedText,
    skippedReason: truncatedText.length > 0 ? undefined : "empty_spoken_text",
    spokenCharacterCount: truncatedText.length,
    sentenceCount: Math.min(selectedSentences.length, countNaturalSentences(truncatedText) || selectedSentences.length),
    excerptCreated
  };
}

function modeForSource(settings: AppSettings, source: VoiceReplySpeakSource): VoiceSpokenReplyMode {
  if (source === "direct_conversation") return settings.voice_direct_spoken_reply_mode;
  return settings.voice_spoken_reply_mode;
}

function skippedReasonForContent(
  text: string,
  source: VoiceReplySpeakSource,
  settings: AppSettings
): VoiceSpeakSkippedReason | null {
  if (!text.trim()) return "empty_spoken_text";
  if (source === "debug") return "debug_content";
  if (source === "proactive" && !settings.voice_speak_proactive) return "proactive_disabled";
  if (source === "memory_prompt" && !settings.voice_speak_memory_prompts) return "memory_prompt_disabled";
  if (unsafeContentPattern.test(text) || memoryInternalPattern.test(text) || localPathPattern.test(text)) return "unsafe_content";
  if (looksLikeStructuredContent(text)) return "structured_content";
  return null;
}

function looksLikeStructuredContent(text: string) {
  const trimmed = text.trim();
  if (!trimmed) return false;
  if (/^(\{[\s\S]*\}|\[[\s\S]*\])$/.test(trimmed)) {
    try {
      JSON.parse(trimmed);
      return true;
    } catch {
      return false;
    }
  }
  if (/^(trace|debug|event stream|prompt preview)\s*[:：]/i.test(trimmed)) return true;
  return false;
}

function sanitizeSpokenText(text: string) {
  return text
    .replace(codeFencePattern, " ")
    .replace(/\[[^\]]+\]\([^)]+\)/g, (match) => match.replace(/^\[([^\]]+)\]\([^)]+\)$/, "$1"))
    .replace(inlineCodePattern, " ")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s{0,3}>\s?/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/^\s*\d+[.)、]\s+/gm, "")
    .replace(/^\s*\|.*\|\s*$/gm, " ")
    .replace(/\r/g, "\n")
    .replace(/^[ \t]+$/gm, "")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{2,}/g, "\n")
    .trim();
}

function splitNaturalSentences(text: string) {
  const matches = text
    .split(/\n+/)
    .flatMap((line) => line.match(sentencePattern) ?? [])
    .map((sentence) => sentence.trim())
    .filter(Boolean);
  return matches.length > 0 ? matches : text.trim() ? [text.trim()] : [];
}

function truncateSpokenText(text: string, maxChars: number) {
  if (text.length <= maxChars) return text;
  const sliceLength = Math.max(1, maxChars - 1);
  return `${text.slice(0, sliceLength).replace(/[，、；：,;:\s]+$/u, "")}…`;
}
