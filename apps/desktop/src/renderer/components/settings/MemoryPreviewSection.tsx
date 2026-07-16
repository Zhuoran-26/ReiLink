import { BookOpenText } from "lucide-react";

import { SettingsSection } from "./SettingsSection";

export function MemoryPreviewSection() {
  return (
    <SettingsSection
      action={<span className="settingsFutureBadge">尚未开放</span>}
      icon={<BookOpenText size={19} strokeWidth={1.55} />}
      title="Rei 的日记"
    >
      <p className="settingsExperienceDescription">未来这里可以查看 Rei 记录下的旅程。</p>
    </SettingsSection>
  );
}
