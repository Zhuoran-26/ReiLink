import type { VoiceSpokenReplyMode } from "./voiceProfile";
import { getSystemTtsProviderDescriptor, SYSTEM_TTS_PROVIDER_ID } from "./ttsProviderRegistry";

export type TtsStrategyId = "system_speech_synthesis";
export type TtsSpeakSource = "assistant_reply" | "direct_conversation" | "test_voice";

export type TtsStrategyStatus = {
  available: boolean;
  hasVoices: boolean;
  hasChineseVoice: boolean;
  selectedVoiceLanguage: string | null;
};

export type TtsSpeakRequest = {
  text: string;
  profile: VoiceSpokenReplyMode;
  rate?: number;
  volume?: number;
  source?: TtsSpeakSource;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (reason: string) => void;
};

export type TtsSpeakAttempt = {
  ok: boolean;
  errorReason?: string;
};

export interface TtsStrategy {
  id: TtsStrategyId;
  label: string;
  description: string;
  prepare(onStatusChanged?: () => void): void;
  getStatus(): TtsStrategyStatus;
  isAvailable(): boolean;
  speak(request: TtsSpeakRequest): TtsSpeakAttempt;
  stop(): void;
  resetForTest(): void;
}

const clamp = (value: number | undefined, min: number, max: number, fallback: number) => {
  if (typeof value !== "number" || Number.isNaN(value)) return fallback;
  return Math.min(max, Math.max(min, value));
};

const isChineseVoice = (voice: SpeechSynthesisVoice) => voice.lang.toLowerCase().startsWith("zh");

const voicePriority = (voice: SpeechSynthesisVoice) => {
  const language = voice.lang.toLowerCase();
  if (language === "zh-cn") return 0;
  if (language === "zh-hans") return 1;
  if (language.startsWith("zh-")) return 2;
  if (language.startsWith("zh")) return 3;
  return 4;
};

export class SystemSpeechSynthesisStrategy implements TtsStrategy {
  id: TtsStrategyId = SYSTEM_TTS_PROVIDER_ID;
  label = getSystemTtsProviderDescriptor().label;
  description = getSystemTtsProviderDescriptor().description;

  private voices: SpeechSynthesisVoice[] = [];
  private voicesChangedListenerBound = false;
  private onStatusChanged: (() => void) | null = null;

  prepare(onStatusChanged?: () => void) {
    if (onStatusChanged) {
      this.onStatusChanged = onStatusChanged;
    }
    if (!this.isAvailable()) {
      this.voices = [];
      return;
    }
    this.refreshVoices();
    if (this.voicesChangedListenerBound) return;
    const synthesis = window.speechSynthesis;
    const onVoicesChanged = () => {
      this.refreshVoices();
      this.onStatusChanged?.();
    };
    if (typeof synthesis.addEventListener === "function") {
      synthesis.addEventListener("voiceschanged", onVoicesChanged);
      this.voicesChangedListenerBound = true;
      return;
    }
    synthesis.onvoiceschanged = onVoicesChanged;
    this.voicesChangedListenerBound = true;
  }

  getStatus(): TtsStrategyStatus {
    this.prepare();
    const selectedVoice = this.selectVoice();
    return {
      available: this.isAvailable(),
      hasVoices: this.voices.length > 0,
      hasChineseVoice: this.voices.some(isChineseVoice),
      selectedVoiceLanguage: selectedVoice?.lang ?? null
    };
  }

  isAvailable() {
    return (
      typeof window !== "undefined" &&
      typeof window.speechSynthesis !== "undefined" &&
      typeof window.SpeechSynthesisUtterance === "function"
    );
  }

  speak(request: TtsSpeakRequest): TtsSpeakAttempt {
    if (!this.isAvailable()) {
      return { ok: false, errorReason: "unavailable" };
    }

    const utterance = new window.SpeechSynthesisUtterance(request.text);
    utterance.rate = clamp(request.rate, 0.7, 1.3, 1);
    utterance.volume = clamp(request.volume, 0, 1, 1);
    const selectedVoice = this.selectVoice();
    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }
    utterance.lang = selectedVoice?.lang ?? "zh-CN";
    utterance.onstart = () => request.onStart?.();
    utterance.onend = () => request.onEnd?.();
    utterance.onerror = (event) => request.onError?.(event.error || "speech_error");

    try {
      if (window.speechSynthesis.paused && typeof window.speechSynthesis.resume === "function") {
        window.speechSynthesis.resume();
      }
      window.speechSynthesis.speak(utterance);
      return { ok: true };
    } catch {
      return { ok: false, errorReason: "speech_error" };
    }
  }

  stop() {
    window.speechSynthesis?.cancel();
  }

  resetForTest() {
    this.voices = [];
    this.voicesChangedListenerBound = false;
    this.onStatusChanged = null;
  }

  private refreshVoices() {
    if (!this.isAvailable()) {
      this.voices = [];
      return;
    }
    try {
      this.voices = window.speechSynthesis.getVoices?.() ?? [];
    } catch {
      this.voices = [];
    }
  }

  private selectVoice() {
    if (this.voices.length === 0) return undefined;
    return [...this.voices].sort((left, right) => voicePriority(left) - voicePriority(right))[0];
  }
}

export const systemSpeechSynthesisStrategy = new SystemSpeechSynthesisStrategy();
