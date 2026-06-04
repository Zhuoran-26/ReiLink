import { eventBus } from "./eventBus";

export type VoiceInputPhase = "idle" | "listening" | "recognizing";
export type VoiceInputStopReason = "user_stop" | "unmount";
export type VoiceInputErrorReason = "not_supported" | "permission_denied" | "network" | "no_speech" | "aborted" | "audio_capture" | "unknown";

export type VoiceInputStatus = {
  supported: boolean;
  phase: VoiceInputPhase;
  language: string;
  lastError: string | null;
  lastTranscriptCharacterCount: number;
  interimCharacterCount: number;
};

export type VoiceInputStartOptions = {
  onFinalTranscript: (text: string) => void;
};

type VoiceInputListener = (status: VoiceInputStatus) => void;

type SpeechRecognitionAlternativeLike = {
  transcript?: string;
};

type SpeechRecognitionResultLike = {
  isFinal?: boolean;
  length: number;
  [index: number]: SpeechRecognitionAlternativeLike;
};

type SpeechRecognitionResultListLike = {
  length: number;
  [index: number]: SpeechRecognitionResultLike;
};

type SpeechRecognitionEventLike = {
  resultIndex?: number;
  results: SpeechRecognitionResultListLike;
};

type SpeechRecognitionErrorEventLike = {
  error?: string;
};

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort?: () => void;
};

type SpeechRecognitionConstructorLike = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructorLike;
    webkitSpeechRecognition?: SpeechRecognitionConstructorLike;
  }
}

type ActiveRecognition = {
  recognition: SpeechRecognitionLike;
  onFinalTranscript: (text: string) => void;
  finalCharacterCount: number;
  stopped: boolean;
  completed: boolean;
};

const DEFAULT_LANGUAGE = "zh-CN";

const now = () => new Date().toISOString();

const reasonText = (reason: string) => {
  const labels: Record<string, string> = {
    not_supported: "当前环境不支持本地语音输入",
    permission_denied: "麦克风权限被拒绝",
    network: "语音识别服务不可用",
    no_speech: "没有识别到语音",
    aborted: "用户停止",
    audio_capture: "无法读取麦克风",
    user_stop: "用户停止",
    unmount: "窗口关闭",
    unknown: "语音输入失败"
  };
  return labels[reason] ?? labels.unknown;
};

const normalizeErrorReason = (reason?: string): VoiceInputErrorReason => {
  if (reason === "not-allowed" || reason === "service-not-allowed" || reason === "permission_denied") {
    return "permission_denied";
  }
  if (reason === "network") return "network";
  if (reason === "no-speech" || reason === "no_speech") return "no_speech";
  if (reason === "aborted" || reason === "abort") return "aborted";
  if (reason === "audio-capture" || reason === "audio_capture") return "audio_capture";
  if (reason === "not_supported") return "not_supported";
  return "unknown";
};

const recognitionConstructor = () => {
  if (typeof window === "undefined") return undefined;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
};

const transcriptFromResult = (result: SpeechRecognitionResultLike) => {
  let text = "";
  for (let index = 0; index < result.length; index += 1) {
    text += result[index]?.transcript ?? "";
  }
  return text.trim();
};

export class VoiceInputController {
  private activeRecognition: ActiveRecognition | null = null;
  private listeners = new Set<VoiceInputListener>();
  private lastError: string | null = null;
  private lastTranscriptCharacterCount = 0;
  private interimCharacterCount = 0;
  private language = DEFAULT_LANGUAGE;
  private lastUnavailableEventAt = 0;

  getStatus(): VoiceInputStatus {
    return {
      supported: this.isSupported(),
      phase: this.activeRecognition ? (this.interimCharacterCount > 0 ? "recognizing" : "listening") : "idle",
      language: this.language,
      lastError: this.lastError,
      lastTranscriptCharacterCount: this.lastTranscriptCharacterCount,
      interimCharacterCount: this.interimCharacterCount
    };
  }

  subscribe(listener: VoiceInputListener) {
    this.listeners.add(listener);
    listener(this.getStatus());
    return () => {
      this.listeners.delete(listener);
    };
  }

