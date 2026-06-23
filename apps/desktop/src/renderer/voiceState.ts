export type VoiceConversationState =
  | "idle"
  | "listening"
  | "transcribing"
  | "auto_sending"
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
  autoSending?: boolean;
  readyToSend?: boolean;
  assistantThinking?: boolean;
  speaking?: boolean;
  interrupted?: boolean;
  errorMessage?: string | null;
};

const VOICE_STATE_META: Record<VoiceConversationState, Omit<VoiceConversationSnapshot, "state">> = {
  idle: {
    label: "语音待机",
    description: "默认确认后发送，开启直接对话后才会自动发送。",
    tone: "neutral"
  },
  listening: {
    label: "正在录音",
    description: "说完后停止录音，随后本地转写。",
    tone: "active"
  },
  transcribing: {
    label: "正在识别",
    description: "正在本地转写，音频不会上传。",
    tone: "active"
  },
  auto_sending: {
    label: "已转写，正在发送给 Rei",
    description: "直接对话已开启，这句会自动进入聊天。",
    tone: "active"
  },
  ready_to_send: {
    label: "已识别，等待发送",
    description: "文本已在输入框，请确认后发送。",
    tone: "ready"
  },
  assistant_thinking: {
    label: "Rei 正在回应",
    description: "已发送，正在等待回复。",
    tone: "active"
  },
  speaking: {
    label: "正在播报",
    description: "可以点击停止语音打断播报。",
    tone: "active"
  },
  interrupted: {
    label: "已停止播放",
    description: "播报已停止。",
    tone: "warning"
  },
  error: {
    label: "语音暂时不可用",
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
  if (signals.errorMessage) return voiceConversationSnapshot("error", signals.errorMessage);
  if (signals.speaking) return voiceConversationSnapshot("speaking");
  if (signals.autoSending) return voiceConversationSnapshot("auto_sending");
  if (signals.assistantThinking) return voiceConversationSnapshot("assistant_thinking");
  if (signals.readyToSend) return voiceConversationSnapshot("ready_to_send");
  if (signals.listening) return voiceConversationSnapshot("listening");
  if (signals.interrupted) return voiceConversationSnapshot("interrupted");
  return voiceConversationSnapshot("idle");
};
