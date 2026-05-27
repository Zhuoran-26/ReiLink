import { expect, test } from "@playwright/test";

test("mock backend chat flow works", async ({ page }) => {
  await page.route("**/api/health", (route) => route.fulfill({ json: { status: "ok" } }));
  await page.route("**/api/game/status", (route) =>
    route.fulfill({
      json: {
        game_id: "elden_ring",
        game_name: "Elden Ring",
        process_name: "eldenring.exe",
        status: "running",
        confidence: 1,
        tags: ["soulslike"]
      }
    })
  );
  await page.route("**/api/memory/profile", (route) =>
    route.fulfill({
      json: {
        user_name: null,
        favorite_game: "Elden Ring",
        preferred_tone: null,
        likes_teasing: null,
        skill_level: null,
        current_boss: null,
        repeated_struggles: [],
        emotional_notes: [],
        last_seen_at: null,
        memory_updated_at: {}
      }
    })
  );
  await page.route("**/api/debug/memory?**", (route) =>
    route.fulfill({
      json: {
        prompt_order: ["current_user_message", "current_session", "memory", "persona"],
        memory_written: false,
        current_boss: null,
        emotional_note: null,
        recent_episode_count: 0,
        items: []
      }
    })
  );
  await page.route("**/api/debug/chat", (route) =>
    route.fulfill({
      json: {
        intent: "elden_ring_boss_strategy",
        selected_model: "deepseek-v4-pro",
        thinking_enabled: true,
        reasoning_effort: "medium",
        prompt_tokens_estimate: 100,
        llm_latency_ms: 100,
        memory_latency_ms: 0,
        total_latency_ms: 120,
        reply_segments_count: 2,
        segmenter_mode: "strategy"
      }
    })
  );
  await page.route("**/api/chat", (route) =>
    route.fulfill({
      json: {
        reply: "别急。少打一刀。",
        reply_segments: ["别急。", "少打一刀。"],
        segmenter_mode: "strategy",
        persona_id: "rei_like",
        game_status: "running",
        sources: ["data/elden_ring/bosses.json"],
        timestamp: new Date().toISOString()
      }
    })
  );

  await page.goto("/");
  await expect(page.getByText("艾尔登法环：运行中")).toBeVisible();
  await page.getByLabel("聊天输入").fill("Margit 怎么打?");
  await page.getByRole("button", { name: /发送/i }).click();
  await expect(page.getByText("别急。")).toBeVisible();
  await expect(page.getByText("少打一刀。")).toBeVisible();
  await expect(page.locator("#root")).not.toBeEmpty();
});
