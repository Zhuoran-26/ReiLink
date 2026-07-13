import { eventBus } from "./eventBus";
import type { VoiceCaptureStopReason } from "../shared/events";

export type AudioCapturePhase = "idle" | "recording" | "stopping";

export type AudioCaptureStatus = {
  supported: boolean;
  phase: AudioCapturePhase;
  lastError: string | null;
  startedAtMs: number | null;
  maxDurationMs: number | null;
  lastStopReason: VoiceCaptureStopReason | null;
};

export type AudioCaptureRecording = {
  blob: Blob;
  durationMs: number;
  sizeBytes: number;
  mimeType: string;
  stopReason: Extract<VoiceCaptureStopReason, "user_stop" | "max_duration">;
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
  timer: ReturnType<typeof setTimeout> | null;
  stopped: boolean;
  finalized: boolean;
  deliverRecording: boolean;
  stopReason: VoiceCaptureStopReason | null;
  maxDurationMs: number;
};

const DEFAULT_RECORDING_DURATION_MS = 30_000;
const MAX_RECORDING_DURATION_MS = 30_000;
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
  private lastStopReason: VoiceCaptureStopReason | null = null;

  getStatus(): AudioCaptureStatus {
    return {
      supported: this.isSupported(),
      phase: this.activeCapture ? (this.activeCapture.stopped ? "stopping" : "recording") : "idle",
      lastError: this.lastError,
      startedAtMs: this.activeCapture?.startedAt ?? null,
      maxDurationMs: this.activeCapture?.maxDurationMs ?? null,
      lastStopReason: this.lastStopReason
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
      startedAt: 0,
      chunks: [],
      timer: null,
      stopped: false,
      finalized: false,
      deliverRecording: true,
      stopReason: null,
      maxDurationMs: durationMs
    };
    this.activeCapture = activeCapture;
    this.lastError = null;
    this.lastStopReason = null;

    recorder.ondataavailable = (event) => {
      if (event.data?.size > 0) activeCapture.chunks.push(event.data);
    };

    recorder.onerror = () => {
      if (this.activeCapture !== activeCapture) return;
      this.requestStop(activeCapture, "error", false);
      this.setError("recording_failed");
    };

    recorder.onstop = () => {
      this.finalizeCapture(activeCapture, options);
    };

    try {
      recorder.start();
      activeCapture.startedAt = Date.now();
      activeCapture.timer = setTimeout(() => this.stop("max_duration"), durationMs);
    } catch {
      this.activeCapture = null;
      activeCapture.finalized = true;
      stopStreamTracks(stream);
      this.setError("recording_failed");
      return false;
    }

    eventBus.emit({ type: "audio_capture_started", timestamp: now(), duration_ms: durationMs, max_duration_ms: durationMs });
    this.notify();
    return true;
  }

  stop(reason: Extract<VoiceCaptureStopReason, "user_stop" | "max_duration"> = "user_stop") {
    const activeCapture = this.activeCapture;
    if (!activeCapture) return false;
    return this.requestStop(activeCapture, reason, true);
  }

  cancel() {
    const activeCapture = this.activeCapture;
    if (!activeCapture) return false;
    return this.requestStop(activeCapture, "cancelled", false);
  }

  resetForTest() {
    if (this.activeCapture) {
      if (this.activeCapture.timer) clearTimeout(this.activeCapture.timer);
      this.activeCapture.finalized = true;
      stopStreamTracks(this.activeCapture.stream);
    }
    this.activeCapture = null;
    this.listeners.clear();
    this.lastError = null;
    this.lastStopReason = null;
  }

  private requestStop(activeCapture: ActiveCapture, reason: VoiceCaptureStopReason, deliverRecording: boolean) {
    if (this.activeCapture !== activeCapture || activeCapture.stopped || activeCapture.finalized) return false;
    activeCapture.stopped = true;
    activeCapture.stopReason = reason;
    activeCapture.deliverRecording = deliverRecording;
    this.lastStopReason = reason;
    if (activeCapture.timer) clearTimeout(activeCapture.timer);
    eventBus.emit({
      type: "audio_capture_stopped",
      timestamp: now(),
      reason,
      duration_ms: Math.max(0, Date.now() - activeCapture.startedAt)
    });
    this.notify();
    try {
      if (activeCapture.recorder.state !== "inactive") activeCapture.recorder.stop();
    } catch {
      this.releaseCapture(activeCapture);
      this.setError("recording_failed");
      return false;
    }
    return true;
  }

  private finalizeCapture(activeCapture: ActiveCapture, options: AudioCaptureStartOptions) {
    if (activeCapture.finalized) return;
    activeCapture.finalized = true;
    this.releaseCapture(activeCapture);

    const stopReason = activeCapture.stopReason;
    if (!activeCapture.deliverRecording || stopReason === "cancelled" || stopReason === "error") {
      this.notify();
      return;
    }
    if (stopReason !== "user_stop" && stopReason !== "max_duration") {
      this.lastStopReason = "error";
      this.setError("recording_failed");
      return;
    }

    const recordedDurationMs = Math.max(0, Date.now() - activeCapture.startedAt);
    const mimeType = activeCapture.recorder.mimeType || activeCapture.chunks[0]?.type || "audio/webm";
    const blob = new Blob(activeCapture.chunks, { type: mimeType });
    const recording: AudioCaptureRecording = {
      blob,
      durationMs: recordedDurationMs,
      sizeBytes: blob.size,
      mimeType,
      stopReason
    };
    eventBus.emit({
      type: "audio_capture_completed",
      timestamp: now(),
      duration_ms: recording.durationMs,
      size_bytes: recording.sizeBytes,
      mime_type: recording.mimeType,
      stop_reason: recording.stopReason
    });
    options.onRecorded(recording);
    this.notify();
  }

  private releaseCapture(activeCapture: ActiveCapture) {
    if (activeCapture.timer) clearTimeout(activeCapture.timer);
    stopStreamTracks(activeCapture.stream);
    if (this.activeCapture === activeCapture) this.activeCapture = null;
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
