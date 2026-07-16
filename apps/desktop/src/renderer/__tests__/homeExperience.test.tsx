import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type {
  GameContextResponse,
  GameSessionDebugResponse,
  GameStatus,
  SessionArchiveSummary
} from "../../shared/api";
import { HomeExperience } from "../components/home/HomeExperience";
import { buildHomeJourneyViewModel } from "../components/home/homeViewModel";
import type { SessionTimelineItem } from "../sessionTimeline";

const idleStatus: GameStatus = {
  game_id: null,
  game_name: null,
  process_name: null,
  status: "idle",
  confidence: 0,
  tags: []
};

const emptyContext: GameContextResponse = {
  active_game_id: null,
  active_game_display_name: null,
  active_source: "none",
  manual_override: { enabled: false, game_id: null, display_name: null, set_at: null, source: "user" },
  detected_game: {
    status: "idle",
    detected_game_id: null,
    display_name: null,
    process_name: null,
    match_confidence: 0,
    match_source: "none",
    knowledge_game_id: null,
    detected_at: "2026-07-15T00:00:00.000Z"
  },
  session_game: null,
  previous_game: null,
  game_switched: false,
  user_message_game_id: null,
  user_message_game_display_name: null,
  support_status: null,
  knowledge_available: false,
  fallback_reason: "no_game_detected",
  warnings: [],
  available_games: []
};

const emptySession: GameSessionDebugResponse = {
  current_game: null,
  current_boss: null,
  discussion_target: null,
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
};

const archive = (patch: Partial<SessionArchiveSummary> = {}): SessionArchiveSummary => ({
  id: "archive-1",
  session_id: "default",
  title: "Elden Ring / 史东薇尔城",
  created_at: "2026-07-15T10:00:00.000Z",
  updated_at: "2026-07-15T10:00:00.000Z",
  started_at: "2026-07-15T09:00:00.000Z",
  ended_at: "2026-07-15T10:00:00.000Z",
  source: "session_timeline",
  game: "Elden Ring",
  area: "史东薇尔城附近",
  boss: null,
  summary: "你在史东薇尔城入口停了下来。",
  event_count: 1,
  safe_event_summaries: ["你在史东薇尔城入口停了下来。"],
  memory_candidate_count: 0,
  accepted_memory_count: 0,
  privacy_level: "normal",
  retention_policy: "manual_latest_20",
  is_deleted: false,
  deletion_status: "active",
  ...patch
});

const withGame = (name = "Elden Ring"): GameContextResponse => ({
  ...emptyContext,
  active_game_id: "elden-ring",
  active_game_display_name: name,
  active_source: "session",
  session_game: name,
  support_status: "supported",
  knowledge_available: true,
  fallback_reason: null
});

const timeline = (patch: Partial<SessionTimelineItem> = {}): SessionTimelineItem => ({
  id: "timeline-1",
  timestamp: "2026-07-15T10:00:00.000Z",
  type: "boss_detected",
  source: "game_session",
  summary: "检测到 Boss：恶兆妖鬼 Margit",
  ...patch
});

const buildModel = (patch: Partial<Parameters<typeof buildHomeJourneyViewModel>[0]> = {}) =>
  buildHomeJourneyViewModel({
    archives: [],
    gameContext: emptyContext,
    gameSession: emptySession,
    gameStatus: idleStatus,
    now: new Date("2026-07-16T12:00:00.000Z"),
    timeline: [],
    ...patch
  });

const renderHome = (model = buildModel()) => {
  const callbacks = {
    onOpenChat: vi.fn(),
    onOpenJourney: vi.fn(),
    onOpenVoice: vi.fn()
  };
  render(<HomeExperience model={model} {...callbacks} />);
  return callbacks;
};

