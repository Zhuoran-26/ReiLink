import { eventBus } from "./eventBus";

export type AudioCapturePhase = "idle" | "recording";

export type AudioCaptureStatus = {
  supported: boolean;
  phase: AudioCapturePhase;
  lastError: string | null;
};

export type AudioCaptureRecording = {
  blob: Blob;
  durationMs: number;
  sizeBytes: number;
  mimeType: string;
};

type AudioCaptureListener = (status: AudioCaptureStatus) => void;

type AudioCaptureStartOptions = {
  durationMs?: number;
  onRecorded: (recording: AudioCaptureRecording) => void;
};

type ActiveCapture = {
  recorder: MediaRecorder;
  stream: MediaStream;
  startedAt: number;
  chunks: Blob[];
  timer: ReturnType<typeof setTimeout>;
  stopped: boolean;
};

const DEFAULT_RECORDING_DURATION_MS = 3000;
const MAX_RECORDING_DURATION_MS = 5000;
const now = () => new Date().toISOString();

const errorText = (reason: string) => {
  const labels: Record<string, string> = {
    not_supported: "当前环境不支持录音",
    permission_denied: "麦克风权限被拒绝",
    recording_failed: "录音失败",
    unknown: "录音失败"
  };
  return labels[reason] ?? labels.unknown;
};

const recorderMimeType = () => {
  if (typeof MediaRecorder === "undefined") return "";
  const candidates = ["audio/webm", "audio/ogg", "audio/mp4"];
  const supported = candidates.find((candidate) => {
    try {
      return typeof MediaRecorder.isTypeSupported === "function" && MediaRecorder.isTypeSupported(candidate);
    } catch {
      return false;
    }
  });
  return supported ?? "";
};

export class AudioCaptureController {
  private activeCapture: ActiveCapture | null = null;
  private listeners = new Set<AudioCaptureListener>();
  private lastError: string | null = null;

  getStatus(): AudioCaptureStatus {
    return {
      supported: this.isSupported(),
      phase: this.activeCapture ? "recording" : "idle",
      lastError: this.lastError
    };
  }

  subscribe(listener: AudioCaptureListener) {
    this.listeners.add(listener);
    listener(this.getStatus());
    return () => {
      this.listeners.delete(listener);
    };
  }

  async start(options: AudioCaptureStartOptions) {
    if (this.activeCapture) return true;
    if (!this.isSupported()) {
      this.setError("not_supported");
      return false;
    }

    const durationMs = Math.min(Math.max(options.durationMs ?? DEFAULT_RECORDING_DURATION_MS, 1), MAX_RECORDING_DURATION_MS);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      this.setError(isPermissionDenied(error) ? "permission_denied" : "recording_failed");
      return false;
    }

    let recorder: MediaRecorder;
    try {
      const mimeType = recorderMimeType();
      recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    } catch {
      stopStreamTracks(stream);
      this.setError("recording_failed");
      return false;
    }

    const activeCapture: ActiveCapture = {
      recorder,
      stream,
      startedAt: Date.now(),
      chunks: [],
      timer: setTimeout(() => this.stop("max_duration"), durationMs),
      stopped: false
    };
    this.activeCapture = activeCapture;
    this.lastError = null;

    recorder.ondataavailable = (event) => {
      if (event.data?.size > 0) activeCapture.chunks.push(event.data);
    };

    recorder.onerror = () => {
      if (this.activeCapture !== activeCapture) return;
      this.stop("recording_failed");
      this.setError("recording_failed");
    };

    recorder.onstop = () => {
      if (this.activeCapture === activeCapture) this.activeCapture = null;
      clearTimeout(activeCapture.timer);
      stopStreamTracks(activeCapture.stream);
      const recordedDurationMs = Math.max(0, Date.now() - activeCapture.startedAt);
      const mimeType = recorder.mimeType || activeCapture.chunks[0]?.type || "audio/webm";
      const blob = new Blob(activeCapture.chunks, { type: mimeType });
      const recording = {
        blob,
        durationMs: recordedDurationMs,
        sizeBytes: blob.size,
        mimeType
      };
      eventBus.emit({
        type: "audio_capture_completed",
        timestamp: now(),
        duration_ms: recording.durationMs,
        size_bytes: recording.sizeBytes,
        mime_type: recording.mimeType
      });
      options.onRecorded(recording);
      this.notify();
    };

    try {
      recorder.start();
    } catch {
      this.activeCapture = null;
      clearTimeout(activeCapture.timer);
      stopStreamTracks(stream);
      this.setError("recording_failed");
      return false;
    }

    eventBus.emit({ type: "audio_capture_started", timestamp: now(), duration_ms: durationMs });
    this.notify();
    return true;
  }

  stop(reason = "user_stop") {
    const activeCapture = this.activeCapture;
    if (!activeCapture || activeCapture.stopped) return;
    activeCapture.stopped = true;
    eventBus.emit({
      type: "audio_capture_stopped",
      timestamp: now(),
      reason,
      duration_ms: Math.max(0, Date.now() - activeCapture.startedAt)
    });
    try {
      if (activeCapture.recorder.state !== "inactive") {
        activeCapture.recorder.stop();
      }
    } catch {
      this.activeCapture = null;
      clearTimeout(activeCapture.timer);
      stopStreamTracks(activeCapture.stream);
      this.setError("recording_failed");
    }
    this.notify();
  }

  resetForTest() {
    if (this.activeCapture) {
      clearTimeout(this.activeCapture.timer);
      stopStreamTracks(this.activeCapture.stream);
    }
    this.activeCapture = null;
    this.listeners.clear();
    this.lastError = null;
  }

  private isSupported() {
    return typeof navigator !== "undefined" && typeof navigator.mediaDevices?.getUserMedia === "function" && typeof MediaRecorder !== "undefined";
  }

  private setError(reason: string) {
    this.lastError = errorText(reason);
    eventBus.emit({ type: "audio_capture_error", timestamp: now(), reason, status: this.lastError });
    this.notify();
  }

  private notify() {
    const status = this.getStatus();
    for (const listener of this.listeners) listener(status);
  }
}

const stopStreamTracks = (stream: MediaStream) => {
  for (const track of stream.getTracks()) {
    track.stop();
  }
};

const isPermissionDenied = (error: unknown) => {
  if (!(error instanceof DOMException) && !(error instanceof Error)) return false;
  return ["NotAllowedError", "PermissionDeniedError", "SecurityError"].includes(error.name);
};

export const audioCapture = new AudioCaptureController();
export { DEFAULT_RECORDING_DURATION_MS, MAX_RECORDING_DURATION_MS };
