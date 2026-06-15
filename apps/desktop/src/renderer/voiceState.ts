export type VoiceConversationState =
  | "idle"
  | "listening"
  | "transcribing"
  | "ready_to_send"
  | "assistant_thinking"
  | "speaking"
  | "interrupted"
  | "error";

export type VoiceConversationSnapshot = {
  state: VoiceConversationState;
  label: string;
  description: string;
  tone: "neutral" | "active" | "ready" | "warning" | "error";
};

export type VoiceStateSignals = {
  listening?: boolean;
  transcribing?: boolean;
  readyToSend?: boolean;
  assistantThinking?: boolean;
  speaking?: boolean;
  interrupted?: boolean;
  errorMessage?: string | null;
};

const VOICE_STATE_META: Record<VoiceConversationState, Omit<VoiceConversationSnapshot, "state">> = {
  idle: {
    label: "语音待机",
    description: "默认确认后发送。",
    tone: "neutral"
  },
  listening: {
    label: "正在听",
    description: "录音结束后才会转写。",
    tone: "active"
  },
  transcribing: {
    label: "正在识别",
    description: "本地转写中，不会自动发送。",
    tone: "active"
  },
  ready_to_send: {
    label: "已识别，等待发送",
    description: "文本已在输入框，请确认后发送。",
    tone: "ready"
  },
  assistant_thinking: {
    label: "Rei 正在回应",
    description: "已确认发送，正在等待回复。",
    tone: "active"
  },
  speaking: {
    label: "Rei 正在说话",
    description: "可以随时停止播放。",
    tone: "active"
  },
  interrupted: {
    label: "已停止播放",
    description: "语音播放已停止。",
    tone: "warning"
  },
  error: {
    label: "语音出错",
    description: "语音没有接上。可以再试一次。",
    tone: "error"
  }
};

export const voiceConversationSnapshot = (
  state: VoiceConversationState,
  descriptionOverride?: string | null
): VoiceConversationSnapshot => {
  const meta = VOICE_STATE_META[state];
  return {
    state,
    label: meta.label,
    description: descriptionOverride || meta.description,
    tone: meta.tone
  };
};

export const resolveVoiceConversationState = (signals: VoiceStateSignals): VoiceConversationSnapshot => {
  if (signals.transcribing) return voiceConversationSnapshot("transcribing");
  if (signals.assistantThinking) return voiceConversationSnapshot("assistant_thinking");
  if (signals.speaking) return voiceConversationSnapshot("speaking");
  if (signals.readyToSend) return voiceConversationSnapshot("ready_to_send");
  if (signals.listening) return voiceConversationSnapshot("listening");
  if (signals.interrupted) return voiceConversationSnapshot("interrupted");
  if (signals.errorMessage) return voiceConversationSnapshot("error", signals.errorMessage);
  return voiceConversationSnapshot("idle");
};
