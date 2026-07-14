# ReiLink Voice v2.2 — Direct Conversation & TTS Foundation

Draft: 2026-07-14

Candidate tag: `reilink-v0.2-pre.5`

Document status: draft release note. This file does not create a Git tag, GitHub Release, push, merge, or rebase.

## Summary

Voice v2.2 consolidates ReiLink's user-triggered Local ASR, conservative transcript review, opt-in Direct Conversation, nine-state Voice model, Voice Profile, interruptible system speech, TTS provider capability surface, and privacy-safe Event Stream into one release candidate. The title is consistent with the delivered scope: this is a Direct Conversation and TTS foundation, not an always-listening real-time voice agent or a new production TTS provider.

## Highlights

- Main-chat capture now follows `start -> user_stop or 30-second safety limit -> stopping -> final dataavailable / onstop -> complete Blob -> Local ASR`. It has no Web Audio VAD, silence detection, or old 3-second / 5-second hard stop; the separate Audio Capture Probe keeps its independent 3-second test.
- Capture stop reasons are `user_stop`, `max_duration`, `cancelled`, and `error`. Immediate Stop while microphone permission is pending is queued, final chunks are retained, and the Direct Conversation duration uses the actual start-to-Stop interval rather than delayed teardown or backend echo.
- `confirm_send` remains the default. A Local ASR transcript first becomes an editable, unsent draft that can be changed, cleared, or replaced by another recording. Before send, it is not LLM understanding and does not run Semantic Extraction or update Game Context, Memory, or Boss state.
- Direct Conversation remains explicit opt-in and user-triggered for every round. Disabling it during capture or transcription returns that round to confirm-send and never sends an existing draft.
- Local ASR auto-send requires `user_stop` and quality `acceptable`; a Web Speech final transcript has no MediaRecorder stop reason but still passes the remaining text guards. Empty text, fewer than four lexical characters, Local ASR recordings under 800 ms, 30-second max-duration captures, caption / speaker-label / stage-direction-only output, bounded suspected partials, and mechanically suspicious output are blocked. Non-empty blocked text remains editable; blocked input starts no chat request, extraction, memory, proactive, Game Context, Boss update, or Rei reply.
- Nine visible states remain `idle`, `listening`, `transcribing`, `auto_sending`, `ready_to_send`, `assistant_thinking`, `speaking`, `interrupted`, and `error`.
- Voice Profile `rei_calm` supports normal-chat `full`, deterministic Direct Conversation `brief`, and `silent` without removing the full text reply.
- Test Voice, Stop Voice, active-playback interruption, and recording / speaking mutual exclusion remain supported.
- TTS Provider Registry v0 exposes `system_speech_synthesis` as the only enabled and selectable provider. `local_tts` is disabled / `not_implemented`; `external_tts` is disabled / `not_configured`.
- The GameCatalog clean-context regression is fixed: generic `探索` knowledge aliases can no longer bootstrap Hollow Knight. Only bounded Boss / location entity aliases can bootstrap a canonical game without context. Exact `史东薇尔` still resolves Elden Ring, and explicit `我现在换去玩空洞骑士` still switches correctly.

## GameCatalog Fix Boundary

The erroneous Hollow Knight switch was not caused by Voice mode, Persona, or an LLM candidate. The root cause was a generic `探索` alias in GameCatalog knowledge metadata being treated as canonical-game bootstrap evidence with no current context. The fix restricts that bootstrap to more reliable Boss / location entity aliases. It does not add a `石东威尔` typo alias and does not change the ASR provider, Persona prompt, or LLM provider.

## Privacy

