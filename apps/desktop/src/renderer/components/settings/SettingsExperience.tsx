import type { AppSettings } from "../../../shared/api";
import type { ThemeMode } from "../../hooks/useTheme";
import { MemoryPreviewSection } from "./MemoryPreviewSection";
import { PrivacySettingsSection } from "./PrivacySettingsSection";
import { ReiSettingsSection } from "./ReiSettingsSection";
import { SystemSettingsSection } from "./SystemSettingsSection";
import { VoiceSettingsSection } from "./VoiceSettingsSection";

type SettingsExperienceProps = {
  onOpenDeveloper: () => void;
  onOpenLocalData: () => void;
  onOpenMoreSettings: () => void;
  onOpenVoice: () => void;
  onToggleTheme: () => void;
  theme: ThemeMode;
  voiceInteractionMode: AppSettings["voice_interaction_mode"];
  voiceOutputEnabled: boolean;
};

export function SettingsExperience({
  onOpenDeveloper,
  onOpenLocalData,
  onOpenMoreSettings,
  onOpenVoice,
  onToggleTheme,
  theme,
  voiceInteractionMode,
  voiceOutputEnabled
}: SettingsExperienceProps) {
  return (
    <section aria-label="陪伴设置" className="settingsExperience">
      <header className="settingsExperienceIntro">
        <span aria-hidden="true" className="settingsExperienceGlyph">◇</span>
        <p className="eyebrow">Companion preferences</p>
        <h2>调整 Rei 陪伴你的方式。</h2>
        <p>只保留真正需要你决定的部分，其余保持安静。</p>
      </header>

      <div className="settingsExperienceSections">
        <ReiSettingsSection />
        <VoiceSettingsSection
          interactionMode={voiceInteractionMode}
          onOpenVoice={onOpenVoice}
          outputEnabled={voiceOutputEnabled}
        />
        <MemoryPreviewSection />
        <PrivacySettingsSection onOpenLocalData={onOpenLocalData} />
        <SystemSettingsSection
          onOpenDeveloper={onOpenDeveloper}
          onOpenMoreSettings={onOpenMoreSettings}
          onToggleTheme={onToggleTheme}
          theme={theme}
        />
      </div>
    </section>
  );
}
