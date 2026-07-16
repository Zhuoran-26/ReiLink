import { ArrowRight, Bug, MonitorCog, Moon, Sun } from "lucide-react";

import { Button } from "../ui/Button";
import type { ThemeMode } from "../../hooks/useTheme";
import { SettingsSection } from "./SettingsSection";

type SystemSettingsSectionProps = {
  onOpenDeveloper: () => void;
  onOpenMoreSettings: () => void;
  onToggleTheme: () => void;
  theme: ThemeMode;
};

export function SystemSettingsSection({
  onOpenDeveloper,
  onOpenMoreSettings,
  onToggleTheme,
  theme
}: SystemSettingsSectionProps) {
  const chooseTheme = (nextTheme: ThemeMode) => {
    if (nextTheme !== theme) onToggleTheme();
  };

  return (
    <SettingsSection icon={<MonitorCog size={19} strokeWidth={1.55} />} title="系统">
      <div className="settingsThemeRow">
        <div>
          <span className="settingsExperienceLabel">主题</span>
          <p>跟随你现在想停留的氛围。</p>
        </div>
        <div aria-label="主题" className="settingsThemeControl" role="group">
          <button
            aria-label="使用日间主题"
            aria-pressed={theme === "light"}
            type="button"
            onClick={() => chooseTheme("light")}
          >
            <Sun size={14} />
            日间
          </button>
          <button
            aria-label="使用夜间主题"
            aria-pressed={theme === "dark"}
            type="button"
            onClick={() => chooseTheme("dark")}
          >
            <Moon size={14} />
            夜间
          </button>
        </div>
      </div>
      <div className="settingsExperienceLinks">
        <Button aria-label="打开开发者工具" variant="ghost" onClick={onOpenDeveloper}>
          <Bug size={16} />
          <span>
            <strong>开发者工具</strong>
            <small>运行状态与调试信息留在单独空间。</small>
          </span>
          <ArrowRight className="settingsLinkArrow" size={15} />
        </Button>
        <Button aria-label="更多设置" variant="ghost" onClick={onOpenMoreSettings}>
          <MonitorCog size={16} />
          <span>
            <strong>更多设置</strong>
            <small>模型、本地数据与现有高级功能。</small>
          </span>
          <ArrowRight className="settingsLinkArrow" size={15} />
        </Button>
      </div>
    </SettingsSection>
  );
}
