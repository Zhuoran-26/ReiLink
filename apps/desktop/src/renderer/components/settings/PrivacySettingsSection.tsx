import { ArrowRight, ShieldCheck } from "lucide-react";

import { Button } from "../ui/Button";
import { SettingsSection } from "./SettingsSection";

type PrivacySettingsSectionProps = {
  onOpenLocalData: () => void;
};

export function PrivacySettingsSection({ onOpenLocalData }: PrivacySettingsSectionProps) {
  return (
    <SettingsSection
      action={(
        <Button size="small" variant="ghost" onClick={onOpenLocalData}>
          管理本地数据
          <ArrowRight size={14} />
        </Button>
      )}
      icon={<ShieldCheck size={19} strokeWidth={1.55} />}
      title="隐私"
    >
      <p className="settingsExperienceDescription">你的旅程数据保存在本地。</p>
      <p className="settingsExperienceNote">ReiLink 不会上传本地记录。</p>
    </SettingsSection>
  );
}
