import type { AppSettings } from "../../../shared/api";

type VoiceInteractionMode = AppSettings["voice_interaction_mode"];

type VoiceModeCardProps = {
  busy: boolean;
  mode: VoiceInteractionMode;
  onChange: (mode: VoiceInteractionMode) => void;
};

export function VoiceModeCard({ busy, mode, onChange }: VoiceModeCardProps) {
  return (
    <div className="voiceModeCard" role="group" aria-label="直接对话模式">
      <button
        aria-pressed={mode === "confirm_send"}
        className="voiceModeChoice"
        disabled={busy}
        type="button"
        onClick={() => onChange("confirm_send")}
      >
        <span aria-hidden="true" className="voiceModeMark" />
        <span>确认后发送</span>
      </button>
      <button
        aria-pressed={mode === "direct_conversation"}
        className="voiceModeChoice"
        disabled={busy}
        type="button"
        onClick={() => onChange("direct_conversation")}
      >
        <span aria-hidden="true" className="voiceModeMark" />
        <span>自动发送（安全模式）</span>
      </button>
      <p>
        {mode === "direct_conversation"
          ? "合适的转写会自动发送；不清楚时仍会停在草稿。"
          : "转写先留在草稿里，由你确认。"}
      </p>
    </div>
  );
}