describe("Home Experience", () => {
  it("renders a restrained empty journey state without placeholder data", () => {
    renderHome();

    expect(screen.getByRole("heading", { name: "欢迎回来。" })).toBeInTheDocument();
    expect(screen.getByText("这里还很安静。")).toBeInTheDocument();
    expect(screen.getByText("等你准备好，我们可以从一段新的旅程开始。")).toBeInTheDocument();
    expect(screen.queryByText(/undefined|null|未知地点/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "当前旅程" })).not.toBeInTheDocument();
  });

  it("shows a game without inventing a missing location", () => {
    renderHome(buildModel({ gameContext: withGame() }));

    expect(screen.getByRole("heading", { name: "Elden Ring" })).toBeInTheDocument();
    expect(screen.getByText("Elden Ring 的旅程还在继续。")).toBeInTheDocument();
    expect(screen.queryByText(/未知地点|暂无位置|undefined|null/i)).not.toBeInTheDocument();
  });

  it("does not borrow a location from an archive without a matching game", () => {
    renderHome(buildModel({
      archives: [archive({ game: null, area: "不属于当前旅程的地点" })],
      gameContext: withGame()
    }));

    expect(screen.getByRole("heading", { name: "Elden Ring" })).toBeInTheDocument();
    expect(screen.queryByText("不属于当前旅程的地点")).not.toBeInTheDocument();
  });

  it("renders the complete current journey from matching existing archive data", () => {
    const model = buildModel({
      archives: [archive()],
      gameContext: withGame(),
      gameSession: { ...emptySession, current_game: "Elden Ring", last_updated_at: "2026-07-15T10:00:00.000Z" }
    });
    renderHome(model);

    const currentJourney = screen.getByRole("article", { name: "Elden Ring" });
    expect(currentJourney).toHaveTextContent("当前旅程");
    expect(currentJourney).toHaveTextContent("史东薇尔城附近");
    expect(currentJourney).toHaveTextContent("昨天");
    expect(screen.getByText("我们上次停在史东薇尔城附近。")).toBeInTheDocument();
  });

  it("shows only the latest timeline item as the recent fragment", () => {
    renderHome(buildModel({
      gameContext: withGame(),
      timeline: [
        timeline({ id: "old", type: "game_selected", summary: "切换游戏：Elden Ring" }),
        timeline({ id: "latest", type: "boss_cleared", summary: "击败 Boss：恶兆妖鬼 Margit" })
      ]
    }));

    const recent = screen.getByRole("region", { name: "最近的片段" });
    expect(recent).toHaveTextContent("你已经越过了恶兆妖鬼 Margit。");
    expect(recent).not.toHaveTextContent("重新翻开");
  });

  it("keeps the missing-fragment state as a single low-weight note", () => {
    renderHome(buildModel({ gameContext: withGame() }));

    const recent = screen.getByRole("region", { name: "最近的片段" });
    expect(recent).toHaveClass("homeRecentFragment-empty");
    expect(recent).toHaveTextContent("新的旅程还没有留下太多痕迹。");
    expect(recent).not.toHaveClass("uiCard");
  });

  it("safely truncates unusually long mixed-language journey data", () => {
    const longGame = `旅程-${"Elden Ring 与史东薇尔城".repeat(20)}`;
    const longLocation = `区域-${"城墙入口 mixed text".repeat(20)}`;
    const model = buildModel({
      archives: [archive({ game: longGame, area: longLocation })],
      gameContext: withGame(longGame)
    });
    renderHome(model);

    const journeyTitle = screen.getByRole("heading", { level: 2, name: /旅程-/ });
    expect(journeyTitle.textContent?.length).toBeLessThanOrEqual(100);
    expect(journeyTitle).toHaveAttribute("title", journeyTitle.textContent);
    expect(screen.queryByText(/undefined|null/i)).not.toBeInTheDocument();
  });

  it("routes Continue and quick actions through the supplied navigation callbacks", async () => {
    const callbacks = renderHome(buildModel({ gameContext: withGame() }));

    await userEvent.click(screen.getByRole("button", { name: "继续陪伴" }));
    await userEvent.click(screen.getByRole("button", { name: "语音陪伴" }));
    const quickActions = screen.getByRole("navigation", { name: "首页快捷入口" });
    await userEvent.click(within(quickActions).getByRole("button", { name: "查看旅程" }));
    expect(callbacks.onOpenChat).toHaveBeenCalledOnce();
    expect(callbacks.onOpenVoice).toHaveBeenCalledOnce();
    expect(callbacks.onOpenJourney).toHaveBeenCalledOnce();
  });

  it("keeps Home content understandable when reduced motion is preferred", () => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: true }));
    renderHome(buildModel({ archives: [archive()], gameContext: withGame() }));

    expect(screen.getByRole("heading", { name: "欢迎回来。" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Elden Ring" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "首页快捷入口" })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
