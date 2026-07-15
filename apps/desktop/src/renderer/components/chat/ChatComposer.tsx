import { Mic, Send } from "lucide-react";
import type { ChangeEventHandler, FormEventHandler, ReactNode } from "react";

import { Button } from "../ui/Button";
import { Input } from "../ui/Input";

type ChatComposerProps = {
  input: string;
  onInputChange: ChangeEventHandler<HTMLInputElement>;
  onSubmit: FormEventHandler<HTMLFormElement>;
  onVoiceClick: () => void;
  sending: boolean;
  status: ReactNode;
  statusTone: string;
  voiceActive: boolean;
  voiceDisabled: boolean;
  voiceLabel: string;
  voiceTitle: string;
};

export function ChatComposer({
  input,
  onInputChange,
  onSubmit,
  onVoiceClick,
  sending,
  status,
  statusTone,
  voiceActive,
  voiceDisabled,
  voiceLabel,
  voiceTitle
}: ChatComposerProps) {
  return (
    <form aria-label="聊天输入区" className="composer chatComposer" onSubmit={onSubmit}>
      <div className="chatComposerMain">
        <Button
          aria-label={voiceLabel}
          className={`chatVoiceButton voiceInputButton${voiceActive ? " active" : ""}`}
          disabled={voiceDisabled}
          iconOnly
          title={voiceTitle}
          variant="quiet"
          onClick={onVoiceClick}
        >
          <Mic size={18} strokeWidth={1.75} />
        </Button>
        <Input
          aria-label="聊天输入"
          className="chatComposerInput"
          placeholder="说点什么……"
          value={input}
          onChange={onInputChange}
        />
        <Button
          className="sendButton chatSendButton"
          disabled={sending || !input.trim()}
          type="submit"
          variant="primary"
        >
          <Send size={17} strokeWidth={1.7} />
          <span>{sending ? "发送中" : "发送"}</span>
        </Button>
      </div>
      <div className={`voiceInputInlineStatus chatComposerStatus voiceState-${statusTone}`} role="status">
        {status}
      </div>
    </form>
  );
}
