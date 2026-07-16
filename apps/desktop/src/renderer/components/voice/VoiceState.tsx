import type { VoiceConversationSnapshot, VoiceConversationState } from "../../voiceState";
import { VoiceOrb } from "./VoiceOrb";

type VoiceStateCopy = {
  description: string;
  title: string;
};

const VOICE_EXPERIENCE_COPY: Record<VoiceConversationState, VoiceStateCopy> = {
  idle: {
    title: "Rei 等待着",
    description: "想说的时候，就从这里开始。"
  },
  listening: {
    title: "Rei 正在听...",
    description: "说完后停下来，声音会先留成草稿。"
  },
  transcribing: {
    title: "声音正在留下来...",
    description: "稍等一下。"
  },
  auto_sending: {
    title: "这句话正在送给 Rei...",
    description: "安全模式会把合适的转写直接送进对话。"
  },
  ready_to_send: {
    title: "声音已经留下来。",
    description: "先看一眼，再决定要不要发送。"
  },
  assistant_thinking: {
    title: "Rei 想了一下...",
    description: "这句话已经送出去了。"
  },
  speaking: {
    title: "Rei 正在回应...",
    description: "需要时，可以随时停下来。"
  },
  interrupted: {
    title: "声音停下来了。",
    description: "想继续的时候，再开口就好。"
  },
  error: {
    title: "这次没有听清。",
    description: "可以再试一次。"
  }
};

export const voiceExperienceCopy = (snapshot: VoiceConversationSnapshot): VoiceStateCopy => {
  const copy = VOICE_EXPERIENCE_COPY[snapshot.state];
  return snapshot.state === "error" && snapshot.description
    ? { ...copy, description: snapshot.description }
    : copy;
};

type VoiceStateProps = {
  snapshot: VoiceConversationSnapshot;
};

export function VoiceState({ snapshot }: VoiceStateProps) {
  const copy = voiceExperienceCopy(snapshot);

  return (
    <div
      aria-label="Voice v2.2 状态"
      className={`voicePresence voicePresence-${snapshot.state}`}
      data-voice-state={snapshot.state}
      role="status"
    >
      <VoiceOrb state={snapshot.state} />
      <div className="voicePresenceCopy">
        <h2>{copy.title}</h2>
        <p>{copy.description}</p>
      </div>
    </div>
  );
}
