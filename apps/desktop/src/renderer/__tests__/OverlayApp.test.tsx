import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OverlayApp } from "../OverlayApp";

describe("OverlayApp", () => {
  it("renders only the lightweight overlay bubble surface", async () => {
    render(<OverlayApp />);

    expect(screen.getByLabelText("Rei 游戏悬浮层")).toBeInTheDocument();
    expect(await screen.findByText("Rei 正安静待机。")).toBeInTheDocument();
    expect(screen.queryByLabelText("聊天输入")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Overlay / 游戏悬浮层")).not.toBeInTheDocument();
    expect(screen.queryByText("聊天")).not.toBeInTheDocument();
    expect(screen.queryByText("设置")).not.toBeInTheDocument();
    expect(screen.queryByText("调试")).not.toBeInTheDocument();
  });
});
