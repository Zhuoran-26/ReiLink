import { ReiAvatar, type ReiPresenceState } from "../rei/ReiAvatar";

export type ChatMessageRole = "user" | "assistant";

type ChatMessageProps = {
  meta: string;
  pending?: boolean;
  proactive?: boolean;
  reiState?: ReiPresenceState;
  role: ChatMessageRole;
  text: string;
};

export function ChatMessage({
  meta,
  pending = false,
  proactive = false,
  reiState = "idle",
  role,
  text
}: ChatMessageProps) {
  const isRei = role === "assistant";

  return (
    <article
      className={`messageBubble chatMessage ${role}${pending ? " pending" : ""}${proactive ? " proactive" : ""}`}
    >
      {isRei && <ReiAvatar name="Rei" size="small" state={pending ? "thinking" : reiState} />}
      <div className="chatMessageBody">
        <div className="messageHeader">
          <span className="messageSpeaker">{isRei ? "Rei" : "你"}</span>
          <small className="messageTime">{meta}</small>
        </div>
        <div className="chatMessageText">
          <p className={pending ? "chatVisuallyHidden" : undefined}>{text}</p>
          {pending && (
            <span aria-label="Rei 正在思考" className="chatThinkingDots" role="status">
              <i />
              <i />
              <i />
            </span>
          )}
        </div>
      </div>
    </article>
  );
}
