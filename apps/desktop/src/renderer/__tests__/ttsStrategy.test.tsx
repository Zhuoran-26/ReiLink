import { afterEach, describe, expect, it, vi } from "vitest";

import { SystemSpeechSynthesisStrategy } from "../ttsStrategy";

class MockSpeechSynthesisUtterance {
  text: string;
  rate = 1;
  volume = 1;
  voice: SpeechSynthesisVoice | null = null;
  lang = "";
  onstart: ((event: SpeechSynthesisEvent) => void) | null = null;
  onend: ((event: SpeechSynthesisEvent) => void) | null = null;
  onerror: ((event: SpeechSynthesisErrorEvent) => void) | null = null;

  constructor(text: string) {
    this.text = text;
  }
}

const mockVoice = (lang: string, name = lang): SpeechSynthesisVoice =>
  ({
    default: false,
    lang,
    localService: true,
    name,
    voiceURI: name
  }) as SpeechSynthesisVoice;

const installSpeechSynthesisMock = (voices: SpeechSynthesisVoice[] = []) => {
  const listeners = new Set<() => void>();
  const speak = vi.fn();
  const cancel = vi.fn();
  const resume = vi.fn();
  const getVoices = vi.fn(() => voices);
  vi.stubGlobal("SpeechSynthesisUtterance", MockSpeechSynthesisUtterance);
  Object.defineProperty(window, "speechSynthesis", {
    configurable: true,
    value: {
      speak,
      cancel,
      resume,
      getVoices,
      paused: false,
      addEventListener: vi.fn((event: string, listener: () => void) => {
        if (event === "voiceschanged") listeners.add(listener);
      }),
      onvoiceschanged: null
    }
  });
  return { speak, cancel, resume, getVoices };
};

describe("SystemSpeechSynthesisStrategy", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    Reflect.deleteProperty(window, "speechSynthesis");
  });

  it("speaks through system speechSynthesis when available", () => {
    const speech = installSpeechSynthesisMock([mockVoice("zh-CN")]);
    const strategy = new SystemSpeechSynthesisStrategy();

    strategy.prepare();
    const attempt = strategy.speak({
      text: "你好",
      profile: "full",
      source: "test_voice",
      rate: 1.2,
      volume: 0.6
    });

    expect(attempt).toMatchObject({ ok: true });
    expect(speech.speak).toHaveBeenCalledTimes(1);
    expect(speech.speak.mock.calls[0][0]).toMatchObject({
      text: "你好",
      rate: 1.2,
      volume: 0.6,
      lang: "zh-CN",
      voice: expect.objectContaining({ lang: "zh-CN" })
    });
  });

  it("returns an unavailable result without crashing when system speech is missing", () => {
    vi.stubGlobal("SpeechSynthesisUtterance", undefined);
    Object.defineProperty(window, "speechSynthesis", {
      configurable: true,
      value: undefined
    });
    const strategy = new SystemSpeechSynthesisStrategy();

    expect(strategy.isAvailable()).toBe(false);
    expect(strategy.speak({ text: "你好", profile: "full", source: "test_voice" })).toMatchObject({
      ok: false,
      errorReason: "unavailable"
    });
  });

  it("stops playback through speechSynthesis cancel", () => {
    const speech = installSpeechSynthesisMock();
    const strategy = new SystemSpeechSynthesisStrategy();

    strategy.stop();

    expect(speech.cancel).toHaveBeenCalledTimes(1);
  });
});
