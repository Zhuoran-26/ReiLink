import { describe, expect, it, vi } from "vitest";

import { InteractionEventBus } from "../eventBus";
import type { ReiLinkEvent } from "../../shared/events";

const userEvent = (text: string): ReiLinkEvent => ({
  type: "user_message_sent",
  timestamp: new Date().toISOString(),
  text
});

describe("InteractionEventBus", () => {
  it("emits events to subscribers and supports unsubscribe", () => {
    const bus = new InteractionEventBus();
    const listener = vi.fn();

    const unsubscribe = bus.subscribe(listener);
    const event = userEvent("Margit 怎么打？");
    bus.emit(event);

    expect(listener).toHaveBeenCalledWith(event);
    expect(bus.getRecentEvents()).toEqual([event]);

    unsubscribe();
    bus.emit(userEvent("再试一次"));

    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("keeps only the most recent 100 events by default", () => {
    const bus = new InteractionEventBus();

    for (let index = 0; index < 105; index += 1) {
      bus.emit(userEvent(`message-${index}`));
    }

    const recent = bus.getRecentEvents();
    expect(recent).toHaveLength(100);
    expect(recent[0]).toMatchObject({ text: "message-5" });
    expect(recent.at(-1)).toMatchObject({ text: "message-104" });
    expect(bus.getRecentEvents(3).map((event) => event.type)).toEqual([
      "user_message_sent",
      "user_message_sent",
      "user_message_sent"
    ]);
  });
});
