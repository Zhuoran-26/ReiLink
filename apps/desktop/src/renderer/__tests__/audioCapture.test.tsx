import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  AudioCaptureController,
  DEFAULT_RECORDING_DURATION_MS,
  MAX_RECORDING_DURATION_MS,
  type AudioCaptureRecording
} from "../audioCapture";
import { eventBus } from "../eventBus";

class DeferredMediaRecorder {
  static instances: DeferredMediaRecorder[] = [];
  static isTypeSupported = vi.fn(() => true);

  state: RecordingState = "inactive";
  mimeType: string;
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onstop: (() => void) | null = null;
  start = vi.fn(() => {
    this.state = "recording";
  });
  stop = vi.fn(() => {
    this.state = "inactive";
  });

  constructor(_stream: MediaStream, options?: MediaRecorderOptions) {
    this.mimeType = options?.mimeType || "audio/webm";
    DeferredMediaRecorder.instances.push(this);
  }

  emitChunk(content: string) {
    this.ondataavailable?.({ data: new Blob([content], { type: this.mimeType }) } as BlobEvent);
  }

  finishStop() {
    this.onstop?.();
  }
}

const installCaptureEnvironment = () => {
  const stopTrack = vi.fn();
  const stream = { getTracks: vi.fn(() => [{ stop: stopTrack }]) } as unknown as MediaStream;
  const getUserMedia = vi.fn(async () => stream);
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia }
  });
  vi.stubGlobal("MediaRecorder", DeferredMediaRecorder);
  return { getUserMedia, stopTrack };
};

