import { ArrowRight, Mic2 } from "lucide-react";

import type { AppSettings } from "../../../shared/api";
import { Button } from "../ui/Button";
import { SettingsSection } from "./SettingsSection";

type VoiceSettingsSectionProps = {
  interactionMode: AppSettings["voice_interaction_mode"];
  onOpenVoice: () => void;
  outputEnabled: boolean;
};

export function VoiceSettingsSection({ interactionMode, onOpenVoice, outputEnabled }: VoiceSettingsSectionProps) {
  return (
    <SettingsSection
      action={(
        <Button size="small" variant="quiet" onClick={onOpenVoice}>
          管理语音设置
          <ArrowRight size={14} />
        </Button>
      )}
      icon={<Mic2 size={19} strokeWidth={1.55} />}
      title="语音"
    >
      <dl className="settingsExperienceFacts">
        <div>
          <dt>当前模式</dt>
          <dd>{interactionMode === "direct_conversation" ? "自动发送（安全模式）" : "确认后发送"}</dd>
        </div>
        <div>
          <dt>回应声音</dt>
          <dd>{outputEnabled ? "已开启" : "已关闭"}</dd>
        </div>
      </dl>
    </SettingsSection>
  );
}
