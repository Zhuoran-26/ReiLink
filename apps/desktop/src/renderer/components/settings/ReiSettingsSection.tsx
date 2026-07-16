import { Sparkles } from "lucide-react";

import { ReiAvatar } from "../rei/ReiAvatar";
import { SettingsSection } from "./SettingsSection";

export function ReiSettingsSection() {
  return (
    <SettingsSection icon={<Sparkles size={19} strokeWidth={1.55} />} title="Rei">
      <div className="reiSettingsSummary">
        <ReiAvatar name="Rei" size="small" state="idle" />
        <div>
          <span className="settingsExperienceLabel">陪伴方式</span>
          <strong>安静、克制，保持一点距离。</strong>
          <p>更多互动方式将在未来版本开放。</p>
        </div>
      </div>
    </SettingsSection>
  );
}
