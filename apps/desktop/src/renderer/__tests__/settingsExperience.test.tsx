import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AppSettings } from "../../shared/api";
import { SettingsExperience } from "../components/settings/SettingsExperience";

const settings: AppSettings = {
  persona_mode: "minimal",
  debug_panel: "show",
  memory_enabled: true,
  pending_memory_mode: "manual",
  response_length: "short",
  model_preference: "auto",
  proactive_companion: "off",
  proactive_sensitivity: "low",
  auto_game_detection: "on",
  overlay_enabled: "off",
  overlay_position: "top-right",
  overlay_opacity: 0.72,
  overlay_message_count: 2,
  voice_interaction_mode: "confirm_send",
  voice_profile_id: "rei_calm",
  voice_spoken_reply_mode: "brief",
  voice_direct_spoken_reply_mode: "brief",
  voice_speak_proactive: false,
  voice_speak_memory_prompts: false,
  voice_max_spoken_chars: 120,
  voice_max_spoken_sentences: 2,
  voice_output: "on",
  voice_rate: 1,
  voice_volume: 0.8,
  onboarding_completed: true,
  onboarding_last_seen_at: null
};

function renderSettings(theme: "light" | "dark" = "light") {
  const actions = {
    onOpenDeveloper: vi.fn(),
    onOpenLocalData: vi.fn(),
    onOpenMoreSettings: vi.fn(),
    onOpenVoice: vi.fn(),
    onToggleTheme: vi.fn()
  };

  render(
    <SettingsExperience
      {...actions}
      theme={theme}
      voiceInteractionMode={settings.voice_interaction_mode}
      voiceOutputEnabled={settings.voice_output === "on"}
    />
  );
  return actions;
}

describe("SettingsExperience", () => {
  it("presents the calm companion settings sections without fake memory controls", () => {
    renderSettings();

    expect(screen.getByRole("region", { name: "陪伴设置" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "调整 Rei 陪伴你的方式。" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Rei" })).toBeInTheDocument();
    expect(screen.getByText("安静、克制，保持一点距离。")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "语音" })).toBeInTheDocument();
    expect(screen.getByText("确认后发送")).toBeInTheDocument();
    expect(screen.getByText("已开启")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Rei 的日记" })).toBeInTheDocument();
    expect(screen.getByText("未来这里可以查看 Rei 记录下的旅程。")).toBeInTheDocument();
    expect(screen.getByText("尚未开放")).toBeInTheDocument();
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "隐私" })).toBeInTheDocument();
    expect(screen.getByText("你的旅程数据保存在本地。")).toBeInTheDocument();
    expect(screen.getByText("ReiLink 不会上传本地记录。")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "系统" })).toBeInTheDocument();
  });

  it("routes to existing settings surfaces and only toggles when the selected theme changes", () => {
    const actions = renderSettings("light");

    fireEvent.click(screen.getByRole("button", { name: "管理语音设置" }));
    fireEvent.click(screen.getByRole("button", { name: "管理本地数据" }));
    fireEvent.click(screen.getByRole("button", { name: "打开开发者工具" }));
    fireEvent.click(screen.getByRole("button", { name: "更多设置" }));
    expect(actions.onOpenVoice).toHaveBeenCalledOnce();
    expect(actions.onOpenLocalData).toHaveBeenCalledOnce();
    expect(actions.onOpenDeveloper).toHaveBeenCalledOnce();
    expect(actions.onOpenMoreSettings).toHaveBeenCalledOnce();

    fireEvent.click(screen.getByRole("button", { name: "使用日间主题" }));
    expect(actions.onToggleTheme).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "使用夜间主题" }));
    expect(actions.onToggleTheme).toHaveBeenCalledOnce();
  });
});
