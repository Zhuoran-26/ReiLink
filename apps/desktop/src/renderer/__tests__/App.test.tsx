import { act } from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App, INTERIM_PLACEHOLDERS } from "../App";

const runningStatus = {
  game_id: "elden_ring",
  game_name: "Elden Ring",
  process_name: "eldenring.exe",
  status: "running",
  confidence: 1,
  tags: ["soulslike"]
};

const memoryProfile = {
  user_name: null,
  favorite_game: "Elden Ring",
  preferred_tone: "轻微吐槽",
  likes_teasing: true,
  skill_level: null,
  current_boss: "恶兆妖鬼 Margit",
  repeated_struggles: ["恶兆妖鬼 Margit死亡循环"],
  emotional_notes: ["玩家在死亡循环里有点急"],
  last_seen_at: new Date().toISOString(),
  memory_updated_at: {}
};

const memoryDebug = {
  prompt_order: ["current_user_message", "current_session", "memory", "persona"],
  memory_written: true,
  current_boss: "恶兆妖鬼 Margit",
  emotional_note: "frustrated",
  recent_episode_count: 2,
  items: [
    { source: "profile", field: "current_boss", text: "玩家当前卡点：恶兆妖鬼 Margit" },
    { source: "episode", field: "summary", text: "玩家最近卡在恶兆妖鬼 Margit，问题像是恶兆妖鬼 Margit死亡循环" }
  ]
};

const chatDebug = {
  intent: "casual_chat",
  selected_model: "deepseek-v4-flash",
  thinking_enabled: false,
  reasoning_effort: null,
  prompt_tokens_estimate: 120,
  llm_latency_ms: 300,
  memory_latency_ms: 0,
  total_latency_ms: 320,
  reply_segments_count: 1,
  segmenter_mode: "compact"
};

const gameSessionDebug = {
  current_game: "Elden Ring",
  current_boss: {
    name: "恶兆妖鬼 Margit",
    updated_at: new Date().toISOString(),
    confidence: 0.95,
    source: "current_message",
    mention_count: 2,
    age_hours: 0.1,
    is_fresh: true,
    freshness: "fresh"
  },
  last_boss: "恶兆妖鬼 Margit",
  last_attempted_boss: "恶兆妖鬼 Margit",
  last_cleared_boss: null,
  current_activity: "boss_attempt",
  recent_game_topics: ["恶兆妖鬼 Margit"],
  boss_history: [
    {
      name: "恶兆妖鬼 Margit",
      status: "current",
      updated_at: new Date().toISOString(),
      confidence: 0.95,
      source: "current_message",
      mention_count: 2,
      last_activity: "boss_attempt",
      age_hours: 0.1,
      freshness: "fresh"
    }
  ],
  frustration_count: 1,
  death_count: 1,
  last_user_intent: "casual_chat",
  last_game_intent: "casual_chat",
  last_updated_at: new Date().toISOString()
};

const promptPreview = {
  persona_mode: "minimal",
  current_user_message: "Margit 怎么打？",
  prompt_order: ["current_user_message", "current_session_context", "session_focus", "game_state", "memory", "persona"],
  session_focus_summary: { boss: "恶兆妖鬼 Margit", source: "current_message", prompt_line: "当前短期焦点：恶兆妖鬼 Margit" },
  game_state_summary: {
    current_game: "Elden Ring",
    current_boss: gameSessionDebug.current_boss,
    current_activity: "boss_attempt",
    freshness: "fresh",
    death_count: 1,
    frustration_count: 1,
    last_attempted_boss: "恶兆妖鬼 Margit",
    last_cleared_boss: null,
    boss_history: gameSessionDebug.boss_history
  },
  memory_summary: {
    injected: memoryDebug.items,
    skipped: [{ source: "profile", field: "current_boss", reason: "conflict_with_fresh_game_state", text: "玩家当前卡点：大树守卫" }]
  },
  final_context_summary: { raw_prompt_omitted: true, memory_injected_count: 2 },
  warnings: ["memory boss conflicts with fresh game state"]
};

const semanticExtractionDebug = {
  latest_user_message: "我喜欢简短的游戏攻略",
  rule_result: { game_event: { type: "none" }, memory_candidate: { type: "guide_preference" } },
  rule_confidence: 0.65,
  llm_called: true,
  llm_result: {
    game_event: { type: "none" },
    memory_candidate: { type: "guide_preference" }
  },
  final_decision: {
    game_event: { type: "none" },
    memory_candidate: { type: "guide_preference" }
  },
  skip_reason: null,
  latency_ms: 42,
  parse_error: null
};

