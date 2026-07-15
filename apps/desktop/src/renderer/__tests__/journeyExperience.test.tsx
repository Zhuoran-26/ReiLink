import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { JourneyGameSelector } from "../components/journey/JourneyGameSelector";
import { JourneyOverview } from "../components/journey/JourneyOverview";
import { JourneyReference } from "../components/journey/JourneyReference";
import { JourneyTimeline } from "../components/journey/JourneyTimeline";
import type { SessionTimelineItem } from "../sessionTimeline";

describe("Journey experience presentation", () => {
  it("renders current game state as a personal journey instead of debug facts", () => {
    render(
      <JourneyOverview
        activity="挑战中"
        challengeName="恶兆妖鬼 Margit"
        gameName="艾尔登法环"
        history={[{ name: "恶兆妖鬼 Margit", status: "当前挑战" }]}
        lastAttempted="恶兆妖鬼 Margit"
        lastCleared={null}
        retryCount={2}
      />
    );

    const journey = screen.getByRole("region", { name: "当前旅程" });
    expect(journey).toHaveTextContent("艾尔登法环");
    expect(journey).toHaveTextContent("正在面对恶兆妖鬼 Margit挑战中");
    expect(journey).toHaveTextContent("记录了 2 次重新尝试");
    expect(journey).not.toHaveTextContent("current_game");
    expect(journey).not.toHaveTextContent("canonical");
  });

  it("shows a restrained empty journey state", () => {
    render(
      <JourneyOverview
        activity=""
        challengeName={null}
        gameName={null}
        history={[]}
        lastAttempted={null}
        lastCleared={null}
        retryCount={0}
      />
    );

    expect(screen.getByRole("region", { name: "空白旅程" })).toHaveTextContent(
      "还没有开始一段旅程。等新的脚步出现，这里会慢慢留下记录。"
    );
  });

  it("turns safe session timeline fields into player-facing journey records", async () => {
    const items: SessionTimelineItem[] = [
      {
        id: "boss",
        timestamp: "2026-07-15T13:04:00.000Z",
        type: "boss_detected",
        source: "game_session",
        summary: "检测到 Boss：恶兆妖鬼 Margit"
      },
      {
        id: "retry",
        timestamp: "2026-07-15T13:12:00.000Z",
        type: "death_count_changed",
        source: "game_session",
        summary: "死亡次数更新：1"
      }
    ];
    const onClear = vi.fn();
    render(<JourneyTimeline items={items} onClear={onClear} />);

    const timeline = screen.getByRole("region", { name: "最近记录" });
    expect(timeline).toHaveTextContent("正在面对恶兆妖鬼 Margit");
    expect(timeline).toHaveTextContent("再次尝试本局第 1 次重新出发");
    expect(timeline).not.toHaveTextContent("死亡次数更新");
    await userEvent.click(screen.getByRole("button", { name: "清空本局记录" }));
    expect(onClear).toHaveBeenCalledOnce();
  });

  it("keeps journey reference language outside developer terminology", () => {
    render(<JourneyReference available gameName="艾尔登法环" usedRecently />);

    const reference = screen.getByRole("region", { name: "旅程参考" });
    expect(reference).toHaveTextContent("已有资料可以参考");
    expect(reference).toHaveTextContent("Rei 参考了相关资料");
    expect(reference).not.toHaveTextContent("retrieval");
    expect(reference).not.toHaveTextContent("fallback");
  });

  it("preserves game selection callbacks with player-facing labels", async () => {
    const onSelect = vi.fn();
    const onUseDetected = vi.fn();
    const onClearManual = vi.fn();
    render(
      <JourneyGameSelector
        busy={false}
        canUseDetectedGame
        detectedGameName="艾尔登法环"
        manualEnabled
        onClearManual={onClearManual}
        onSelect={onSelect}
        onUseDetected={onUseDetected}
        options={[
          {
            game_id: "elden_ring",
            display_name: "艾尔登法环",
            enabled: true,
            knowledge_available: true,
            support_status: "supported",
            knowledge_game_id: "elden_ring",
            manifest_path: null,
            knowledge_path: null
          }
        ]}
        selectedGameId=""
      />
    );

    fireEvent.change(screen.getByLabelText("当前游戏"), { target: { value: "elden_ring" } });
    expect(onSelect).toHaveBeenCalledOnce();
    await userEvent.click(screen.getByRole("button", { name: "使用检测结果" }));
    await userEvent.click(screen.getByRole("button", { name: "清除手动选择" }));
    expect(onUseDetected).toHaveBeenCalledOnce();
    expect(onClearManual).toHaveBeenCalledOnce();
  });
});