  start(options: VoiceInputStartOptions) {
    const Recognition = recognitionConstructor();
    if (!Recognition) {
      this.lastError = reasonText("not_supported");
      this.emitUnavailable();
      this.notify();
      return false;
    }

    this.stop("user_stop", { emitEvent: false });
    const recognition = new Recognition();
    recognition.lang = this.language;
    recognition.interimResults = true;
    recognition.continuous = false;

    const activeRecognition: ActiveRecognition = {
      recognition,
      onFinalTranscript: options.onFinalTranscript,
      finalCharacterCount: 0,
      stopped: false,
      completed: false
    };
    this.activeRecognition = activeRecognition;
    this.lastError = null;
    this.interimCharacterCount = 0;

    recognition.onstart = () => {
      if (this.activeRecognition !== activeRecognition || activeRecognition.stopped) return;
      eventBus.emit({ type: "voice_input_started", timestamp: now(), language: this.language });
      this.notify();
    };

    recognition.onresult = (event) => {
      if (this.activeRecognition !== activeRecognition || activeRecognition.stopped) return;
      let interimText = "";
      let finalText = "";
      const startIndex = event.resultIndex ?? 0;
      for (let index = startIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const text = transcriptFromResult(result);
        if (!text) continue;
        if (result.isFinal) {
          finalText += text;
        } else {
          interimText += text;
        }
      }
      this.interimCharacterCount = interimText.length;
      if (interimText) {
        this.notify();
      }
      const normalizedFinal = finalText.trim();
      if (!normalizedFinal) return;
      activeRecognition.completed = true;
      activeRecognition.finalCharacterCount += normalizedFinal.length;
      this.lastTranscriptCharacterCount = activeRecognition.finalCharacterCount;
      activeRecognition.onFinalTranscript(normalizedFinal);
      eventBus.emit({
        type: "voice_input_completed",
        timestamp: now(),
        character_count: normalizedFinal.length,
        is_final: true,
        language: this.language
      });
      this.notify();
    };

    recognition.onerror = (event) => {
      if (this.activeRecognition !== activeRecognition || activeRecognition.stopped) return;
      this.activeRecognition = null;
      const reason = normalizeErrorReason(event.error);
      this.lastError = reasonText(reason);
      this.interimCharacterCount = 0;
      eventBus.emit({
        type: "voice_input_error",
        timestamp: now(),
        character_count: activeRecognition.finalCharacterCount || undefined,
        reason,
        status: this.lastError,
        language: this.language
      });
      this.notify();
    };

    recognition.onend = () => {
      if (this.activeRecognition !== activeRecognition) return;
      this.activeRecognition = null;
      this.interimCharacterCount = 0;
      this.notify();
    };

    this.notify();
    try {
      recognition.start();
    } catch {
      this.activeRecognition = null;
      this.lastError = reasonText("unknown");
      this.interimCharacterCount = 0;
      eventBus.emit({
        type: "voice_input_error",
        timestamp: now(),
        reason: "unknown",
        status: this.lastError,
        language: this.language
      });
      this.notify();
      return false;
    }
    return true;
  }

  stop(reason: VoiceInputStopReason = "user_stop", options: { emitEvent?: boolean } = {}) {
    if (!this.activeRecognition) return;
    const activeRecognition = this.activeRecognition;
    activeRecognition.stopped = true;
    this.activeRecognition = null;
    this.interimCharacterCount = 0;
    try {
      activeRecognition.recognition.stop();
    } catch {
      activeRecognition.recognition.abort?.();
    }
    if (options.emitEvent !== false) {
      eventBus.emit({
        type: "voice_input_stopped",
        timestamp: now(),
        character_count: activeRecognition.finalCharacterCount || undefined,
        reason,
        status: reasonText(reason),
        language: this.language
      });
    }
    this.notify();
  }

  resetForTest() {
    this.activeRecognition = null;
    this.listeners.clear();
    this.lastError = null;
    this.lastTranscriptCharacterCount = 0;
    this.interimCharacterCount = 0;
    this.language = DEFAULT_LANGUAGE;
    this.lastUnavailableEventAt = 0;
  }

  private isSupported() {
    return Boolean(recognitionConstructor());
  }

  private emitUnavailable() {
    const currentTime = Date.now();
    if (currentTime - this.lastUnavailableEventAt < 3000) return;
    this.lastUnavailableEventAt = currentTime;
    eventBus.emit({
      type: "voice_input_unavailable",
      timestamp: now(),
      reason: "not_supported",
      status: reasonText("not_supported"),
      language: this.language
    });
  }

  private notify() {
    const status = this.getStatus();
    for (const listener of this.listeners) {
      listener(status);
    }
  }
}

export const voiceInput = new VoiceInputController();
