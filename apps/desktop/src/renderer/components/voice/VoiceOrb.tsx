import { ReiAvatar, type ReiPresenceState } from "../rei/ReiAvatar";
import type { VoiceConversationState } from "../../voiceState";

type VoiceOrbProps = {
  state: VoiceConversationState;
};

const presenceState = (state: VoiceConversationState): ReiPresenceState => {
  if (state === "listening") return "listening";
  if (state === "speaking") return "speaking";
  if (state === "transcribing" || state === "auto_sending" || state === "assistant_thinking") return "thinking";
  return "idle";
};

export function VoiceOrb({ state }: VoiceOrbProps) {
  return (
    <div aria-hidden="true" className={`voiceOrb voiceOrb-${state}`}>
      <span className="voiceOrbRing voiceOrbRing-outer" />
      <span className="voiceOrbRing voiceOrbRing-middle" />
      <span className="voiceOrbRing voiceOrbRing-inner" />
      <span className="voiceOrbGoldLine" />
      <ReiAvatar name="Rei" size="large" state={presenceState(state)} />
    </div>
  );
}
