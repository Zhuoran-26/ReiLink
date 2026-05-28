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
    vi.stubGlobal("crypto", { randomUUID: () => `test-id-${uuid++}` });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json(runningStatus);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(chatDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json(gameSessionDebug);
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

  it("shows running game status", async () => {
    render(<App />);
    await screen.findByText("艾尔登法环：运行中");
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
        if (url.endsWith("/api/health")) return Promise.resolve(Response.json({ status: "ok" }));
        if (url.endsWith("/api/game/status")) return Promise.resolve(Response.json(runningStatus));
        if (url.endsWith("/api/memory/profile")) return Promise.resolve(Response.json(memoryProfile));
        if (url.includes("/api/debug/memory")) return Promise.resolve(Response.json(memoryDebug));
        if (url.endsWith("/api/debug/chat")) return Promise.resolve(Response.json(chatDebug));
        if (url.endsWith("/api/debug/game-session")) return Promise.resolve(Response.json(gameSessionDebug));
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
        if (url.endsWith("/api/health")) return Promise.resolve(Response.json({ status: "ok" }));
        if (url.endsWith("/api/game/status")) return Promise.resolve(Response.json(runningStatus));
        if (url.endsWith("/api/memory/profile")) return Promise.resolve(Response.json(memoryProfile));
        if (url.includes("/api/debug/memory")) return Promise.resolve(Response.json(memoryDebug));
        if (url.endsWith("/api/debug/chat")) return Promise.resolve(Response.json(chatDebug));
        if (url.endsWith("/api/debug/game-session")) return Promise.resolve(Response.json(gameSessionDebug));
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
        if (url.endsWith("/api/health")) return Promise.resolve(Response.json({ status: "ok" }));
        if (url.endsWith("/api/game/status")) return Promise.resolve(Response.json(runningStatus));
        if (url.endsWith("/api/memory/profile")) return Promise.resolve(Response.json(memoryProfile));
        if (url.includes("/api/debug/memory")) return Promise.resolve(Response.json(memoryDebug));
        if (url.endsWith("/api/debug/chat")) return Promise.resolve(Response.json({ ...chatDebug, reply_segments_count: 3, segmenter_mode: "strategy" }));
        if (url.endsWith("/api/debug/game-session")) return Promise.resolve(Response.json(gameSessionDebug));
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
    await userEvent.click(screen.getByRole("button", { name: /调试/i }));
    await waitFor(() => expect(screen.getByText(/personaId/)).toBeInTheDocument());
    expect(screen.getAllByText(/current_boss/).length).toBeGreaterThan(0);
    expect(screen.getByText(/memory_provenance/)).toBeInTheDocument();
    expect(screen.getByText(/game_session/)).toBeInTheDocument();
    expect(screen.getByText("Prompt Preview")).toBeInTheDocument();
    expect(screen.getByText("Persona mode")).toBeInTheDocument();
    expect(screen.getByText("Prompt order")).toBeInTheDocument();
    expect(screen.getByText("Current user message")).toBeInTheDocument();
    expect(screen.getByText("Session Focus")).toBeInTheDocument();
    expect(screen.getByText("Game State Summary")).toBeInTheDocument();
    expect(screen.getByText("Memory Injected")).toBeInTheDocument();
    expect(screen.getByText("Memory Skipped")).toBeInTheDocument();
    expect(screen.getByText("Warnings")).toBeInTheDocument();
    expect(screen.queryByText(/prompt_preview/)).not.toBeInTheDocument();
    expect(screen.getByText(/selected_model/)).toBeInTheDocument();
    expect(screen.getByText(/reply_segments_count/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /调试/i }));
    await waitFor(() => expect(screen.queryByText(/personaId/)).not.toBeInTheDocument());
  });

  it("falls back to game session debug data and shows empty warnings as none", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith("/api/health")) return Response.json({ status: "ok" });
        if (url.endsWith("/api/game/status")) return Response.json(runningStatus);
        if (url.endsWith("/api/memory/profile")) return Response.json(memoryProfile);
        if (url.includes("/api/debug/memory")) return Response.json(memoryDebug);
        if (url.endsWith("/api/debug/chat")) return Response.json(chatDebug);
        if (url.endsWith("/api/debug/game-session")) return Response.json(gameSessionDebug);
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
    await userEvent.click(screen.getByRole("button", { name: /调试/i }));

    const gameStateSection = screen.getByText("Game State Summary").closest("section");
    expect(gameStateSection).not.toBeNull();
    expect(within(gameStateSection as HTMLElement).getAllByText("恶兆妖鬼 Margit").length).toBeGreaterThan(0);
    expect(within(gameStateSection as HTMLElement).getByText("boss_attempt")).toBeInTheDocument();

    const warningsSection = screen.getByText("Warnings").closest("section");
    expect(warningsSection).not.toBeNull();
    expect(within(warningsSection as HTMLElement).getByText("无")).toBeInTheDocument();
  });
});
