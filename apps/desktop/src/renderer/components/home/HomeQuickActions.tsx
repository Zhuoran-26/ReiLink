import { ArrowRight, BookOpenText, MessageSquareText, Mic } from "lucide-react";
import type { ComponentType } from "react";

type QuickActionProps = {
  description: string;
  icon: ComponentType<{ size?: number; strokeWidth?: number }>;
  label: string;
  onClick: () => void;
  primary?: boolean;
};

function QuickAction({ description, icon: Icon, label, onClick, primary = false }: QuickActionProps) {
  return (
    <button
      aria-label={label}
      className={`homeQuickAction${primary ? " homeQuickAction-primary" : ""}`}
      type="button"
      onClick={onClick}
    >
      <span className="homeQuickActionIcon" aria-hidden="true">
        <Icon size={18} strokeWidth={1.65} />
      </span>
      <span className="homeQuickActionCopy">
        <strong>{label}</strong>
        <small>{description}</small>
      </span>
      <ArrowRight className="homeQuickActionArrow" aria-hidden="true" size={17} strokeWidth={1.55} />
    </button>
  );
}

type HomeQuickActionsProps = {
  onOpenChat: () => void;
  onOpenJourney: () => void;
  onOpenVoice: () => void;
};

export function HomeQuickActions({ onOpenChat, onOpenJourney, onOpenVoice }: HomeQuickActionsProps) {
  return (
    <nav aria-label="首页快捷入口" className="homeQuickActions">
      <QuickAction
        description="安静地聊一会儿"
        icon={MessageSquareText}
        label="与 Rei 说话"
        primary
        onClick={onOpenChat}
      />
      <QuickAction description="让 Rei 听见你" icon={Mic} label="语音陪伴" onClick={onOpenVoice} />
      <QuickAction description="回到最近的记录" icon={BookOpenText} label="查看旅程" onClick={onOpenJourney} />
    </nav>
  );
}
