import type { ChangeEventHandler, FormEventHandler } from "react";
import { Mic, Square, VolumeX } from "lucide-react";

import type { AppSettings } from "../../../shared/api";
import type { VoiceConversationSnapshot } from "../../voiceState";
import { Button } from "../ui/Button";
import { TranscriptDraft } from "./TranscriptDraft";
import { VoiceModeCard } from "./VoiceModeCard";
import { VoiceState } from "./VoiceState";

type VoiceConversationProps = {
  draftHint: string;
  draftReady: boolean;
  draftValue: string;
  mode: AppSettings["voice_interaction_mode"];
  modeBusy: boolean;
  onDraftChange: ChangeEventHandler<HTMLTextAreaElement>;
  onModeChange: (mode: AppSettings["voice_interaction_mode"]) => void;
  onRecord: () => void;
  onRestart: () => void;
  onStopSpeaking: () => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
  recordActive: boolean;
  recordDisabled: boolean;
  recordLabel: string;
  recordTitle: string;
  sending: boolean;
  speaking: boolean;
  state: VoiceConversationSnapshot;
};

const recordButtonText = (state: VoiceConversationSnapshot, active: boolean) => {
  if (state.state === "listening") return "停止录音";
  if (state.state === "transcribing" || state.state === "auto_sending") return "请稍等";
  if (active) return "停止录音";
  return "开始说话";
};

export function VoiceConversation({
  draftHint,
  draftReady,
  draftValue,
  mode,
  modeBusy,
  onDraftChange,
  onModeChange,
  onRecord,
  onRestart,
  onStopSpeaking,
  onSubmit,
  recordActive,
  recordDisabled,
  recordLabel,
  recordTitle,
  sending,
  speaking,
  state
}: VoiceConversationProps) {
  const recordText = recordButtonText(state, recordActive);

  return (
    <section aria-label="语音对话" className="voiceConversation">
      <VoiceModeCard busy={modeBusy} mode={mode} onChange={onModeChange} />

      <div className="voiceListeningSpace">
        <VoiceState snapshot={state} />
        <div className="voicePrimaryActions">
          <Button
            aria-label={recordLabel}
            className="voiceRecordButton"
            disabled={recordDisabled}
            title={recordTitle}
            variant={state.state === "listening" ? "secondary" : "quiet"}
            onClick={onRecord}
          >
            {state.state === "listening" || recordActive ? (
              <Square aria-hidden="true" fill="currentColor" size={12} strokeWidth={1.5} />
            ) : (
              <Mic aria-hidden="true" size={16} strokeWidth={1.7} />
            )}
            {recordText}
          </Button>
          {speaking ? (
            <Button aria-label="停止语音 / Stop Voice" variant="quiet" onClick={onStopSpeaking}>
              <VolumeX aria-hidden="true" size={16} strokeWidth={1.7} />
              停止回应
            </Button>
          ) : null}
        </div>
      </div>

      <TranscriptDraft
        busy={sending || state.state === "transcribing" || state.state === "auto_sending"}
        hint={draftHint}
        onChange={onDraftChange}
        onRestart={onRestart}
        onSubmit={onSubmit}
        ready={draftReady}
        value={draftValue}
      />

      <footer className="voiceExperienceFooter">
        <span>当前：{mode === "direct_conversation" ? "自动发送（安全模式）" : "确认后发送"}</span>
        <i aria-hidden="true" />
        <span>声音只在本地处理</span>
      </footer>
    </section>
  );
}
