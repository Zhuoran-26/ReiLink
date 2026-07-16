import type { ReactNode } from "react";

type SettingsSectionProps = {
  action?: ReactNode;
  children: ReactNode;
  icon: ReactNode;
  title: string;
};

export function SettingsSection({ action, children, icon, title }: SettingsSectionProps) {
  const titleId = `settings-${title.replace(/\s+/g, "-")}`;

  return (
    <section className="settingsExperienceSection" aria-labelledby={titleId}>
      <span aria-hidden="true" className="settingsExperienceIcon">
        {icon}
      </span>
      <div className="settingsExperienceSectionBody">
        <div className="settingsExperienceSectionHeader">
          <h3 id={titleId}>{title}</h3>
          {action}
        </div>
        {children}
      </div>
    </section>
  );
}
