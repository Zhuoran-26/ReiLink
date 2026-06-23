import { afterEach, describe, expect, it, vi } from "vitest";

import { eventBus } from "../eventBus";
import { VoiceOutputController } from "../voiceOutput";
import type { TtsSpeakRequest, TtsStrategy } from "../ttsStrategy";

const createMockStrategy = (available: boolean) => {
  const speak = vi.fn((request: TtsSpeakRequest) => {
    request.onStart?.();
    return { ok: true };
  });
  const stop = vi.fn();
  const strategy: TtsStrategy = {
    id: "system_speech_synthesis",
    label: "System Speech Synthesis",
    description: "本机系统语音 fallback",
    prepare: vi.fn(),
    getStatus: vi.fn(() => ({
      available,
      hasVoices: available,
      hasChineseVoice: available,
      selectedVoiceLanguage: available ? "zh-CN" : null
    })),
    isAvailable: vi.fn(() => available),
    speak,
    stop,
    resetForTest: vi.fn()
  };
  return { speak, stop, strategy };
};

describe("VoiceOutputController provider resolution", () => {
  afterEach(() => {
    eventBus.clear();
    vi.restoreAllMocks();
  });

  it("falls back to the system provider when an illegal provider id is requested", () => {
    const { speak, strategy } = createMockStrategy(true);
    const controller = new VoiceOutputController(strategy, "unknown_tts");

    expect(controller.getStatus()).toMatchObject({
      providerId: "system_speech_synthesis",
      providerStatus: "available",
      providerFallbackUsed: true,
      providerFallbackReason: "unknown_provider"
    });
    expect(controller.speak("你好", { source: "test_voice", profile: "full" })).toBe(true);

    expect(speak).toHaveBeenCalledTimes(1);
    expect(eventBus.getRecentEvents(10)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          type: "tts_started",
          provider_id: "system_speech_synthesis",
          provider_status: "available",
          provider_fallback_used: true
        })
      ])
    );
    expect(JSON.stringify(eventBus.getRecentEvents(10))).not.toContain("你好");
    controller.resetForTest();
  });

  it("reports system provider unavailable without calling speech synthesis", () => {
    const { speak, strategy } = createMockStrategy(false);
    const controller = new VoiceOutputController(strategy);

    expect(controller.speak("你好", { source: "test_voice", profile: "full" })).toBe(false);

    expect(speak).not.toHaveBeenCalled();
    expect(controller.getStatus()).toMatchObject({
      providerId: "system_speech_synthesis",
      providerStatus: "unavailable",
      active: false,
      phase: "idle",
      lastError: "当前环境不支持语音输出。"
    });
    expect(eventBus.getRecentEvents(10)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          type: "tts_error",
          reason: "unavailable",
          provider_id: "system_speech_synthesis",
          provider_status: "unavailable",
          provider_fallback_used: false
        })
      ])
    );
    expect(JSON.stringify(eventBus.getRecentEvents(10))).not.toContain("你好");
    controller.resetForTest();
  });
});
