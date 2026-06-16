import { describe, expect, it } from "vitest";

import type { AppSettings } from "../../shared/api";
import {
  buildSpokenAssistantReply,
  VOICE_PROFILE_ID,
  voiceSpeakSkippedReasonText,
  voiceSpokenModeText
} from "../voiceProfile";

const settings = (patch: Partial<AppSettings> = {}): AppSettings =>
  ({
    voice_profile_id: VOICE_PROFILE_ID,
    voice_spoken_reply_mode: "full",
    voice_direct_spoken_reply_mode: "brief",
    voice_speak_proactive: false,
    voice_speak_memory_prompts: false,
    voice_max_spoken_chars: 120,
    voice_max_spoken_sentences: 2,
    ...patch
  }) as AppSettings;

describe("voice profile policy", () => {
  it("allows full assistant replies in normal chat", () => {
    const decision = buildSpokenAssistantReply("别急。先看动作。", settings(), "assistant_reply");

    expect(decision).toMatchObject({
      shouldSpeak: true,
      spokenMode: "full",
      spokenText: "别急。先看动作。",
      spokenCharacterCount: "别急。先看动作。".length,
      sentenceCount: 2,
      excerptCreated: false
    });
  });

  it("uses brief mode by default for direct conversation replies", () => {
    const decision = buildSpokenAssistantReply("第一句。第二句。第三句不会读。", settings(), "direct_conversation");

    expect(decision.shouldSpeak).toBe(true);
    expect(decision.spokenMode).toBe("brief");
    expect(decision.spokenText).toBe("第一句。第二句。");
    expect(decision.excerptCreated).toBe(true);
  });

  it("lets direct conversation use full mode when configured", () => {
    const text = "第一句。第二句。第三句也读。";
    const decision = buildSpokenAssistantReply(text, settings({ voice_direct_spoken_reply_mode: "full" }), "direct_conversation");

    expect(decision).toMatchObject({
      shouldSpeak: true,
      spokenMode: "full",
      spokenText: text,
      excerptCreated: false
    });
  });

  it("skips speech in silent mode", () => {
    const decision = buildSpokenAssistantReply(
      "这句只显示不播报。",
      settings({ voice_direct_spoken_reply_mode: "silent" }),
      "direct_conversation"
    );

    expect(decision).toMatchObject({
      shouldSpeak: false,
      spokenMode: "silent",
      skippedReason: "silent_mode",
      spokenText: ""
    });
  });

  it("trims brief replies to the configured sentence and character limits", () => {
    const decision = buildSpokenAssistantReply(
      "这是一句很长很长的中文回复，需要被截短，否则播报会显得太啰嗦也太像攻略，还会打断玩家正在观察动作节奏。第二句不会读。第三句也不会读。",
      settings({ voice_direct_spoken_reply_mode: "brief", voice_max_spoken_chars: 40, voice_max_spoken_sentences: 1 }),
      "direct_conversation"
    );

    expect(decision.spokenText.length).toBeLessThanOrEqual(40);
    expect(decision.spokenText.endsWith("…")).toBe(true);
    expect(decision.sentenceCount).toBe(1);
    expect(decision.excerptCreated).toBe(true);
  });

  it("removes code blocks and inline code before speaking", () => {
    const decision = buildSpokenAssistantReply(
      "先这样做。\n```ts\nconst roll = 1;\n```\n然后重试 `npm test`。",
      settings(),
      "assistant_reply"
    );

    expect(decision.shouldSpeak).toBe(true);
    expect(decision.spokenText).toBe("先这样做。\n然后重试 。");
    expect(decision.spokenText).not.toContain("const roll");
    expect(decision.spokenText).not.toContain("npm test");
    expect(decision.excerptCreated).toBe(true);
  });

  it("skips JSON and trace-like structured content", () => {
    expect(buildSpokenAssistantReply('{"trace": "hidden"}', settings(), "assistant_reply")).toMatchObject({
      shouldSpeak: false,
      skippedReason: "structured_content"
    });
    expect(buildSpokenAssistantReply("Trace: raw internal detail", settings(), "assistant_reply")).toMatchObject({
      shouldSpeak: false,
      skippedReason: "structured_content"
    });
  });

  it("skips unsafe internal content", () => {
    const decision = buildSpokenAssistantReply("raw prompt 包含 /Users/aragoto/.env", settings(), "assistant_reply");

    expect(decision).toMatchObject({
      shouldSpeak: false,
      skippedReason: "unsafe_content"
    });
  });

  it("keeps proactive and memory prompts quiet by default", () => {
    expect(buildSpokenAssistantReply("主动陪伴提示。", settings(), "proactive")).toMatchObject({
      shouldSpeak: false,
      skippedReason: "proactive_disabled"
    });
    expect(buildSpokenAssistantReply("记忆确认提示。", settings(), "memory_prompt")).toMatchObject({
      shouldSpeak: false,
      skippedReason: "memory_prompt_disabled"
    });
  });

  it("exposes stable Chinese labels for UI and events", () => {
    expect(voiceSpokenModeText("brief")).toBe("短版播报");
    expect(voiceSpeakSkippedReasonText("debug_content")).toBe("调试内容不播报");
  });
});
