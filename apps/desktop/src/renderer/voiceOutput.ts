import { eventBus } from "./eventBus";
import { systemSpeechSynthesisStrategy, type TtsSpeakSource, type TtsStrategy, type TtsStrategyId } from "./ttsStrategy";
import type { VoiceSpokenReplyMode } from "./voiceProfile";

export type VoiceStopReason = "user_stop" | "new_message" | "disabled" | "unmount" | "new_reply";
export type VoiceSpeakSource = TtsSpeakSource;

export type VoiceOutputStatus = {
  active: boolean;
  phase: "idle" | "starting" | "playing";
  available: boolean;
  lastError: string | null;
  hasVoices: boolean;
  hasChineseVoice: boolean;
  selectedVoiceLanguage: string | null;
  strategyId: TtsStrategyId;
  strategyLabel: string;
  strategyDescription: string;
};

type VoiceOutputListener = (status: VoiceOutputStatus) => void;
type VoiceSpeakOptions = {
  rate?: number;
  volume?: number;
  source?: VoiceSpeakSource;
  profile?: VoiceSpokenReplyMode;
};

type ActiveSpeech = {
  characterCount: number;
  source: VoiceSpeakSource;
  profile: VoiceSpokenReplyMode;
  strategyId: TtsStrategyId;
  stopped: boolean;
  started: boolean;
  startTimer: number | null;
};

const START_TIMEOUT_MS = 5000;

const now = () => new Date().toISOString();

const reasonText = (reason: string) => {
  const labels: Record<string, string> = {
    user_stop: "用户停止",
    new_message: "新消息打断",
    disabled: "已关闭",
    unmount: "窗口关闭",
    new_reply: "新回复开始",
    unavailable: "当前环境不支持",
    speech_error: "播放失败",
    start_timeout: "语音没有开始，请检查系统声音输出或语音包"
  };
  return labels[reason] ?? "播放失败";
};

export class VoiceOutputController {
  private activeSpeech: ActiveSpeech | null = null;
  private listeners = new Set<VoiceOutputListener>();
  private lastError: string | null = null;
  private lastUnavailableEventAt = 0;

  constructor(private readonly strategy: TtsStrategy = systemSpeechSynthesisStrategy) {}

