# ReiLink Voice v2.2 — Direct Conversation & TTS Foundation

Draft: 2026-07-12

Document status: draft release note. This file does not create a Git tag, GitHub Release, push, merge, or rebase.

## Summary

Voice v2.2 consolidates ReiLink's user-triggered Local ASR, default transcript confirmation, opt-in Direct Conversation, Voice state model, Voice Profile, interruptible system speech, provider capability surface, and privacy-safe Event Stream into one release-ready baseline. It remains a restrained game-companion voice loop rather than an always-listening real-time voice agent.

## Highlights

- Nine visible states: `idle`, `listening`, `transcribing`, `auto_sending`, `ready_to_send`, `assistant_thinking`, `speaking`, `interrupted`, and `error`.
- Conservative `confirm_send` default with editable transcript review.
- Explicit Direct Conversation opt-in that auto-sends only after a user-triggered recording passes empty-text, short-text, short-recording, and likely-partial guards.
- Full text chat remains the source of truth; voice-origin turns use the same chat, memory, knowledge, game-context, persona, and provider safety path.
- Voice Profile `rei_calm` supports normal-chat `full`, deterministic Direct Conversation `brief`, and `silent` without removing the text reply.
- Test Voice, Stop Voice, active-playback interruption, and recording / speaking mutual exclusion.
- TTS Provider Registry v0 exposes System Speech Synthesis as the only enabled and selectable provider.
- Local TTS and External TTS remain disabled capability placeholders.
- Release-level QA matrix and reusable automated / manual / packaged hardening checklist.

## Privacy

- Captured audio is transferred only to ReiLink's local backend for user-configured Local ASR. No cloud ASR or cloud audio-upload path is integrated.
- Temporary audio is not a durable product data type and is cleaned by the Local ASR path after success, failure, or timeout, with safe cleanup status.
- Voice / TTS Event Stream payloads store safe lifecycle metadata and counts, not full transcript text, assistant replies, spoken text, or Test Voice text.
- Voice / TTS events exclude raw ASR output, raw prompt, persona markdown, raw JSON, local absolute paths, raw stdout / stderr, provider raw config, environment files, credentials, and authorization data.
- ReiLink delegates selected TTS text to the platform `speechSynthesis` implementation. ReiLink does not integrate an external TTS endpoint or TTS API key; this statement does not make an undocumented platform privacy guarantee.

## Limitations

- Every recording round requires a user action. There is no hands-free, always-listening, wake-word, or automatic next-round loop.
- Local ASR requires user-managed binary, model, and converter configuration.
- ASR quality and latency depend on the local model, microphone, noise, and hardware.
- System speech is not character-grade and may pronounce names or game terminology unnaturally.
- Stop / interrupt is best-effort through platform speech cancellation.
- No speaker diarization, local neural TTS, external / streaming TTS provider, custom character voice, voice cloning, cloud audio upload, or Overlay Voice state.

## Testing

- Desktop lint, renderer / main tests, and production build are required.
- Full backend pytest is recommended even when backend runtime is unchanged.
- Repository safety scan must return no secret-like token match.
- Runtime / UI / shared / backend changes require `make package-backend`, `make package-desktop`, and packaged `.app` smoke.
- Detailed gates live in `docs/release_voice_v2_2_hardening_checklist.md`.
- Machine-readable release mapping lives in `docs/qa/voice_v2_2_release_matrix.json`.
- Extraction live eval and Persona-Memory live eval are not required for this release hardening because Voice v2.2 does not change semantic extraction, model routing, persona assembly, memory retrieval, or Persona-Memory behavior. Existing runner tests remain part of backend pytest.

## Upgrade / Compatibility Notes

- Existing settings remain compatible; missing interaction-mode settings continue to default to `confirm_send`.
- Voice Output remains optional and defaults to the existing safe behavior.
- Existing Local ASR binary, model, and converter settings remain user-managed and outside the packaged app.
- Direct Conversation is never enabled implicitly by Local ASR readiness, Voice Output, or opening the Voice workspace.
- Invalid or disabled TTS provider ids safely resolve to System Speech Synthesis; if system speech is unavailable, the text reply remains visible and playback no-ops.

## Not Included

- No new TTS provider, backend provider service, network request, API key surface, or model download.
- No hands-free, wake word, audio streaming, cloud audio upload, speaker diarization, or voice cloning.
- No Overlay expansion, Live2D, Vision, Memory feature, persona prompt, proactive behavior, game-session core, knowledge core, or model-routing change.

## Release Boundary

This draft records the local Voice v2.2 readiness baseline only. Publishing, tagging, pushing, merging, or rebasing remains a separate project-owner action.