const pendingMemories = [
  {
    id: "pending-1",
    type: "user_preference",
    text: "玩家不喜欢长篇攻略",
    source: "explicit_user_statement",
    confidence: 0.95,
    status: "pending",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    evidence: {
      user_message: "我不喜欢长篇攻略",
      game_state_summary: "current_boss=none"
    }
  }
];

const appSettings = {
  persona_mode: "minimal",
  debug_panel: "show",
  memory_enabled: true,
  pending_memory_mode: "manual",
  response_length: "normal",
  model_preference: "auto"
};

let appSettingsStore = { ...appSettings };

const resetSettingsResponse = () => {
  appSettingsStore = { ...appSettings };
};

const settingsResponse = (url: string, init?: RequestInit) => {
  if (url.endsWith("/api/settings") && init?.method === "POST") {
    appSettingsStore = { ...appSettingsStore, ...JSON.parse(String(init.body ?? "{}")) };
    return Response.json(appSettingsStore);
  }
  if (url.endsWith("/api/settings")) return Response.json(appSettingsStore);
  return null;
};

const pendingMemoryResponse = (url: string, init?: RequestInit) => {
  if (url.endsWith("/api/memory/pending")) return Response.json(pendingMemories);
  if (url.endsWith("/api/memory/pending/clear") && init?.method === "POST") {
    return Response.json({ status: "cleared" });
  }
  if (url.includes("/api/memory/pending/pending-1/accept") && init?.method === "POST") {
    return Response.json({ ...pendingMemories[0], status: "accepted" });
  }
  if (url.includes("/api/memory/pending/pending-1/ignore") && init?.method === "POST") {
    return Response.json({ ...pendingMemories[0], status: "ignored" });
  }
  return null;
};

const debugActionResponse = (url: string, init?: RequestInit) => {
  if (url.endsWith("/api/debug/game-session/reset") && init?.method === "POST") {
    return Response.json({ status: "reset" });
  }
  if (url.endsWith("/api/memory/reset") && init?.method === "POST") {
    return Response.json({ status: "reset" });
  }
  return null;
};

const chatResponse = {
  reply: "别急着翻滚。先看动作。再试一次。",
  reply_segments: ["别急着翻滚。先看动作。再试一次。"],
  segmenter_mode: "compact",
  persona_id: "rei_like",
  game_status: "running",
  sources: ["data/elden_ring/bosses.json"],
  timestamp: new Date().toISOString()
};