- Captured audio is transferred only to ReiLink's local backend for user-configured Local ASR. No cloud ASR or cloud audio-upload path is integrated.
- Temporary audio is not a durable product data type and is cleaned by the Local ASR path after success, failure, or timeout, with safe cleanup status.
- Voice / TTS Event Stream payloads may store capture duration, audio-format summary, stop reason, quality, send decision, source / mode, provider / status / profile, fallback flag, safe guard reason, and counts.
- They do not store full transcript text, raw ASR output, raw audio, full assistant replies, spoken text, Test Voice text, raw prompts, raw provider config, API keys, Authorization data, environment files, user-specific absolute paths, raw stdout / stderr, or raw JSON dumps.
- ReiLink delegates selected TTS text to the platform `speechSynthesis` implementation. ReiLink does not integrate an external TTS endpoint or TTS API key; this is an application-boundary statement, not an undocumented platform privacy guarantee.

## Known Limitations

- Local ASR quality and latency depend on the user-managed model, microphone, accent, noise, and hardware. Game terminology, long Chinese sentences, and noisy speech can still be misrecognized.
- The current Local ASR response exposes no renderer-usable no-speech probability, segment confidence, or average log probability. ReiLink does not invent confidence metadata.
- Direct Conversation partial-utterance detection is bounded and best-effort, not semantic endpointing. ASR can drop punctuation, change wording, or make incomplete speech look complete, so some unfinished utterances may still auto-send.
- The guard will not expand through open-ended sentence-final regexes, unlimited keyword lists, or typo aliases to chase every observed edge case. Use default `confirm_send` when every transcript must be reviewed.
- Caption protection is finite transcript-structure detection, not audio VAD. `(字幕:J Chong)`, `(拍摄)`, `[Music]`, and bare speaker labels are conservatively blocked; a real natural utterance fully enclosed in brackets can also be blocked and remains manually editable.
- Every recording round requires a user action. There is no hands-free, always-listening, wake-word, automatic next-round, streaming-ASR, or full-duplex loop.
- System speech is not character-grade and may pronounce names or game terminology unnaturally. Stop / interrupt is best-effort through platform speech cancellation.
- No local neural TTS, production external TTS, streaming TTS, custom character voice, voice cloning, speaker diarization, cloud audio upload, or Overlay Voice state is included.
- Streaming ASR, VAD, endpointing, partial / final transcript signals, and turn-taking require a separately scoped future design.

## QA Evidence Boundaries

- Automated tests cover state, capture lifecycle, guard reasons, side effects, provider fallback, and privacy assertions.
- Simulated MediaRecorder covers final chunks, delayed `onstop`, actual duration, pending microphone permission, and the 30-second timer; it is not a real microphone result.
- Controlled transcripts cover empty / short / caption / partial / mode-switch and GameCatalog decisions; they do not prove the ASR model generated those strings.
- System-speech rerecord exercises a near-real local audio path but is not a complete human-microphone, accent, physical tapping, or ambient-noise acceptance.
- Real microphone and user-manual results must be reported separately from the above methods.
- Detailed release gates and reusable evidence rules live in `docs/release_voice_v2_2_hardening_checklist.md`; machine-readable mapping lives in `docs/qa/voice_v2_2_release_matrix.json`.

## Upgrade / Compatibility Notes

- Existing settings remain compatible; missing interaction-mode settings default to `confirm_send`.
- Voice Output remains optional and does not implicitly enable Direct Conversation.
- Existing Local ASR binary, model, and converter settings remain user-managed and outside the packaged app.
- Invalid or disabled TTS provider ids safely resolve to System Speech Synthesis; if system speech is unavailable, the text reply remains visible and playback no-ops.

## Not Included

- No new TTS provider, backend provider service, network request, API key surface, model download, ASR provider replacement, Persona change, or source-specific extraction path.
- No hands-free, wake word, audio streaming, cloud audio upload, speaker diarization, full duplex, or voice cloning.
- No Overlay expansion, Live2D, Vision, Memory feature, proactive behavior, game-session core, knowledge core, or model-routing change.

## Release Boundary

This draft records the local Voice v2.2 candidate only. Publishing, creating `reilink-v0.2-pre.5`, creating a GitHub Release, pushing, merging, or rebasing remains a separate project-owner action.
