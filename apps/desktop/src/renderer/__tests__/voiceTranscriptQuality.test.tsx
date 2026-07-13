import { describe, expect, it } from "vitest";

import { assessVoiceTranscript, autoSendBlockReasonForQuality } from "../voiceTranscriptQuality";

describe("voice transcript quality", () => {
  it("keeps a normal long sentence as an editable confirm-send draft", () => {
    const assessment = assessVoiceTranscript({
      transcript: "我现在不打玛尔基特了，我准备换去打接肢葛瑞克",
      durationMs: 6200,
      interactionMode: "confirm_send",
      captureStopReason: "user_stop"
    });

    expect(assessment).toMatchObject({ quality: "acceptable", sendDecision: "editable_draft" });
  });

  it("allows direct auto-send only when the quality guard passes", () => {
    const assessment = assessVoiceTranscript({
      transcript: "我准备换一条路线继续打",
      durationMs: 2800,
      interactionMode: "direct_conversation",
      captureStopReason: "user_stop"
    });

    expect(assessment).toMatchObject({ quality: "acceptable", sendDecision: "auto_send_allowed" });
    expect(autoSendBlockReasonForQuality(assessment.quality)).toBeNull();
  });

  it("blocks the partial transcript example in direct conversation", () => {
    const assessment = assessVoiceTranscript({
      transcript: "我现在不打玛尔",
      durationMs: 1800,
      interactionMode: "direct_conversation",
      captureStopReason: "user_stop"
    });

    expect(assessment).toMatchObject({ quality: "suspected_partial", sendDecision: "blocked" });
    expect(autoSendBlockReasonForQuality(assessment.quality)).toBe("partial_transcript");
  });

  it("does not rewrite or semantically guess a plausible but incorrect long transcript", () => {
    const transcript = "我现在不打猫耳机做了去打机";
    const assessment = assessVoiceTranscript({
      transcript,
      durationMs: 3100,
      interactionMode: "confirm_send",
      captureStopReason: "user_stop"
    });

    expect(assessment).toMatchObject({ quality: "acceptable", sendDecision: "editable_draft" });
    expect(transcript).toBe("我现在不打猫耳机做了去打机");
  });

  it.each([
    { transcript: "", durationMs: 1500, quality: "empty", reason: "short_transcript" },
    { transcript: "好", durationMs: 1500, quality: "too_short", reason: "short_transcript" },
    { transcript: "我准备继续挑战", durationMs: 300, quality: "short_recording", reason: "short_recording" },
    { transcript: "我准备继续挑战下一个目标", durationMs: 30_000, quality: "suspected_partial", reason: "partial_transcript", stopReason: "max_duration" },
    { transcript: "啊啊啊啊啊", durationMs: 1800, quality: "suspicious", reason: "suspicious_transcript" }
  ])("blocks $quality transcripts in direct conversation", ({ transcript, durationMs, quality, reason, stopReason }) => {
    const assessment = assessVoiceTranscript({
      transcript,
      durationMs,
      interactionMode: "direct_conversation",
      captureStopReason: stopReason === "max_duration" ? "max_duration" : "user_stop"
    });

    expect(assessment).toMatchObject({ quality, sendDecision: "blocked" });
    expect(autoSendBlockReasonForQuality(assessment.quality)).toBe(reason);
  });
});
