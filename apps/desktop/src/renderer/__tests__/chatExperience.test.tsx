import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatComposer } from "../components/chat/ChatComposer";
import { ChatMessage } from "../components/chat/ChatMessage";
import { EmptyConversation } from "../components/chat/EmptyConversation";

describe("Chat experience presentation", () => {
  it("renders Rei and user messages with distinct companion states", () => {
    const { rerender } = render(
      <ChatMessage meta="今天 21:43" reiState="speaking" role="assistant" text="好。慢慢来。" />
    );

    expect(screen.getByText("Rei")).toBeInTheDocument();
    expect(screen.getByText("好。慢慢来。")).toBeInTheDocument();
    expect(document.querySelector(".reiAvatar-speaking")).toBeInTheDocument();

    rerender(<ChatMessage meta="今天 21:42" role="user" text="今晚想继续走一段。" />);
    expect(screen.getByText("你")).toBeInTheDocument();
    expect(screen.getByText("今晚想继续走一段。").closest("article")).toHaveClass("messageBubble", "user");
  });

  it("shows a restrained empty conversation state", () => {
    render(<EmptyConversation />);

    expect(screen.getByRole("region", { name: "空白对话" })).toHaveTextContent("Rei 在这里。想说的时候，就说。");
    expect(document.querySelector(".reiAvatar-idle")).toBeInTheDocument();
  });

  it("keeps keyboard, send, and voice callbacks in the visual composer", async () => {
    const onInputChange = vi.fn();
    const onSubmit = vi.fn((event) => event.preventDefault());
    const onVoiceClick = vi.fn();
    render(
      <ChatComposer
        input="继续走吧"
        onInputChange={onInputChange}
        onSubmit={onSubmit}
        onVoiceClick={onVoiceClick}
        sending={false}
        status={<span>语音待机</span>}
        statusTone="ready"
        voiceActive={false}
        voiceDisabled={false}
        voiceLabel="开始语音 / Start Voice"
        voiceTitle="开始语音"
      />
    );

    await userEvent.click(screen.getByRole("button", { name: "开始语音 / Start Voice" }));
    expect(onVoiceClick).toHaveBeenCalledOnce();

    await userEvent.click(screen.getByRole("button", { name: "发送" }));
    expect(onSubmit).toHaveBeenCalledOnce();
    expect(screen.getByLabelText("聊天输入")).toHaveValue("继续走吧");
  });
});
