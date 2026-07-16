import {
  BookOpenText,
  Bug,
  ChevronDown,
  ChevronRight,
  Database,
  FlaskConical,
  House,
  Layers3,
  MessageSquare,
  Mic,
  Moon,
  Settings,
  Sparkles,
  Sun
} from "lucide-react";
import { useState, type ComponentType } from "react";

import { ReiAvatar, type ReiPresenceState } from "../components/rei/ReiAvatar";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Surface";
import { StatusIndicator, type StatusTone } from "../components/ui/StatusIndicator";
import type { ThemeMode } from "../hooks/useTheme";
import type { WorkspaceId } from "./navigation";

type IconComponent = ComponentType<{ size?: number; strokeWidth?: number }>;

type NavigationItem = {
  icon: IconComponent;
  id: WorkspaceId;
  label: string;
};

const PLAYER_NAV_ITEMS: NavigationItem[] = [
  { id: "home", label: "首页", icon: House },
  { id: "chat", label: "聊天", icon: MessageSquare },
  { id: "voice", label: "声音", icon: Mic },
  { id: "game", label: "旅程", icon: BookOpenText },
  { id: "memory", label: "回忆", icon: Database },
  { id: "overlay", label: "悬浮层", icon: Layers3 },
  { id: "settings", label: "设置", icon: Settings }
];

const DEVELOPER_NAV_ITEMS: NavigationItem[] = [
  { id: "debug", label: "调试", icon: Bug },
  { id: "presentation", label: "未来展示", icon: FlaskConical }
];

function navigationStatusTone(status: "checking" | "connected" | "disconnected"): StatusTone {
  if (status === "connected") return "success";
  if (status === "disconnected") return "danger";
  return "warning";
}

type NavigationButtonProps = {
  active: boolean;
  item: NavigationItem;
  onOpenWorkspace: (workspaceId: WorkspaceId) => void;
};

function NavigationButton({ active, item, onOpenWorkspace }: NavigationButtonProps) {
  const Icon = item.icon;
  return (
    <button
      aria-current={active ? "page" : undefined}
      className={`navItem${active ? " active" : ""}`}
      type="button"
      onClick={() => onOpenWorkspace(item.id)}
    >
      <Icon size={18} strokeWidth={1.75} />
      <span>{item.label}</span>
    </button>
  );
}

type AppNavigationProps = {
  activeWorkspace: WorkspaceId;
  backendStatus: "checking" | "connected" | "disconnected";
  companionName: string;
  companionStatus: string;
  presenceState: ReiPresenceState;
  theme: ThemeMode;
  onOpenWorkspace: (workspaceId: WorkspaceId) => void;
  onToggleTheme: () => void;
};

export function AppNavigation({
  activeWorkspace,
  backendStatus,
  companionName,
  companionStatus,
  presenceState,
  theme,
  onOpenWorkspace,
  onToggleTheme
}: AppNavigationProps) {
  const developerWorkspaceActive = activeWorkspace === "debug" || activeWorkspace === "presentation";
  const [developerOpen, setDeveloperOpen] = useState(developerWorkspaceActive);
  const developerItemsVisible = developerOpen || developerWorkspaceActive;

  return (
    <aside className="appSidebar" aria-label="ReiLink 导航">
      <div className="sidebarBrand">
        <span aria-hidden="true" className="brandMark">
          <Sparkles size={19} strokeWidth={1.55} />
        </span>
        <span>ReiLink</span>
      </div>

      <nav className="navMenu" aria-label="应用导航">
        <div className="playerNavigation">
          {PLAYER_NAV_ITEMS.map((item) => (
            <NavigationButton
              active={activeWorkspace === item.id}
              item={item}
              key={item.id}
              onOpenWorkspace={onOpenWorkspace}
            />
          ))}
        </div>

        <div className="developerNavigation">
          <Button
            aria-controls="developer-navigation-items"
            aria-expanded={developerItemsVisible}
            className="developerNavigationToggle"
            size="small"
            variant="ghost"
            onClick={() => setDeveloperOpen((open) => !open)}
          >
            {developerItemsVisible ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
            <span>开发者工具</span>
          </Button>
          {developerItemsVisible && (
            <div className="developerNavigationItems" id="developer-navigation-items">
              {DEVELOPER_NAV_ITEMS.map((item) => (
                <NavigationButton
                  active={activeWorkspace === item.id}
                  item={item}
                  key={item.id}
                  onOpenWorkspace={onOpenWorkspace}
                />
              ))}
            </div>
          )}
        </div>
      </nav>

      <div className="sidebarFooter">
        <Card as="section" className="companionStatusCard" aria-label="Rei 状态">
          <ReiAvatar name={companionName} size="small" state={presenceState} />
          <div className="companionStatusCopy">
            <strong>{companionName}</strong>
            <span>安静陪你走一会儿</span>
            <StatusIndicator label={companionStatus} tone={navigationStatusTone(backendStatus)} />
          </div>
        </Card>
        <Button className="themeToggle" variant="quiet" onClick={onToggleTheme}>
          {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
          <span>{theme === "light" ? "切换到夜间" : "切换到日间"}</span>
        </Button>
      </div>
    </aside>
  );
}
