import {
  createOverlayMessage,
  createOverlayState,
  normalizeOverlayConfig,
  normalizeOverlayContentUpdate,
  normalizeOverlayMessageCount,
  normalizeOverlayOpacity,
  normalizeOverlayPosition,
  OVERLAY_DEFAULT_MESSAGE_COUNT,
  OVERLAY_DEFAULT_OPACITY,
  OVERLAY_DEFAULT_POSITION,
  OVERLAY_MAX_MESSAGE_LENGTH,
  sanitizeOverlayText
} from "../shared/overlay";
import { calculateOverlayBounds, configureOverlayWindowForClickThrough, createOverlayWindowOptions } from "./overlayWindow";

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

  it("redacts local paths with spaces before IPC payloads reach the overlay", () => {
    const update = normalizeOverlayContentUpdate({
      text: "模型在 /Users/aragoto/Library/Application Support/ReiLink/models/ggml-base.bin，stdout 里还有 transcript。",
      source: "unknown",
      timestamp: { raw: "bad" }
    });

    expect(update.source).toBe("assistant_reply");
    expect(update.timestamp).toBeUndefined();
    expect(update.text).not.toContain("/Users/aragoto");
    expect(update.text).not.toContain("Application Support");
    expect(update.text).not.toContain("stdout");
    expect(update.text).not.toContain("transcript");
  });

  it("uses safe Overlay config defaults", () => {
    const state = createOverlayState(false, false, []);
    const config = normalizeOverlayConfig({
      position: "outside",
      opacity: 2,
      max_messages: 99
    });

    expect(state.position).toBe(OVERLAY_DEFAULT_POSITION);
    expect(state.opacity).toBe(OVERLAY_DEFAULT_OPACITY);
    expect(state.max_messages).toBe(OVERLAY_DEFAULT_MESSAGE_COUNT);
    expect(config.position).toBe(OVERLAY_DEFAULT_POSITION);
    expect(config.opacity).toBe(0.95);
    expect(config.max_messages).toBe(3);
  });

  it("normalizes Overlay position, opacity, and message count", () => {
    expect(normalizeOverlayPosition("middle-left")).toBe("middle-left");
    expect(normalizeOverlayPosition("center")).toBe(OVERLAY_DEFAULT_POSITION);
    expect(normalizeOverlayOpacity(0.1)).toBe(0.35);
    expect(normalizeOverlayOpacity("0.82")).toBe(0.82);
    expect(normalizeOverlayOpacity(2)).toBe(0.95);
    expect(normalizeOverlayMessageCount(0)).toBe(1);
    expect(normalizeOverlayMessageCount("2")).toBe(2);
    expect(normalizeOverlayMessageCount(10)).toBe(3);
  });

  it("keeps only the configured number of safe messages in state", () => {
    const messages = [0, 1, 2, 3].map((index) =>
      createOverlayMessage({ text: `message ${index}`, source: "assistant_reply" }, `id-${index}`)
    );

    const state = createOverlayState(true, true, messages, "2026-06-06T00:00:00.000Z", { max_messages: 3 });
    const compactState = createOverlayState(true, true, messages, "2026-06-06T00:00:00.000Z", { max_messages: 1 });

    expect(state.messages.map((message) => message.text)).toEqual(["message 1", "message 2", "message 3"]);
    expect(state.max_messages).toBe(3);
    expect(compactState.messages.map((message) => message.text)).toEqual(["message 3"]);
    expect(compactState.max_messages).toBe(1);
    expect(state.visible).toBe(true);
  });

  it("calculates preset overlay bounds inside the primary work area", () => {
    const workArea = { x: 0, y: 0, width: 1440, height: 900 };
    const topRight = calculateOverlayBounds(workArea, "top-right");
    const middleRight = calculateOverlayBounds(workArea, "middle-right");
    const bottomLeft = calculateOverlayBounds(workArea, "bottom-left");

    expect(topRight.x).toBeGreaterThan(middleRight.width);
    expect(topRight.y).toBe(44);
    expect(middleRight.y).toBeGreaterThan(topRight.y);
    expect(bottomLeft.x).toBe(44);
    expect(bottomLeft.y).toBeGreaterThan(middleRight.y);
    for (const bounds of [topRight, middleRight, bottomLeft]) {
      expect(bounds.x).toBeGreaterThanOrEqual(workArea.x + 24);
      expect(bounds.y).toBeGreaterThanOrEqual(workArea.y + 24);
      expect(bounds.x + bounds.width).toBeLessThanOrEqual(workArea.width - 24);
      expect(bounds.y + bounds.height).toBeLessThanOrEqual(workArea.height - 24);
    }
  });

  it("builds a non-focusable click-through overlay window configuration", () => {
    const options = createOverlayWindowOptions({ width: 360, height: 168, x: 100, y: 200 }, "/tmp/preload.cjs");

    expect(options.transparent).toBe(true);
    expect(options.frame).toBe(false);
    expect(options.alwaysOnTop).toBe(true);
    expect(options.skipTaskbar).toBe(true);
    expect(options.focusable).toBe(false);
    expect(options.show).toBe(false);
    expect(options.webPreferences).toMatchObject({
      contextIsolation: true,
      nodeIntegration: false,
      preload: "/tmp/preload.cjs"
    });
  });

  it("explicitly configures click-through mouse behavior", () => {
    const window = {
      setAlwaysOnTop: vi.fn(),
      setIgnoreMouseEvents: vi.fn(),
      setVisibleOnAllWorkspaces: vi.fn()
    };

    configureOverlayWindowForClickThrough(window as unknown as Parameters<typeof configureOverlayWindowForClickThrough>[0]);

    expect(window.setIgnoreMouseEvents).toHaveBeenCalledWith(true);
    expect(window.setAlwaysOnTop).toHaveBeenCalledWith(true, "floating");
    expect(window.setVisibleOnAllWorkspaces).toHaveBeenCalledWith(true, { visibleOnFullScreen: true });
  });
});
