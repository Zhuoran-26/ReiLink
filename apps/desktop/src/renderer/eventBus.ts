import type { ReiLinkEvent } from "../shared/events";

export type ReiLinkEventListener = (event: ReiLinkEvent) => void;

const DEFAULT_MAX_EVENTS = 100;

export class InteractionEventBus {
  private readonly maxEvents: number;
  private events: ReiLinkEvent[] = [];
  private listeners = new Set<ReiLinkEventListener>();

  constructor(maxEvents = DEFAULT_MAX_EVENTS) {
    this.maxEvents = maxEvents;
  }

  emit(event: ReiLinkEvent) {
    this.events = [...this.events, event].slice(-this.maxEvents);
    for (const listener of this.listeners) {
      listener(event);
    }
  }

  subscribe(listener: ReiLinkEventListener) {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  getRecentEvents(limit = this.maxEvents) {
    return this.events.slice(-limit);
  }

  clear() {
    this.events = [];
    this.listeners.clear();
  }
}

// Renderer-only, in-memory interaction stream. It is not persisted, sent to the
// backend, uploaded, or allowed to carry API keys/secrets/raw prompts.
//
// Future consumers:
// - TTS can subscribe to assistant_reply_segment_shown.
// - Live2D can subscribe to assistant_reply_started, proactive_message_shown, and game_session_changed.
// - Overlay can subscribe to proactive_message_shown and backend_status_changed.
export const eventBus = new InteractionEventBus();
