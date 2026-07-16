import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppNavigation } from "../app/AppNavigation";
import { ReiAvatar } from "../components/rei/ReiAvatar";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Card, Surface } from "../components/ui/Surface";
import { StatusIndicator } from "../components/ui/StatusIndicator";

describe("UI visual foundation", () => {
  it("renders reusable primitives with semantic variants", () => {
    render(
      <Surface aria-label="基础表面" level="base">
        <Card aria-label="抬升卡片">
          <Input aria-label="示例输入" placeholder="说点什么……" />
          <Button variant="primary">继续</Button>
          <StatusIndicator label="已连接" tone="success" />
          <ReiAvatar label="Rei 正在思考" state="thinking" />
        </Card>
      </Surface>
    );

    expect(screen.getByLabelText("基础表面")).toHaveAttribute("data-surface-level", "base");
    expect(screen.getByLabelText("抬升卡片")).toHaveAttribute("data-surface-level", "raised");
    expect(screen.getByRole("button", { name: "继续" })).toHaveClass("uiButton-primary");
    expect(screen.getByLabelText("示例输入")).toHaveClass("uiInput");
    expect(screen.getByText("已连接").closest(".uiStatus")).toHaveClass("uiStatus-success");
    expect(screen.getByRole("img", { name: "Rei 正在思考" })).toHaveAttribute("data-presence-state", "thinking");
  });

  it("keeps developer workspaces collapsed until explicitly requested", async () => {
    const openWorkspace = vi.fn();
    const toggleTheme = vi.fn();
    render(
      <AppNavigation
        activeWorkspace="home"
        backendStatus="connected"
        companionName="Rei"
        companionStatus="在线"
        presenceState="idle"
        theme="light"
        onOpenWorkspace={openWorkspace}
        onToggleTheme={toggleTheme}
      />
    );

    const navigation = screen.getByRole("navigation", { name: "应用导航" });
    expect(within(navigation).getByRole("button", { name: "首页" })).toHaveAttribute("aria-current", "page");
    expect(within(navigation).getByRole("button", { name: "聊天" })).not.toHaveAttribute("aria-current");
    expect(within(navigation).queryByRole("button", { name: "调试" })).not.toBeInTheDocument();

    await userEvent.click(within(navigation).getByRole("button", { name: "开发者工具" }));
    expect(within(navigation).getByRole("button", { name: "调试" })).toBeInTheDocument();
    await userEvent.click(within(navigation).getByRole("button", { name: "调试" }));
    expect(openWorkspace).toHaveBeenCalledWith("debug");

    await userEvent.click(screen.getByRole("button", { name: "切换到夜间" }));
    expect(toggleTheme).toHaveBeenCalledOnce();
  });
});