  getStatus(): VoiceOutputStatus {
    this.strategy.prepare(() => this.notify());
    const strategyStatus = this.strategy.getStatus();
    return {
      active: Boolean(this.activeSpeech),
      phase: this.activeSpeech ? (this.activeSpeech.started ? "playing" : "starting") : "idle",
      available: strategyStatus.available,
      lastError: this.lastError,
      hasVoices: strategyStatus.hasVoices,
      hasChineseVoice: strategyStatus.hasChineseVoice,
      selectedVoiceLanguage: strategyStatus.selectedVoiceLanguage,
      strategyId: this.strategy.id,
      strategyLabel: this.strategy.label,
      strategyDescription: this.strategy.description
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
    const source = options.source ?? "assistant_reply";
    const profile = options.profile ?? "full";
    this.strategy.prepare(() => this.notify());
    if (!this.strategy.isAvailable()) {
      this.lastError = "当前环境不支持语音输出。";
      this.emitUnavailable(characterCount, source, profile);
      this.notify();
      return false;
    }

    this.stop("new_reply");

    const activeSpeech: ActiveSpeech = {
      characterCount,
      source,
      profile,
      strategyId: this.strategy.id,
      stopped: false,
      started: false,
      startTimer: null
    };
    this.activeSpeech = activeSpeech;
    this.lastError = null;

    this.notify();
    activeSpeech.startTimer = window.setTimeout(() => {
      if (this.activeSpeech !== activeSpeech || activeSpeech.stopped || activeSpeech.started) return;
      this.activeSpeech = null;
      this.lastError = reasonText("start_timeout");
      eventBus.emit({
        type: "tts_error",
        timestamp: now(),
        character_count: characterCount,
        reason: "start_timeout",
        status: this.lastError,
        source,
        profile,
        strategy_id: activeSpeech.strategyId
      });
      this.notify();
    }, START_TIMEOUT_MS);

    const attempt = this.strategy.speak({
      text: safeText,
      rate: options.rate,
      volume: options.volume,
      source,
      profile,
      onStart: () => {
        if (this.activeSpeech !== activeSpeech || activeSpeech.stopped) return;
        activeSpeech.started = true;
        this.clearStartTimer(activeSpeech);
        eventBus.emit({
          type: "tts_started",
          timestamp: now(),
          character_count: characterCount,
          source,
          profile,
          strategy_id: activeSpeech.strategyId
        });
        this.notify();
      },
      onEnd: () => {
        if (this.activeSpeech !== activeSpeech || activeSpeech.stopped) return;
        this.clearStartTimer(activeSpeech);
        this.activeSpeech = null;
        if (!activeSpeech.started) {
          this.lastError = reasonText("start_timeout");
          eventBus.emit({
            type: "tts_error",
            timestamp: now(),
            character_count: characterCount,
            reason: "start_timeout",
            status: this.lastError,
            source,
            profile,
            strategy_id: activeSpeech.strategyId
          });
          this.notify();
          return;
        }
        eventBus.emit({
          type: "tts_completed",
          timestamp: now(),
          character_count: characterCount,
          source,
          profile,
          strategy_id: activeSpeech.strategyId
        });
        this.notify();
      },
      onError: (reason) => {
        if (this.activeSpeech !== activeSpeech || activeSpeech.stopped) return;
        this.clearStartTimer(activeSpeech);
        this.activeSpeech = null;
        this.lastError = reasonText(reason);
        eventBus.emit({
          type: "tts_error",
          timestamp: now(),
          character_count: characterCount,
          reason,
          status: this.lastError,
          source,
          profile,
          strategy_id: activeSpeech.strategyId
        });
        this.notify();
      }
    });

    if (!attempt.ok) {
      this.clearStartTimer(activeSpeech);
      this.activeSpeech = null;
      const reason = attempt.errorReason ?? "speech_error";
      this.lastError = reasonText(reason);
      eventBus.emit({
        type: "tts_error",
        timestamp: now(),
        character_count: characterCount,
        reason,
        status: this.lastError,
        source,
        profile,
        strategy_id: activeSpeech.strategyId
      });
      this.notify();
      return false;
    }

    return true;
  }

  stop(reason: VoiceStopReason) {
    if (!this.activeSpeech) return;
    const activeSpeech = this.activeSpeech;
    activeSpeech.stopped = true;
    this.clearStartTimer(activeSpeech);
    this.activeSpeech = null;
    this.strategy.stop();
    eventBus.emit({
      type: "tts_stopped",
      timestamp: now(),
      character_count: activeSpeech.characterCount,
      reason,
      source: activeSpeech.source,
      profile: activeSpeech.profile,
      strategy_id: activeSpeech.strategyId
    });
    this.notify();
  }

  resetForTest() {
    if (this.activeSpeech) {
      this.activeSpeech.stopped = true;
      this.clearStartTimer(this.activeSpeech);
    }
    this.activeSpeech = null;
    this.lastError = null;
    this.listeners.clear();
    this.lastUnavailableEventAt = 0;
    this.strategy.resetForTest();
  }

  private emitUnavailable(characterCount: number, source: VoiceSpeakSource, profile: VoiceSpokenReplyMode) {
    const currentTime = Date.now();
    if (currentTime - this.lastUnavailableEventAt < 3000) return;
    this.lastUnavailableEventAt = currentTime;
    eventBus.emit({
      type: "tts_error",
      timestamp: now(),
      character_count: characterCount,
      reason: "unavailable",
      status: reasonText("unavailable"),
      source,
      profile,
      strategy_id: this.strategy.id
    });
  }

  private clearStartTimer(activeSpeech: ActiveSpeech) {
    if (activeSpeech.startTimer === null) return;
    window.clearTimeout(activeSpeech.startTimer);
    activeSpeech.startTimer = null;
  }

  private notify() {
    const status = this.getStatus();
    for (const listener of this.listeners) {
      listener(status);
    }
  }
}

export const voiceOutput = new VoiceOutputController();
