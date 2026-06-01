import { eventBus } from "./eventBus";

export type VoiceStopReason = "user_stop" | "new_message" | "disabled" | "unmount" | "new_reply";

export type VoiceOutputStatus = {
  active: boolean;
  available: boolean;
  lastError: string | null;
};

type VoiceOutputListener = (status: VoiceOutputStatus) => void;

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

export class VoiceOutputController {
  private activeSpeech: ActiveSpeech | null = null;
  private listeners = new Set<VoiceOutputListener>();
  private lastError: string | null = null;

  getStatus(): VoiceOutputStatus {
    return {
      active: Boolean(this.activeSpeech),
      available: this.isAvailable(),
      lastError: this.lastError
    };
  }

  subscribe(listener: VoiceOutputListener) {
    this.listeners.add(listener);
    listener(this.getStatus());
    return () => {
      this.listeners.delete(listener);
    };
  }

  speak(text: string, options: { rate?: number; volume?: number } = {}) {
    const safeText = text.trim();
    if (!safeText) return false;
    const characterCount = safeText.length;
    if (!this.isAvailable()) {
      this.lastError = "当前环境不支持语音输出。";
      eventBus.emit({
        type: "tts_error",
        timestamp: now(),
        character_count: characterCount,
        reason: "unavailable",
        status: reasonText("unavailable")
      });
      this.notify();
      return false;
    }

    this.stop("new_reply");

    const utterance = new window.SpeechSynthesisUtterance(safeText);
    utterance.rate = options.rate ?? 1;
    utterance.volume = options.volume ?? 1;
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
  }

  private isAvailable() {
    return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  }

  private notify() {
    const status = this.getStatus();
    for (const listener of this.listeners) {
      listener(status);
    }
  }
}

export const voiceOutput = new VoiceOutputController();
