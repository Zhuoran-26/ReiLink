import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TranscriptDraft } from "../components/voice/TranscriptDraft";
import { VoiceConversation } from "../components/voice/VoiceConversation";
import { VoiceModeCard } from "../components/voice/VoiceModeCard";
import { VoiceState, voiceExperienceCopy } from "../components/voice/VoiceState";
import { voiceConversationSnapshot, type VoiceConversationState } from "../voiceState";

describe("Voice experience presentation", () => {
  it("maps internal Voice states to restrained player-facing copy", () => {
    const expected: Record<VoiceConversationState, string> = {
      idle: "Rei 等待着",
      listening: "Rei 正在听...",
      transcribing: "声音正在留下来...",
      auto_sending: "这句话正在送给 Rei...",
      ready_to_send: "声音已经留下来。",
      assistant_thinking: "Rei 想了一下...",
      speaking: "Rei 正在回应...",
      interrupted: "声音停下来了。",
      error: "这次没有听清。"
    };

    for (const [state, title] of Object.entries(expected) as [VoiceConversationState, string][]) {
      expect(voiceExperienceCopy(voiceConversationSnapshot(state)).title).toBe(title);
    }
  });

  it("gives the quiet Voice Orb a state-aware Rei presence", () => {
    const { rerender } = render(<VoiceState snapshot={voiceConversationSnapshot("listening")} />);
    expect(screen.getByRole("status", { name: "Voice v2.2 状态" })).toHaveTextContent(
      "Rei 正在听...说完后停下来，声音会先留成草稿。"
    );
    expect(document.querySelector(".voiceOrb-listening .reiAvatar-listening")).toBeInTheDocument();

    rerender(<VoiceState snapshot={voiceConversationSnapshot("assistant_thinking")} />);
    expect(screen.getByRole("status", { name: "Voice v2.2 状态" })).toHaveTextContent("Rei 想了一下...");
    expect(document.querySelector(".voiceOrb-assistant_thinking .reiAvatar-thinking")).toBeInTheDocument();

    rerender(<VoiceState snapshot={voiceConversationSnapshot("speaking")} />);
    expect(screen.getByRole("status", { name: "Voice v2.2 状态" })).toHaveTextContent("Rei 正在回应...");
    expect(document.querySelector(".voiceOrb-speaking .reiAvatar-speaking")).toBeInTheDocument();
  });

  it("keeps Direct Conversation opt-in explicit while using player-facing language", async () => {
    const onChange = vi.fn();
    render(<VoiceModeCard busy={false} mode="confirm_send" onChange={onChange} />);

    const mode = screen.getByRole("group", { name: "直接对话模式" });
    expect(within(mode).getByRole("button", { name: "确认后发送" })).toHaveAttribute("aria-pressed", "true");
    expect(within(mode).getByRole("button", { name: "自动发送（安全模式）" })).toHaveAttribute("aria-pressed", "false");
    expect(mode).toHaveTextContent("转写先留在草稿里，由你确认");

    await userEvent.click(within(mode).getByRole("button", { name: "自动发送（安全模式）" }));
    expect(onChange).toHaveBeenCalledWith("direct_conversation");
  });

  it("keeps the transcript editable, restartable, and explicitly unsent", async () => {
    const onChange = vi.fn();
    const onRestart = vi.fn();
    const onSubmit = vi.fn((event: React.FormEvent<HTMLFormElement>) => event.preventDefault());
    render(
      <TranscriptDraft
        busy={false}
        hint="12 字转写草稿已在输入框，尚未发送。"
        onChange={onChange}
        onRestart={onRestart}
        onSubmit={onSubmit}
        ready
        value="我刚刚走到了城门前。"
      />
    );

    const draft = screen.getByLabelText("转写草稿");
    expect(draft).toHaveValue("我刚刚走到了城门前。");
    expect(screen.getByText("尚未发送 · 可以编辑")).toBeInTheDocument();
    fireEvent.change(draft, { target: { value: "我走到了城门。" } });
    expect(onChange).toHaveBeenCalledOnce();
    await userEvent.click(screen.getByRole("button", { name: "重新录音" }));
    await userEvent.click(screen.getByRole("button", { name: "发送给 Rei" }));
    expect(onRestart).toHaveBeenCalledOnce();
    expect(onSubmit).toHaveBeenCalledOnce();
  });

  it("reuses the existing recording and speaking callbacks", async () => {
    const onRecord = vi.fn();
    const onStopSpeaking = vi.fn();
    render(
      <VoiceConversation
        draftHint=""
        draftReady={false}
        draftValue=""
        mode="confirm_send"
        modeBusy={false}
        onDraftChange={() => undefined}
        onModeChange={() => undefined}
        onRecord={onRecord}
        onRestart={() => undefined}
        onStopSpeaking={onStopSpeaking}
        onSubmit={(event) => event.preventDefault()}
        recordActive={false}
        recordDisabled={false}
        recordLabel="开始本地语音 / Start Local ASR"
        recordTitle="开始本地语音"
        sending={false}
        speaking
        state={voiceConversationSnapshot("speaking")}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "开始本地语音 / Start Local ASR" }));
    await userEvent.click(screen.getByRole("button", { name: "停止语音 / Stop Voice" }));
    expect(onRecord).toHaveBeenCalledOnce();
    expect(onStopSpeaking).toHaveBeenCalledOnce();
  });
});
