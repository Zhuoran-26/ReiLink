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
  autoSendBlockReason: VoiceAutoSendBlockReason | null;
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
  if (/…+$/.test(text)) return true;
  const withoutTerminalPunctuation = text.replace(/[。！？!?]+$/u, "");
  if (/(?:准备|準備|打算)去$/u.test(withoutTerminalPunctuation)) return true;
  if (/(?:等一下|等下|待会|待會|之后|之後|然后|然後|准备|準備|打算).{0,8}想去$/u.test(withoutTerminalPunctuation)) {
    return true;
  }
  if (withoutTerminalPunctuation.length !== text.length) return false;
  if (text.length <= 8 && partialEndMarkers.some((marker) => text.endsWith(marker))) return true;
  return text.length <= 9 && /^(?:我(?:现在|現在|想|要|准备|準備|打算|先)|这次|這次)/u.test(text);
};

const enclosedCaptionPattern = /^(?:(?:\([^()]*\)|（[^（）]*）|\[[^[\]]*\]|【[^【】]*】)\s*)+$/u;
const captionOrSpeakerLabelPattern = /^(?:(?:字幕|旁白|说话人|說話人|speaker|caption)\s*[:：]\s*[\p{L}\p{N}][\p{L}\p{N}\s._'-]{0,31}|[\p{L}\p{N}][\p{L}\p{N}\s._'-]{0,31}\s*[:：])$/iu;

const looksLikeNonSpeechCaption = (text: string) =>
  enclosedCaptionPattern.test(text) || captionOrSpeakerLabelPattern.test(text);

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
  const normalized = text.normalize("NFKC").replace(/\s+/g, " ").trim();
  const compact = normalized.replace(/\s+/g, "");
  const lexicalCharacterCount = compact.match(/[\p{L}\p{N}]/gu)?.length ?? 0;
  let quality: VoiceTranscriptQuality;
  let autoSendBlockReason: VoiceAutoSendBlockReason | null;

  if (captureStopReason === "max_duration") {
    quality = "suspected_partial";
    autoSendBlockReason = "max_duration";
  } else if (captureStopReason === "cancelled" || captureStopReason === "error") {
    quality = "suspicious";
    autoSendBlockReason = "capture_stop_not_allowed";
  } else if (typeof durationMs === "number" && Number.isFinite(durationMs) && durationMs >= 0 && durationMs < VOICE_DIRECT_MIN_AUTO_SEND_DURATION_MS) {
    quality = "short_recording";
    autoSendBlockReason = "recording_too_short";
  } else if (!compact) {
    quality = "empty";
    autoSendBlockReason = "empty_transcript";
  } else if (lexicalCharacterCount === 0) {
    quality = "too_short";
    autoSendBlockReason = "transcript_too_short";
  } else if (looksLikeNonSpeechCaption(normalized)) {
    quality = "non_speech_caption";
    autoSendBlockReason = "non_speech_caption";
  } else if (lexicalCharacterCount < VOICE_DIRECT_MIN_AUTO_SEND_CHARS) {
    quality = "too_short";
    autoSendBlockReason = "transcript_too_short";
  } else if (looksPartial(compact)) {
    quality = "suspected_partial";
    autoSendBlockReason = "suspected_partial";
  } else if (looksSuspicious(compact)) {
    quality = "suspicious";
    autoSendBlockReason = "suspicious_transcript";
  } else {
    quality = "acceptable";
    autoSendBlockReason = null;
  }

  const sendDecision: VoiceSendDecision =
    quality === "empty"
      ? "blocked"
      : interactionMode === "confirm_send"
        ? "editable_draft"
        : quality === "acceptable"
          ? "auto_send_allowed"
          : "blocked";

  return { characterCount: text.length, quality, sendDecision, autoSendBlockReason };
};
