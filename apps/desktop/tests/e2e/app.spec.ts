import { expect, test } from "@playwright/test";

test("mock backend chat flow works", async ({ page }) => {
  await page.route("**/api/health", (route) => route.fulfill({ json: { status: "ok" } }));
  await page.route("**/api/settings", (route) =>
    route.fulfill({
      json: {
        persona_mode: "minimal",
        debug_panel: "show",
        memory_enabled: true,
        pending_memory_mode: "manual",
        response_length: "normal",
        model_preference: "auto",
        proactive_companion: "off",
        proactive_sensitivity: "low",
        auto_game_detection: "on"
      }
    })
  );
  await page.route("**/api/proactive/status?**", (route) =>
    route.fulfill({
      json: {
        enabled: false,
        sensitivity: "low",
        last_triggered_at: null,
        last_triggered_type: "none",
        next_possible_trigger_at: null,
        active_candidate_triggers: [],
        cooldown_remaining_seconds: 0,
        last_trigger_reason: null
      }
    })
  );
  await page.route("**/api/proactive/check", (route) =>
    route.fulfill({
      json: {
        should_send: false,
        trigger_type: "none",
        message: "",
        reason: "disabled",
        cooldown_remaining_seconds: 0
      }
    })
  );
  await page.route("**/api/game/status", (route) =>
    route.fulfill({
      json: {
        game_id: "elden_ring",
        game_name: "Elden Ring",
        process_name: "eldenring.exe",
        status: "running",
        confidence: 1,
        tags: ["soulslike"],
        detected_game_id: "elden_ring",
        display_name: "艾尔登法环",
        match_confidence: 1,
        match_source: "process",
        knowledge_game_id: "elden_ring",
        detected_at: new Date().toISOString()
      }
    })
  );
  await page.route("**/api/game/detected", (route) =>
    route.fulfill({
      json: {
        status: "running",
        detected_game_id: "elden_ring",
        display_name: "艾尔登法环",
        process_name: "eldenring.exe",
        match_confidence: 1,
        match_source: "process",
        knowledge_game_id: "elden_ring",
        detected_at: new Date().toISOString()
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
        model_used: "deepseek-v4-pro",
        main_reply_model: "deepseek-v4-pro",
        model_route_mode: "auto",
        route_reason: "explicit_detail_request",
        route_intent: "elden_ring_boss_strategy",
        estimated_complexity: "high",
        fallback_reason: null,
        thinking_enabled: true,
        reasoning_effort: "medium",
        prompt_tokens_estimate: 100,
        llm_latency_ms: 100,
        provider_latency_ms: 100,
        memory_latency_ms: 0,
        total_latency_ms: 120,
        response_latency_ms: 120,
        request_started_at: new Date().toISOString(),
        reply_segments_count: 2,
        segmenter_mode: "strategy",
        semantic_extraction_called: false,
        semantic_extraction_model: null,
        semantic_extraction_latency_ms: 0,
        semantic_extraction_parse_error: null,
        knowledge_matched: true,
        knowledge_game_id: "elden_ring",
        knowledge_game_display_name: "艾尔登法环",
        knowledge_match_source: "current_game",
        knowledge_path: "data/knowledge/games/elden_ring/snippets.json",
        knowledge_supported_games_count: 1,
        knowledge_fallback_reason: null,
        knowledge_confidence: 0.83,
        matched_topics: ["margit", "boss_strategy"],
        snippets_count: 2,
        snippet_titles: ["恶兆妖鬼 Margit：延迟攻击", "恶兆妖鬼 Margit：战前准备"],
        knowledge_used_in_prompt: true
      }
    })
  );
  await page.route("**/api/debug/provider", (route) =>
    route.fulfill({
      json: {
        provider: "deepseek",
        model: "deepseek-v4-pro",
        base_url: "https://api.deepseek.com",
        api_key_loaded: true,
        configured_provider: "deepseek",
        fallback_to_mock: false,
        env_file_loaded: true,
        env_file_path: "/tmp/.env",
        persona_mode: "minimal",
        model_route_mode: "auto",
        deepseek_model_fast: "deepseek-v4-flash",
        deepseek_model_pro: "deepseek-v4-pro",
        selected_model: "deepseek-v4-pro",
        main_reply_model: "deepseek-v4-pro",
        route_reason: "explicit_detail_request",
        route_intent: "elden_ring_boss_strategy",
        estimated_complexity: "high",
        provider_latency_ms: 100,
        semantic_extraction_model: null,
        fallback_reason: null
      }
    })
  );
  await page.route("**/api/debug/game-session", (route) =>
    route.fulfill({
      json: {
        current_game: "Elden Ring",
        current_boss: null,
        last_boss: null,
        last_attempted_boss: null,
        last_cleared_boss: null,
        current_activity: null,
        recent_game_topics: [],
        boss_history: [],
        frustration_count: 0,
        death_count: 0,
        last_user_intent: null,
        last_game_intent: null,
        last_updated_at: null
      }
    })
  );
  await page.route("**/api/debug/semantic-extraction/latest", (route) =>
    route.fulfill({
      json: {
        latest_user_message: null,
        rule_result: null,
        rule_confidence: 0,
        llm_called: false,
        semantic_extraction_model: null,
        semantic_extraction_latency_ms: 0,
        provider_latency_ms: 0,
        llm_result: null,
        final_decision: null,
        skip_reason: "not_run",
        latency_ms: 0,
        parse_error: null
      }
    })
  );
  await page.route("**/api/debug/prompt-preview?**", (route) =>
    route.fulfill({
      json: {
        persona_mode: "minimal",
        current_user_message: null,
        prompt_order: [],
        model_route_summary: {},
        session_focus_summary: {},
        game_state_summary: {},
        knowledge_summary: {},
        memory_summary: {},
        final_context_summary: {},
        warnings: []
      }
    })
  );
  await page.route("**/api/memory/pending", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/chat", (route) =>
    route.fulfill({
      json: {
        reply: "别急。少打一刀。",
        reply_segments: ["别急。", "少打一刀。"],
        segmenter_mode: "strategy",
        persona_id: "rei_like",
        game_status: "running",
        sources: ["data/knowledge/games/elden_ring/snippets.json"],
        timestamp: new Date().toISOString(),
        request_started_at: new Date().toISOString(),
        response_latency_ms: 120,
        provider_latency_ms: 100,
        model_used: "deepseek-v4-pro",
        route_reason: "explicit_detail_request"
      }
    })
  );

  await page.goto("/");
  await expect(page.getByText("已连接")).toBeVisible();
  await expect(page.getByText("游戏：Elden Ring")).toBeVisible();
  await page.getByLabel("聊天输入").fill("Margit 怎么打?");
  await page.getByRole("button", { name: /发送/i }).click();
  await expect(page.getByText("别急。")).toBeVisible();
  await expect(page.getByText("少打一刀。")).toBeVisible();
  await expect(page.locator("#root")).not.toBeEmpty();
});
