import { describe, expect, it } from "vitest";

import { assessVoiceTranscript } from "../voiceTranscriptQuality";

describe("voice transcript quality", () => {
  it("keeps a normal long sentence as an editable confirm-send draft", () => {
    const assessment = assessVoiceTranscript({
      transcript: "我现在不打玛尔基特了，我准备换去打接肢葛瑞克",
      durationMs: 6200,
      interactionMode: "confirm_send",
      captureStopReason: "user_stop"
    });

    expect(assessment).toMatchObject({
      quality: "acceptable",
      sendDecision: "editable_draft",
      autoSendBlockReason: null
    });
  });

  it("allows the acceptance sentence through the Direct Conversation guard", () => {
    const assessment = assessVoiceTranscript({
      transcript: "我今天准备先在史东薇尔城附近探索一会儿",
      durationMs: 2800,
      interactionMode: "direct_conversation",
      captureStopReason: "user_stop"
    });

    expect(assessment).toMatchObject({
      quality: "acceptable",
      sendDecision: "auto_send_allowed",
      autoSendBlockReason: null
    });
  });

  it("blocks the real ASR partial transcript even when the ellipsis was lost", () => {
    const assessment = assessVoiceTranscript({
      transcript: "我等您下准备去",
      durationMs: 1800,
      interactionMode: "direct_conversation",
      captureStopReason: "user_stop"
    });

    expect(assessment).toMatchObject({
      quality: "suspected_partial",
      sendDecision: "blocked",
      autoSendBlockReason: "suspected_partial"
    });
  });

  it("does not rewrite or semantically guess a plausible but incorrect long transcript", () => {
    const transcript = "我现在不打猫耳机做了去打机";
    const assessment = assessVoiceTranscript({
      transcript,
      durationMs: 3100,
      interactionMode: "confirm_send",
      captureStopReason: "user_stop"
    });

    expect(assessment).toMatchObject({
      quality: "acceptable",
      sendDecision: "editable_draft",
      autoSendBlockReason: null
    });
    expect(transcript).toBe("我现在不打猫耳机做了去打机");
  });

  it.each([
    { transcript: "", durationMs: 1500, quality: "empty", reason: "empty_transcript" },
    { transcript: "嗯", durationMs: 1500, quality: "too_short", reason: "transcript_too_short" },
    { transcript: "幻觉出来的长转写内容", durationMs: 300, quality: "short_recording", reason: "recording_too_short" },
    { transcript: "我准备继续挑战下一个目标", durationMs: 30_000, quality: "suspected_partial", reason: "max_duration", stopReason: "max_duration" },
    { transcript: "啊啊啊啊啊", durationMs: 1800, quality: "suspicious", reason: "suspicious_transcript" }
  ])("blocks $quality transcripts in direct conversation", ({ transcript, durationMs, quality, reason, stopReason }) => {
    const assessment = assessVoiceTranscript({
      transcript,
      durationMs,
      interactionMode: "direct_conversation",
      captureStopReason: stopReason === "max_duration" ? "max_duration" : "user_stop"
    });

    expect(assessment).toMatchObject({ quality, sendDecision: "blocked", autoSendBlockReason: reason });
  });

  it.each(["(字幕:J Chong)", "(拍摄)", "[Music]", "字幕: J Chong", "Narrator:"])(
    "blocks the caption or speaker-label-only transcript %s",
    (transcript) => {
      const assessment = assessVoiceTranscript({
        transcript,
        durationMs: 1800,
        interactionMode: "direct_conversation",
        captureStopReason: "user_stop"
      });

      expect(assessment).toMatchObject({
        quality: "non_speech_caption",
        sendDecision: "blocked",
        autoSendBlockReason: "non_speech_caption"
      });
    }
  );

  it("does not over-block a natural sentence that contains parenthetical detail", () => {
    const assessment = assessVoiceTranscript({
      transcript: "我今天准备去城堡（从正门进去）探索一会儿",
      durationMs: 2800,
      interactionMode: "direct_conversation",
      captureStopReason: "user_stop"
    });

    expect(assessment).toMatchObject({
      quality: "acceptable",
      sendDecision: "auto_send_allowed",
      autoSendBlockReason: null
    });
  });

  it("keeps a blocked caption as an editable confirm-send draft", () => {
    const assessment = assessVoiceTranscript({
      transcript: "(拍摄)",
      durationMs: 1800,
      interactionMode: "confirm_send",
      captureStopReason: "user_stop"
    });

    expect(assessment).toMatchObject({
      quality: "non_speech_caption",
      sendDecision: "editable_draft",
      autoSendBlockReason: "non_speech_caption"
    });
  });
});
