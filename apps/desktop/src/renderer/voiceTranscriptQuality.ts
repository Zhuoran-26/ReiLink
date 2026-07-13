import type {
  VoiceAutoSendBlockReason,
  VoiceCaptureStopReason,
  VoiceInteractionModeEvent,
  VoiceSendDecision,
  VoiceTranscriptQuality
} from "../shared/events";

export type VoiceTranscriptAssessment = {
  characterCount: number;
  quality: VoiceTranscriptQuality;
  sendDecision: VoiceSendDecision;
};

type VoiceTranscriptAssessmentInput = {
  transcript: string;
  interactionMode: VoiceInteractionModeEvent;
  durationMs?: number;
  captureStopReason?: VoiceCaptureStopReason;
};

export const VOICE_DIRECT_MIN_AUTO_SEND_DURATION_MS = 800;
export const VOICE_DIRECT_MIN_AUTO_SEND_CHARS = 4;

const partialEndMarkers = [
  "我想",
  "我现在",
  "我現在",
  "我换",
  "我換",
  "我换去",
  "我換去",
  "不打",
  "先不打",
  "去打",
  "换到",
  "換到",
  "那个",
  "那個",
  "这个",
  "這個",
  "帮我",
  "幫我",
  "然后",
  "然後",
  "但是",
  "因为",
  "因為"
];

const looksPartial = (text: string) => {
  if (/[。！？!?…]$/.test(text)) return false;
  if (text.length <= 8 && partialEndMarkers.some((marker) => text.endsWith(marker))) return true;
  return text.length <= 9 && /^(?:我(?:现在|現在|想|要|准备|準備|打算|先)|这次|這次)/.test(text);
};

const looksSuspicious = (text: string) =>
  /�|<unk>|\[(?:blank_audio|inaudible|noise)\]/i.test(text) ||
  /(.)\1{3,}/u.test(text) ||
  /^(?:(?:嗯|啊|呃|额|欸)[，。！？、\s]*){4,}$/u.test(text);

export const assessVoiceTranscript = ({
  transcript,
  interactionMode,
  durationMs,
  captureStopReason
}: VoiceTranscriptAssessmentInput): VoiceTranscriptAssessment => {
  const text = transcript.trim();
  const compact = text.replace(/\s+/g, "");
  let quality: VoiceTranscriptQuality;

  if (!compact) {
    quality = "empty";
  } else if (typeof durationMs === "number" && durationMs > 0 && durationMs < VOICE_DIRECT_MIN_AUTO_SEND_DURATION_MS) {
    quality = "short_recording";
  } else if (compact.length < VOICE_DIRECT_MIN_AUTO_SEND_CHARS) {
    quality = "too_short";
  } else if (captureStopReason === "max_duration" || looksPartial(compact)) {
    quality = "suspected_partial";
  } else if (looksSuspicious(compact)) {
    quality = "suspicious";
  } else {
    quality = "acceptable";
  }

  const sendDecision: VoiceSendDecision =
    quality === "empty"
      ? "blocked"
      : interactionMode === "confirm_send"
        ? "editable_draft"
        : quality === "acceptable"
          ? "auto_send_allowed"
          : "blocked";

  return { characterCount: text.length, quality, sendDecision };
};

export const autoSendBlockReasonForQuality = (quality: VoiceTranscriptQuality): VoiceAutoSendBlockReason | null => {
  if (quality === "acceptable") return null;
  if (quality === "short_recording") return "short_recording";
  if (quality === "suspected_partial") return "partial_transcript";
  if (quality === "suspicious") return "suspicious_transcript";
  return "short_transcript";
};
