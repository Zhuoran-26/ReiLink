import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

import {
  createOverlayState,
  OVERLAY_PLACEHOLDER_TEXT,
  type OverlayMessage,
  type OverlayState
} from "../shared/overlay";

const placeholderMessage = (): OverlayMessage => ({
  id: "overlay-placeholder",
  speaker: "Rei",
  text: OVERLAY_PLACEHOLDER_TEXT,
  source: "placeholder",
  timestamp: new Date().toISOString()
});

export function OverlayApp() {
  const [state, setState] = useState<OverlayState>(() => createOverlayState(false, false, []));
  const messages = useMemo(() => (state.messages.length > 0 ? state.messages : [placeholderMessage()]), [state.messages]);
  const overlayStyle = useMemo(() => ({
    "--overlay-bg-opacity": String(state.opacity)
  }) as CSSProperties, [state.opacity]);

  useEffect(() => {
    document.body.classList.add("overlayBody");
    const runtime = window.reilinkRuntime;
    void runtime?.getOverlayStatus?.().then(setState).catch(() => undefined);
    const unsubscribe = runtime?.onOverlayState?.(setState);
    return () => {
      document.body.classList.remove("overlayBody");
      unsubscribe?.();
    };
  }, []);

  return (
    <main className="overlayRoot" aria-label="Rei 游戏悬浮层" style={overlayStyle}>
      <section className="overlayBubbleLayer" aria-label="Rei 最近短消息">
        {messages.slice(-state.max_messages).map((message) => (
          <article className="overlayBubbleRow" key={message.id}>
            <span className="overlayAvatar" aria-label="Rei">
              Rei
            </span>
            <p className="overlayBubble">{message.text}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
