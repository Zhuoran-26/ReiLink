import { eventBus } from "./eventBus";

export type VoiceStopReason = "user_stop" | "new_message" | "disabled" | "unmount" | "new_reply";

export type VoiceOutputStatus = {
  active: boolean;
  available: boolean;
  lastError: string | null;
  hasVoices: boolean;
  hasChineseVoice: boolean;
  selectedVoiceLanguage: string | null;
};

type VoiceOutputListener = (status: VoiceOutputStatus) => void;
type VoiceSpeakOptions = { rate?: number; volume?: number };

type ActiveSpeech = {
  utterance: SpeechSynthesisUtterance;
  characterCount: number;
  stopped: boolean;
};

const now = () => new Date().toISOString();

const reasonText = (reason: string) => {
  const labels: Record<string, string> = {
    user_stop: "用户停止",
    new_message: "新消息打断",
    disabled: "已关闭",
    unmount: "窗口关闭",
    new_reply: "新回复开始",
    unavailable: "当前环境不支持",
    speech_error: "播放失败"
  };
  return labels[reason] ?? "播放失败";
};

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

export class VoiceOutputController {
  private activeSpeech: ActiveSpeech | null = null;
  private listeners = new Set<VoiceOutputListener>();
  private lastError: string | null = null;
  private voices: SpeechSynthesisVoice[] = [];
  private voicesChangedListenerBound = false;
  private lastUnavailableEventAt = 0;

  getStatus(): VoiceOutputStatus {
    this.prepareVoices();
    const selectedVoice = this.selectVoice();
    return {
      active: Boolean(this.activeSpeech),
      available: this.isAvailable(),
      lastError: this.lastError,
      hasVoices: this.voices.length > 0,
      hasChineseVoice: this.voices.some(isChineseVoice),
      selectedVoiceLanguage: selectedVoice?.lang ?? null
    };
  }

  subscribe(listener: VoiceOutputListener) {
    this.listeners.add(listener);
    listener(this.getStatus());
    return () => {
      this.listeners.delete(listener);
    };
  }

  speak(text: string, options: VoiceSpeakOptions = {}) {
    const safeText = text.trim();
    if (!safeText) return false;
    const characterCount = safeText.length;
    this.prepareVoices();
    if (!this.isAvailable()) {
      this.lastError = "当前环境不支持语音输出。";
      this.emitUnavailable(characterCount);
      this.notify();
      return false;
    }

    this.stop("new_reply");

    const utterance = new window.SpeechSynthesisUtterance(safeText);
    utterance.rate = clamp(options.rate, 0.7, 1.3, 1);
    utterance.volume = clamp(options.volume, 0, 1, 1);
    const selectedVoice = this.selectVoice();
    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }
    const activeSpeech: ActiveSpeech = { utterance, characterCount, stopped: false };
    this.activeSpeech = activeSpeech;
    this.lastError = null;

    utterance.onend = () => {
      if (this.activeSpeech !== activeSpeech || activeSpeech.stopped) return;
      this.activeSpeech = null;
      eventBus.emit({ type: "tts_completed", timestamp: now(), character_count: characterCount });
      this.notify();
    };

    utterance.onerror = (event) => {
      if (this.activeSpeech !== activeSpeech || activeSpeech.stopped) return;
      this.activeSpeech = null;
      const reason = event.error || "speech_error";
      this.lastError = reasonText(reason);
      eventBus.emit({
        type: "tts_error",
        timestamp: now(),
        character_count: characterCount,
        reason,
        status: this.lastError
      });
      this.notify();
    };

    eventBus.emit({ type: "tts_started", timestamp: now(), character_count: characterCount });
    this.notify();
    window.speechSynthesis.speak(utterance);
    return true;
  }

  stop(reason: VoiceStopReason) {
    if (!this.activeSpeech) return;
    const activeSpeech = this.activeSpeech;
    activeSpeech.stopped = true;
    this.activeSpeech = null;
    window.speechSynthesis?.cancel();
    eventBus.emit({
      type: "tts_stopped",
      timestamp: now(),
      character_count: activeSpeech.characterCount,
      reason
    });
    this.notify();
  }

  resetForTest() {
    if (this.activeSpeech) {
      this.activeSpeech.stopped = true;
    }
    this.activeSpeech = null;
    this.lastError = null;
    this.listeners.clear();
    this.voices = [];
    this.voicesChangedListenerBound = false;
    this.lastUnavailableEventAt = 0;
  }

  private isAvailable() {
    return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  }

  private prepareVoices() {
    if (!this.isAvailable()) return;
    this.refreshVoices();
    if (this.voicesChangedListenerBound) return;
    const synthesis = window.speechSynthesis;
    const onVoicesChanged = () => {
      this.refreshVoices();
      this.notify();
    };
    if (typeof synthesis.addEventListener === "function") {
      synthesis.addEventListener("voiceschanged", onVoicesChanged);
      this.voicesChangedListenerBound = true;
      return;
    }
    synthesis.onvoiceschanged = onVoicesChanged;
    this.voicesChangedListenerBound = true;
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

  private emitUnavailable(characterCount: number) {
    const currentTime = Date.now();
    if (currentTime - this.lastUnavailableEventAt < 3000) return;
    this.lastUnavailableEventAt = currentTime;
    eventBus.emit({
      type: "tts_error",
      timestamp: now(),
      character_count: characterCount,
      reason: "unavailable",
      status: reasonText("unavailable")
    });
  }

  private notify() {
    const status = this.getStatus();
    for (const listener of this.listeners) {
      listener(status);
    }
  }
}

export const voiceOutput = new VoiceOutputController();