describe("App", () => {
  beforeEach(() => {
    let uuid = 0;
    resetSettingsResponse();
    vi.stubGlobal("crypto", { randomUUID: () => `test-id-${uuid++}` });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return debugAction;
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return pendingResponse;
        const settings = settingsResponse(url, init);
        if (settings) return settings;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json(runningStatus);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(chatDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json(gameSessionDebug);
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Response.json(semanticExtractionDebug);
        if (url.includes("/api/debug/prompt-preview")) return Response.json(promptPreview);
        if (url.endsWith("/api/chat") && init?.method === "POST") {
          return Response.json(chatResponse);
        }
        return new Response("missing", { status: 404 });
      })
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders the app", async () => {
    render(<App />);
    expect(screen.getByText("ReiLink")).toBeInTheDocument();
    await screen.findByText("已连接");
  });

  it("renders the polished companion layout sections", async () => {
    render(<App />);

    await screen.findByText("已连接");
    const navigation = screen.getByRole("navigation", { name: "应用导航" });
    expect(navigation).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "主聊天界面" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "信息侧栏" })).toBeInTheDocument();
    expect(within(navigation).getByText("Chat")).toBeInTheDocument();
    expect(within(navigation).getByText("Memory")).toBeInTheDocument();
    expect(within(navigation).getByText("Game")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pending Memory" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Game Session" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Debug Panel/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Prompt Preview/i })).toBeInTheDocument();
    expect(screen.queryByText("Semantic Extraction")).not.toBeInTheDocument();
  });

  it("shows running game status", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getAllByText("Elden Ring").length).toBeGreaterThan(0));
    expect(screen.getAllByText("恶兆妖鬼 Margit").length).toBeGreaterThan(0);
    expect(screen.getAllByText("boss_attempt").length).toBeGreaterThan(0);
  });

  it("renders settings panel values", async () => {
    render(<App />);

    expect(await screen.findByLabelText("Persona Mode")).toHaveValue("minimal");
    expect(screen.getByRole("combobox", { name: "Debug Panel" })).toHaveValue("show");
    expect(screen.getByLabelText("Memory")).toHaveValue("enabled");
    expect(screen.getByLabelText("Pending Memory Mode")).toHaveValue("manual");
    expect(screen.getByLabelText("Response Length")).toHaveValue("normal");
    expect(screen.getByLabelText("Model Preference")).toHaveValue("auto");
  });

  it("updates settings through the API", async () => {
    render(<App />);

    await userEvent.selectOptions(await screen.findByLabelText("Persona Mode"), "guarded");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ persona_mode: "guarded" }) })
      )
    );

    await userEvent.selectOptions(screen.getByLabelText("Memory"), "disabled");
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/settings"),
        expect.objectContaining({ method: "POST", body: JSON.stringify({ memory_enabled: false }) })
      )
    );
  });

  it("hides debug panel through settings", async () => {
    render(<App />);

    await screen.findByRole("button", { name: /Debug Panel/i });
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Debug Panel" }), "hide");

    await waitFor(() => expect(screen.queryByRole("button", { name: /Debug Panel/i })).not.toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /Prompt Preview/i })).not.toBeInTheDocument();
  });

  it("sends chat and renders user plus assistant messages", async () => {
    render(<App />);
    await userEvent.type(screen.getByLabelText("聊天输入"), "Margit 怎么打？");
    await userEvent.click(screen.getByRole("button", { name: /发送/i }));
    expect(screen.getByText("Margit 怎么打？")).toBeInTheDocument();
    await screen.findByText("别急着翻滚。先看动作。再试一次。");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/chat"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("does not show an interim placeholder before three seconds", async () => {
    vi.useFakeTimers();
    let resolveChat: (value: Response) => void = () => {};
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return Promise.resolve(debugAction);
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return Promise.resolve(pendingResponse);
        const settings = settingsResponse(url, init);
        if (settings) return Promise.resolve(settings);
        if (url.endsWith("/api/health")) return Promise.resolve(Response.json({ status: "ok" }));
        if (url.endsWith("/api/game/status")) return Promise.resolve(Response.json(runningStatus));
        if (url.endsWith("/api/memory/profile")) return Promise.resolve(Response.json(memoryProfile));
        if (url.includes("/api/debug/memory")) return Promise.resolve(Response.json(memoryDebug));
        if (url.endsWith("/api/debug/chat")) return Promise.resolve(Response.json(chatDebug));
        if (url.endsWith("/api/debug/game-session")) return Promise.resolve(Response.json(gameSessionDebug));
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Promise.resolve(Response.json(semanticExtractionDebug));
        if (url.includes("/api/debug/prompt-preview")) return Promise.resolve(Response.json(promptPreview));
        if (url.endsWith("/api/chat") && init?.method === "POST") {
          return new Promise<Response>((resolve) => {
            resolveChat = resolve;
          });
        }
        return Promise.resolve(new Response("missing", { status: 404 }));
      })
    );
    render(<App />);
    fireEvent.change(screen.getByLabelText("聊天输入"), { target: { value: "你好" } });
    fireEvent.click(screen.getByRole("button", { name: /发送/i }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2999);
    });
    expect(screen.queryByText("……")).not.toBeInTheDocument();
    await act(async () => {
      resolveChat(
        Response.json({
          reply: "我在。",
          reply_segments: ["我在。"],
          segmenter_mode: "compact",
          persona_id: "rei_like",
          game_status: "running",
          sources: [],
          timestamp: new Date().toISOString()
        })
      );
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText("我在。")).toBeInTheDocument();
  });

  it("shows an interim placeholder after three seconds and removes it after the official reply", async () => {
    vi.useFakeTimers();
    vi.spyOn(Math, "random").mockReturnValue(0);
    let resolveChat: (value: Response) => void = () => {};
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return Promise.resolve(debugAction);
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return Promise.resolve(pendingResponse);
        const settings = settingsResponse(url, init);
        if (settings) return Promise.resolve(settings);
        if (url.endsWith("/api/health")) return Promise.resolve(Response.json({ status: "ok" }));
        if (url.endsWith("/api/game/status")) return Promise.resolve(Response.json(runningStatus));
        if (url.endsWith("/api/memory/profile")) return Promise.resolve(Response.json(memoryProfile));
        if (url.includes("/api/debug/memory")) return Promise.resolve(Response.json(memoryDebug));
        if (url.endsWith("/api/debug/chat")) return Promise.resolve(Response.json(chatDebug));
        if (url.endsWith("/api/debug/game-session")) return Promise.resolve(Response.json(gameSessionDebug));
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Promise.resolve(Response.json(semanticExtractionDebug));
        if (url.includes("/api/debug/prompt-preview")) return Promise.resolve(Response.json(promptPreview));
        if (url.endsWith("/api/chat") && init?.method === "POST") {
          return new Promise<Response>((resolve) => {
            resolveChat = resolve;
          });
        }
        return Promise.resolve(new Response("missing", { status: 404 }));
      })
    );
    render(<App />);
    fireEvent.change(screen.getByLabelText("聊天输入"), { target: { value: "你好" } });
    fireEvent.click(screen.getByRole("button", { name: /发送/i }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(screen.getByText("……")).toBeInTheDocument();
    await act(async () => {
      resolveChat(
        Response.json({
          reply: "我在。",
          reply_segments: ["我在。"],
          segmenter_mode: "compact",
          persona_id: "rei_like",
          game_status: "running",
          sources: [],
          timestamp: new Date().toISOString()
        })
      );
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText("我在。")).toBeInTheDocument();
    expect(screen.queryByText("……")).not.toBeInTheDocument();
  });

  it("uses only neutral low-semantic interim placeholders", () => {
    expect(INTERIM_PLACEHOLDERS).toEqual(["……", "……嗯", "嗯……"]);
    expect(INTERIM_PLACEHOLDERS).not.toContain("我听见了。");
    expect(INTERIM_PLACEHOLDERS).not.toContain("等一下。");
    expect(INTERIM_PLACEHOLDERS).not.toContain("别急。");
  });

  it("renders reply segments with staggered timing", async () => {
    vi.useFakeTimers();
    vi.spyOn(Math, "random").mockReturnValue(0);
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return Promise.resolve(debugAction);
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return Promise.resolve(pendingResponse);
        const settings = settingsResponse(url, init);
        if (settings) return Promise.resolve(settings);
        if (url.endsWith("/api/health")) return Promise.resolve(Response.json({ status: "ok" }));
        if (url.endsWith("/api/game/status")) return Promise.resolve(Response.json(runningStatus));
        if (url.endsWith("/api/memory/profile")) return Promise.resolve(Response.json(memoryProfile));
        if (url.includes("/api/debug/memory")) return Promise.resolve(Response.json(memoryDebug));
        if (url.endsWith("/api/debug/chat")) return Promise.resolve(Response.json({ ...chatDebug, reply_segments_count: 3, segmenter_mode: "strategy" }));
        if (url.endsWith("/api/debug/game-session")) return Promise.resolve(Response.json(gameSessionDebug));
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Promise.resolve(Response.json(semanticExtractionDebug));
        if (url.includes("/api/debug/prompt-preview")) return Promise.resolve(Response.json(promptPreview));
        if (url.endsWith("/api/chat") && init?.method === "POST") {
          return Promise.resolve(
            Response.json({
              reply: "别急。少打一刀。先活下来。",
              reply_segments: ["别急。", "少打一刀。", "先活下来。"],
              segmenter_mode: "strategy",
              persona_id: "rei_like",
              game_status: "running",
              sources: [],
              timestamp: new Date().toISOString()
            })
          );
        }
        return Promise.resolve(new Response("missing", { status: 404 }));
      })
    );
    render(<App />);
    fireEvent.change(screen.getByLabelText("聊天输入"), { target: { value: "Margit 怎么打" } });
    fireEvent.click(screen.getByRole("button", { name: /发送/i }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByText("别急。")).toBeInTheDocument();
    expect(screen.queryByText("少打一刀。")).not.toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(screen.getByText("少打一刀。")).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(screen.getByText("先活下来。")).toBeInTheDocument();
  });

  it("shows disconnected state when backend fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("offline", { status: 500 })));
    render(<App />);
    await screen.findByText("未连接");
  });

  it("toggles debug panel", async () => {
    render(<App />);

    await screen.findByText("Game Session");
    expect(screen.getByText("current_game")).toBeInTheDocument();
    expect(screen.getByText("current_boss")).toBeInTheDocument();
    expect(screen.getByText("freshness")).toBeInTheDocument();
    expect(screen.getByText("last_attempted")).toBeInTheDocument();
    expect(screen.getByText("last_cleared")).toBeInTheDocument();
    expect(screen.queryByText("Semantic Extraction")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Debug Panel/i }));
    await waitFor(() => expect(screen.getByText("Semantic Extraction")).toBeInTheDocument());
    expect(screen.getByText("Semantic Extraction")).toBeInTheDocument();
    expect(screen.getByText("llm_called")).toBeInTheDocument();
    expect(screen.getAllByText("guide_preference").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Prompt Preview/i })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Prompt Preview/i }));
    await waitFor(() => expect(screen.getByText("persona_mode")).toBeInTheDocument());
    expect(screen.getByText("persona_mode")).toBeInTheDocument();
    expect(screen.getByText("prompt_order")).toBeInTheDocument();
    expect(screen.getByText("current_user_message")).toBeInTheDocument();
    expect(screen.getByText("session_focus")).toBeInTheDocument();
    expect(screen.getByText("game_state")).toBeInTheDocument();
    expect(screen.getByText("Memory injected")).toBeInTheDocument();
    expect(screen.getByText("Memory skipped")).toBeInTheDocument();
    expect(screen.getByText("Pending Memory")).toBeInTheDocument();
    expect(screen.getByText("玩家不喜欢长篇攻略")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ignore" })).toBeInTheDocument();
    expect(screen.getByText("Warnings")).toBeInTheDocument();
    expect(screen.getByText("Raw JSON")).toBeInTheDocument();
    expect(screen.getByText("Raw JSON").closest("details")).not.toHaveAttribute("open");
    await userEvent.click(screen.getByRole("button", { name: /Debug Panel/i }));
    await waitFor(() => expect(screen.queryByText("Semantic Extraction")).not.toBeInTheDocument());
  });

  it("falls back to game session debug data and shows empty warnings as none", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return debugAction;
        const pendingResponse = pendingMemoryResponse(url, init);
        if (pendingResponse) return pendingResponse;
        const settings = settingsResponse(url, init);
        if (settings) return settings;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json(runningStatus);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(chatDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json(gameSessionDebug);
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Response.json(semanticExtractionDebug);
        if (url.includes("/api/debug/prompt-preview")) {
          return Response.json({
            ...promptPreview,
            game_state_summary: {},
            memory_summary: { injected: [], skipped: [] },
            warnings: []
          });
        }
        return new Response("missing", { status: 404 });
      })
    );

    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /Prompt Preview/i }));

    const gameStateSection = screen.getByText("game_state").closest("section");
    expect(gameStateSection).not.toBeNull();
    expect(gameStateSection?.textContent).toContain("恶兆妖鬼 Margit");
    expect(gameStateSection?.textContent).toContain("boss_attempt");

    const warningsSection = screen.getByText("Warnings").closest(".debugSubgroup");
    expect(warningsSection).not.toBeNull();
    expect(within(warningsSection as HTMLElement).getByText("无")).toBeInTheDocument();
  });

  it("accepts pending memory from the debug panel", async () => {
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Accept" }));

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/memory/pending/pending-1/accept"),
        expect.objectContaining({ method: "POST" })
      )
    );
  });

  it("shows empty pending memory state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const debugAction = debugActionResponse(url, init);
        if (debugAction) return debugAction;
        if (url.endsWith("/api/memory/pending")) return Response.json([]);
        const settings = settingsResponse(url, init);
        if (settings) return settings;
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json(runningStatus);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(chatDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json(gameSessionDebug);
        if (url.endsWith("/api/debug/semantic-extraction/latest")) return Response.json(semanticExtractionDebug);
        if (url.includes("/api/debug/prompt-preview")) return Response.json(promptPreview);
        return new Response("missing", { status: 404 });
      })
    );

    render(<App />);
    expect(await screen.findByText("暂无待确认记忆")).toBeInTheDocument();
  });

  it("calls debug reset and clear endpoints", async () => {
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /Debug Panel/i }));

    await userEvent.click(await screen.findByRole("button", { name: "Reset Game Session" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/debug/game-session/reset"),
        expect.objectContaining({ method: "POST" })
      )
    );

    await userEvent.click(screen.getByRole("button", { name: "Reset Memory" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/memory/reset"),
        expect.objectContaining({ method: "POST" })
      )
    );

    await userEvent.click(screen.getByRole("button", { name: "Clear Pending Memory" }));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/memory/pending/clear"),
        expect.objectContaining({ method: "POST" })
      )
    );
  });
});
