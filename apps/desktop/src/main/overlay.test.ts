import {
  createOverlayMessage,
  createOverlayState,
  OVERLAY_MAX_MESSAGE_LENGTH,
  sanitizeOverlayText
} from "../shared/overlay";

describe("overlay content safety", () => {
  it("redacts sensitive text and truncates long content", () => {
    const text = sanitizeOverlayText(
      "请不要显示 /Users/aragoto/Desktop/ReiLink/services/backend/.env，也不要显示 API key 或 raw stderr。后面继续补一些很长很长的内容用于测试截断，还要继续写很多观察、路线、翻滚、精力条和时机内容，确保悬浮层只保留短摘要。继续追加很多很多很多很多很多很多很多很多很多很多文字。"
    );

    expect(text.length).toBeLessThanOrEqual(OVERLAY_MAX_MESSAGE_LENGTH);
    expect(text).toContain("…");
    expect(text).not.toContain("/Users/aragoto");
    expect(text).not.toContain(".env");
    expect(text).not.toContain("API key");
    expect(text).not.toContain("raw stderr");
  });

  it("keeps only the latest three safe messages in state", () => {
    const messages = [0, 1, 2, 3].map((index) =>
      createOverlayMessage({ text: `message ${index}`, source: "assistant_reply" }, `id-${index}`)
    );

    const state = createOverlayState(true, true, messages, "2026-06-06T00:00:00.000Z");

    expect(state.messages.map((message) => message.text)).toEqual(["message 1", "message 2", "message 3"]);
    expect(state.max_messages).toBe(3);
    expect(state.visible).toBe(true);
  });
});