describe("AudioCaptureController", () => {
  beforeEach(() => {
    DeferredMediaRecorder.instances = [];
    eventBus.clear();
    installCaptureEnvironment();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    Reflect.deleteProperty(navigator, "mediaDevices");
    eventBus.clear();
  });

  it("waits for the final audio chunk before delivering a user-stopped recording", async () => {
    const controller = new AudioCaptureController();
    const onRecorded = vi.fn<(recording: AudioCaptureRecording) => void>();

    await controller.start({ onRecorded });
    const recorder = DeferredMediaRecorder.instances[0];
    recorder.emitChunk("first");

    controller.stop("user_stop");

    expect(controller.getStatus().phase).toBe("stopping");
    expect(onRecorded).not.toHaveBeenCalled();

    recorder.emitChunk("final");
    expect(onRecorded).not.toHaveBeenCalled();
    recorder.finishStop();

    expect(onRecorded).toHaveBeenCalledTimes(1);
    expect(onRecorded.mock.calls[0][0]).toMatchObject({
      sizeBytes: 10,
      stopReason: "user_stop",
      mimeType: "audio/webm"
    });
    expect(controller.getStatus()).toMatchObject({ phase: "idle", lastStopReason: "user_stop" });
  });

  it("measures capture duration at the stop request instead of delayed recorder finalization", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-07-13T00:00:00.000Z"));
    const controller = new AudioCaptureController();
    const onRecorded = vi.fn<(recording: AudioCaptureRecording) => void>();

    await controller.start({ onRecorded });
    const recorder = DeferredMediaRecorder.instances[0];
    vi.advanceTimersByTime(320);
    controller.stop("user_stop");

    vi.advanceTimersByTime(2000);
    recorder.emitChunk("delayed-final-chunk");
    recorder.finishStop();

    expect(onRecorded).toHaveBeenCalledTimes(1);
    expect(onRecorded.mock.calls[0][0].durationMs).toBe(320);
    expect(eventBus.getRecentEvents()).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ type: "audio_capture_stopped", duration_ms: 320 }),
        expect.objectContaining({ type: "audio_capture_completed", duration_ms: 320 })
      ])
    );
  });

  it("honors an immediate stop requested while microphone permission is still resolving", async () => {
    const stopTrack = vi.fn();
    const stream = { getTracks: vi.fn(() => [{ stop: stopTrack }]) } as unknown as MediaStream;
    const deferred = { resolve: null as ((stream: MediaStream) => void) | null };
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn(() => new Promise<MediaStream>((resolve) => {
          deferred.resolve = resolve;
        }))
      }
    });
    const controller = new AudioCaptureController();
    const onRecorded = vi.fn<(recording: AudioCaptureRecording) => void>();

    const startPromise = controller.start({ onRecorded });
    expect(controller.stop("user_stop")).toBe(true);
    deferred.resolve?.(stream);
    await startPromise;

    const recorder = DeferredMediaRecorder.instances[0];
    expect(recorder.stop).toHaveBeenCalledTimes(1);
    expect(controller.getStatus()).toMatchObject({ phase: "stopping", lastStopReason: "user_stop" });
    recorder.emitChunk("short-audio");
    recorder.finishStop();

    expect(onRecorded).toHaveBeenCalledTimes(1);
    expect(onRecorded.mock.calls[0][0]).toMatchObject({ stopReason: "user_stop" });
    expect(onRecorded.mock.calls[0][0].durationMs).toBeLessThan(800);
  });

  it("keeps recording through a long sentence and natural pause", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-07-13T00:00:00.000Z"));
    const controller = new AudioCaptureController();
    const onRecorded = vi.fn();

    await controller.start({ onRecorded });
    const recorder = DeferredMediaRecorder.instances[0];

    vi.advanceTimersByTime(5000);
    expect(recorder.stop).not.toHaveBeenCalled();
    expect(controller.getStatus().phase).toBe("recording");

    vi.advanceTimersByTime(10_000);
    expect(recorder.stop).not.toHaveBeenCalled();
    expect(onRecorded).not.toHaveBeenCalled();

    controller.cancel();
    recorder.finishStop();
  });

  it("uses a 30 second safety limit and still waits for the final chunk", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-07-13T00:00:00.000Z"));
    const controller = new AudioCaptureController();
    const onRecorded = vi.fn<(recording: AudioCaptureRecording) => void>();

    expect(DEFAULT_RECORDING_DURATION_MS).toBe(30_000);
    expect(MAX_RECORDING_DURATION_MS).toBe(30_000);
    await controller.start({ onRecorded });
    const recorder = DeferredMediaRecorder.instances[0];
    recorder.emitChunk("before-limit");

    vi.advanceTimersByTime(29_999);
    expect(recorder.stop).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);

    expect(recorder.stop).toHaveBeenCalledTimes(1);
    expect(controller.getStatus()).toMatchObject({ phase: "stopping", lastStopReason: "max_duration" });
    expect(onRecorded).not.toHaveBeenCalled();

    recorder.emitChunk("final");
    recorder.finishStop();

    expect(onRecorded.mock.calls[0][0]).toMatchObject({
      sizeBytes: 17,
      stopReason: "max_duration"
    });
    expect(eventBus.getRecentEvents()).toContainEqual(expect.objectContaining({
      type: "audio_capture_completed",
      stop_reason: "max_duration"
    }));
  });

  it("cancels without delivering audio for ASR", async () => {
    const controller = new AudioCaptureController();
    const onRecorded = vi.fn();

    await controller.start({ onRecorded });
    const recorder = DeferredMediaRecorder.instances[0];
    recorder.emitChunk("discard-me");
    controller.cancel();
    recorder.emitChunk("final-discarded");
    recorder.finishStop();

    expect(onRecorded).not.toHaveBeenCalled();
    expect(controller.getStatus()).toMatchObject({ phase: "idle", lastStopReason: "cancelled" });
    expect(eventBus.getRecentEvents()).toContainEqual(expect.objectContaining({
      type: "audio_capture_stopped",
      reason: "cancelled"
    }));
    expect(eventBus.getRecentEvents().some((event) => event.type === "audio_capture_completed")).toBe(false);
  });
});
