import { RefreshCw, VolumeX } from "lucide-react";
import type { ReactNode } from "react";

import { ReiAvatar, type ReiPresenceState } from "../components/rei/ReiAvatar";
import { Button } from "../components/ui/Button";
import { Surface } from "../components/ui/Surface";
import { StatusIndicator, type StatusTone } from "../components/ui/StatusIndicator";
import type { ThemeMode } from "../hooks/useTheme";

type AppShellProps = {
  children: ReactNode;
  header: ReactNode;
  sidebar: ReactNode;
  theme: ThemeMode;
};

export function AppShell({ children, header, sidebar, theme }: AppShellProps) {
  return (
    <Surface as="main" className="shell" data-theme={theme} level="canvas">
      {sidebar}
      <section className="appWorkspace">
        {header}
        {children}
      </section>
    </Surface>
  );
}

function headerStatusTone(status: "checking" | "connected" | "disconnected"): StatusTone {
  if (status === "connected") return "success";
  if (status === "disconnected") return "danger";
  return "warning";
}

type AppHeaderProps = {
  backendStatus: "checking" | "connected" | "disconnected";
  companionName: string;
  companionStatus: string;
  companionSubtitle: string;
  presenceState: ReiPresenceState;
  voiceActive: boolean;
  onRefresh: () => void;
  onStopVoice: () => void;
};

export function AppHeader({
  backendStatus,
  companionName,
  companionStatus,
  companionSubtitle,
  presenceState,
  voiceActive,
  onRefresh,
  onStopVoice
}: AppHeaderProps) {
  return (
    <header className="workspaceHeader">
      <div className="companionIntro">
        <ReiAvatar name={companionName} size="large" state={presenceState} />
        <div className="companionIntroCopy">
          <div className="companionTitleRow">
            <h1>{companionName}</h1>
            <StatusIndicator label={companionStatus} tone={headerStatusTone(backendStatus)} />
          </div>
          <p>{companionSubtitle}</p>
        </div>
      </div>
      <div className="headerActions">
        {voiceActive && (
          <Button aria-label="停止语音 / Stop Voice" size="small" variant="quiet" onClick={onStopVoice}>
            <VolumeX size={15} />
            停止语音
          </Button>
        )}
        <Button aria-label="刷新状态" iconOnly variant="ghost" onClick={onRefresh}>
          <RefreshCw size={17} />
        </Button>
      </div>
    </header>
  );
}
