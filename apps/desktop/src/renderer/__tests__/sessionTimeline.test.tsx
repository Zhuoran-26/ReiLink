import { describe, expect, it } from "vitest";

import type { ReiLinkEvent } from "../../shared/events";
import {
  appendSessionTimelineItems,
  sanitizeSessionTimelineText,
  sessionTimelineItemsFromEvent
} from "../sessionTimeline";

const timestamp = "2026-06-08T12:00:00.000Z";

describe("sessionTimeline", () => {
  it("keeps non-session raw chat events out of the timeline", () => {
    const events: ReiLinkEvent[] = [
      { type: "user_message_sent", timestamp, text: "完整用户消息 /Users/aragoto/.env" },
      { type: "assistant_reply_segment_shown", timestamp, segment_index: 0, text: "完整 assistant reply" }
    ];

    expect(events.flatMap(sessionTimelineItemsFromEvent)).toEqual([]);
  });

  it("creates safe game context and game session items", () => {
    const items = [
      ...sessionTimelineItemsFromEvent({
        type: "game_context_changed",
        timestamp,
        game: "Elden Ring",
        source: "detector"
      }),
      ...sessionTimelineItemsFromEvent({
        type: "game_session_changed",
        timestamp,
        game: "Elden Ring",
        current_boss: "Margit",
        activity: "boss_cleared",
        death_count: 3,
        frustration_count: 2,
        last_cleared_boss: "Margit"
      })
    ];

    expect(items.map((item) => item.type)).toEqual([
      "game_selected",
      "boss_detected",
      "death_count_changed",
      "frustration_changed",
      "boss_cleared"
    ]);
    expect(items.map((item) => item.summary)).toEqual([
      "切换游戏：Elden Ring",
      "检测到 Boss：Margit",
      "死亡次数更新：3",
      "挫败状态升高：2",
      "击败 Boss：Margit"
    ]);
  });

  it("records knowledge usage without leaking snippets or local paths", () => {
    const longSnippet = "Margit phase 2 tips ".repeat(10);
    const items = sessionTimelineItemsFromEvent({
      type: "knowledge_used",
      timestamp,
      game: "艾尔登法环",
      topics: ["已使用本地知识", `${longSnippet} /Users/aragoto/Desktop/ReiLink/services/backend/.env raw prompt`]
    });

    expect(items).toHaveLength(1);
    expect(items[0].summary).toContain("使用知识：艾尔登法环");
    expect(items[0].summary.length).toBeLessThanOrEqual(96);
    expect(items[0].summary).not.toContain("/Users/aragoto");
    expect(items[0].summary).not.toContain(".env");
    expect(items[0].summary).not.toContain("raw prompt");
  });

  it("records proactive and memory actions without full text payloads", () => {
    const items = [
      ...sessionTimelineItemsFromEvent({
        type: "proactive_message_shown",
        timestamp,
        trigger_type: "repeated_death",
        text: "你开始急了。完整 assistant text 不应该进入这里。"
      }),
      ...sessionTimelineItemsFromEvent({
        type: "pending_memory_accepted",
        timestamp,
        memory_id: "memory-with-full-text"
      }),
      ...sessionTimelineItemsFromEvent({
        type: "pending_memory_ignored",
        timestamp,
        memory_id: "ignored-memory-with-full-text"
      })
    ];

    expect(items.map((item) => item.summary)).toEqual([
      "主动陪伴已显示：反复死亡",
      "记忆已接受",
      "记忆已忽略"
    ]);
    expect(items.map((item) => item.summary).join(" ")).not.toContain("你开始急了");
    expect(items.map((item) => item.summary).join(" ")).not.toContain("memory-with-full-text");
  });

  it("sanitizes sensitive text and keeps only the newest timeline items", () => {
    expect(sanitizeSessionTimelineText("API key in /Users/aragoto/.env raw stderr transcript")).not.toMatch(
      /API key|\/Users|\.env|raw stderr|transcript/i
    );

    const incoming = Array.from({ length: 55 }, (_, index) => ({
      id: `item-${index}`,
      timestamp,
      type: "death_count_changed" as const,
      source: "game_session" as const,
      summary: `死亡次数更新：${index}`
    }));
    const limited = appendSessionTimelineItems([], incoming, 50);

    expect(limited).toHaveLength(50);
    expect(limited[0].summary).toBe("死亡次数更新：5");
    expect(limited.at(-1)?.summary).toBe("死亡次数更新：54");
  });
});
