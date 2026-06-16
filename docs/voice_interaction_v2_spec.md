# Voice Interaction v2 Spec

Updated: 2026-06-16

Status: v2.1 implemented. The renderer now has a typed Voice v2 conversation state model, Home / Chat compact state display, Voice workspace Conversation state panel, confirm-send transcript flow, opt-in Direct Conversation Mode, TTS interruption, and speaking / listening mutual exclusion. This does not implement hands-free listening, a new TTS engine, character voice, Overlay auto-show, memory architecture, Live2D, or vision.

## Purpose

Voice Interaction v2 defines the direct conversation loop for ReiLink:

```text
user speaks
-> local ASR transcribes
-> transcript is confirmed or explicitly auto-sent
-> assistant thinks
-> assistant reply may be spoken
-> user can interrupt and speak again
```

The goal is a calmer game companion loop, not a voice assistant that constantly listens or acts on uncertain transcripts. The default remains conservative: user-triggered recording, local ASR, transcript confirmation, and no automatic memory write from unconfirmed speech.

## Current Baseline

Implemented today:

- Voice v2.1 resolves `idle`, `listening`, `transcribing`, `ready_to_send`, `assistant_thinking`, `speaking`, `interrupted`, and `error` from current renderer voice signals.
- Home / Chat shows compact Chinese-first Voice v2 state near the composer without hiding normal text input.
- Voice workspace Conversation tab shows state, mode, transcript confirmation, output status, interruption and privacy boundaries.
- Voice interaction mode is explicit: `confirm_send` is the default, and `direct_conversation` is opt-in.
- Local ASR v1 can record and transcribe after a user gesture.
- ASR uses user-configured local binaries, model files, and optional converter paths.
- Audio is sent only to the local backend.
- Under `confirm_send`, transcript fills the chat input and is not auto-sent.
- Under `direct_conversation`, the transcript is auto-sent through the existing chat flow after the user actively starts and stops a recording round.
- Unconfirmed transcript does not enter memory, prompt, knowledge retrieval, game context, Semantic Extraction, or proactive behavior.
- Voice Output uses renderer-side `speechSynthesis`.
- Voice Output can be enabled, tested, stopped, and tuned with rate / volume; in `direct_conversation`, assistant replies are spoken automatically only when Voice Output is enabled.
- Starting voice input stops active TTS first, and Stop Voice enters a short interrupted state.

Voice v2 should build on these boundaries instead of bypassing them.

## Goals

- Define a state machine for direct voice conversation.
- Preserve Local ASR as the stable main input path.
- Keep confirm-send as the default transcript policy.
- Allow Direct Conversation Mode only as an explicit opt-in with clear state visibility.
- Make TTS playback after assistant replies predictable and interruptible.
- Prevent recording and speaking from conflicting.
- Keep game-mode speech short, low-interruption, and safe.
- Keep internal diagnostics, prompt preview, traces, and memory internals out of spoken output.
- Provide clear error states for ASR, microphone, TTS, and provider failures.
- Define where Voice state appears in Voice workspace, Home / Chat, and future Overlay.

## Non-Goals

- Do not make this foundation a full hands-free direct voice conversation mode.
- Do not make auto-send the default.
- Do not imply direct conversation from enabling ASR, Voice Output, or opening Voice workspace.
- Do not enable hands-free or wake-word listening by default.
- Do not add cloud ASR or commercial ASR.
- Do not bundle whisper binaries, model files, or ffmpeg.
- Do not add a new TTS engine or character voice.
- Do not make Voice automatically write memory.
- Do not let Voice automatically trigger proactive behavior.
- Do not restore Overlay auto-show.
- Do not implement Live2D, avatar runtime, vision, or game-screen understanding.

## Mode Model

Voice v2 has three independent mode choices. The UI should show these as explicit state, not hidden behavior.

| Area | Default | Future Options | Notes |
| --- | --- | --- | --- |
| Input trigger | Push-to-talk / click-to-record | Hands-free / auto-listen later | Hands-free must remain off until a separate task defines permission, timeout, and game-mode risk. |
| Send policy | Confirm-send | Direct Conversation as explicit opt-in | Confirm-send keeps current safety. Direct Conversation must never be implied by enabling ASR or Voice Output. |
| Output policy | Speak only when Voice Output is enabled | Short spoken summary mode later | TTS should speak assistant content only, never Debug, Prompt Preview, trace, or raw internals. |

### Input Modes

`push_to_talk`

- User holds or explicitly activates recording.
- Recording stops when the user releases or clicks stop.
- Best for game sessions because it is intentional and low risk.

`click_to_record`

- User clicks once to begin and clicks again to stop, with a maximum duration.
- Useful when holding a key is inconvenient.
- Still requires a visible listening state and a safe timeout.

`hands_free`

- Future optional mode only.
- Must not be enabled by default.
- Requires a separate implementation plan covering ambient listening, false starts, silence detection, privacy copy, and visible state.

### Send Policies

`confirm_send`

- Default policy.
- ASR transcript enters `ready_to_send`.
- The user can edit, delete, or send it.
- Until the user sends, the transcript remains outside memory, prompt, retrieval, game context, Semantic Extraction, and proactive checks.

`direct_conversation`

- Implemented explicit opt-in.
- Requires a visible mode indicator and a clear off switch.
- Still requires a user gesture for each recording round; it is not hands-free, wake-word, or always-on listening.
- Auto-sends only non-empty ASR transcripts through the normal chat request path.
- Does not write memory directly; any memory still goes through the existing confirmation flow after the normal chat turn.
- Does not bypass normal chat, retrieval, or game-state safety checks after the text is sent.
- Does not leak the full transcript into Event Stream, Debug, Raw JSON, Prompt Preview, or Overlay.

### Output Policies

`tts_off`

- Assistant replies are text-only.

`tts_full_reply`

- If Voice Output is enabled, speak the final assistant reply after it completes.
- Do not speak partial streaming chunks unless a later task designs it.

`tts_short_reply`

- Future game-mode option.
- Speak a short safe sentence derived from the assistant reply while keeping the full text in chat.
- This should be implemented with LLM-first generation or a safe summarization policy, not hardcoded Rei lines.

## State Machine

Recommended states:

| State | Meaning | Entry | Exit |
| --- | --- | --- | --- |
| `idle` | Voice loop is available but inactive. | App start, stop, completion, or recovery. | User starts recording or TTS starts after an assistant reply. |
| `listening` | User-triggered recording is active. | Push-to-talk or click-to-record begins. | User stops, max duration, mic error, or recording failure. |
| `transcribing` | Local ASR is processing the captured audio. | Recording finished and Local ASR request starts. | Transcript ready, no text, timeout, or ASR error. |
| `ready_to_send` | Transcript is available for confirmation. | ASR succeeds under confirm-send. | User sends, edits, clears, records again, or switches mode. |
| `assistant_thinking` | A confirmed or directly sent transcript is in the normal chat request path. | User sends transcript or Direct Conversation auto-send fires. | Assistant final reply, provider error, cancellation, or timeout. |
| `speaking` | TTS is playing a safe assistant reply. | Final assistant reply arrives and Voice Output is enabled. | TTS completes, user stops, user starts recording, or TTS error. |
| `interrupted` | Speaking or listening was intentionally stopped. | User presses stop, starts recording during TTS, or cancels recording. | Return to `idle`, `listening`, or `ready_to_send` depending on remaining transcript. |
| `error` | A user-visible recoverable voice error occurred. | Mic, ASR, converter, TTS, or provider failure. | User retries, edits transcript, changes settings, or dismisses. |

### Transition Rules

- `idle -> listening`: only after a user gesture.
- `listening -> transcribing`: only after audio capture completes.
- `transcribing -> ready_to_send`: ASR succeeds and send policy is `confirm_send`.
- `transcribing -> assistant_thinking`: ASR succeeds and send policy is explicit `direct_conversation`.
- `ready_to_send -> assistant_thinking`: user confirms by sending.
- `assistant_thinking -> speaking`: assistant final reply exists and Voice Output is enabled.
- `assistant_thinking -> idle`: assistant final reply exists and Voice Output is disabled.
- `speaking -> interrupted`: user stops speech or starts recording.
- `speaking -> listening`: user starts a new recording; TTS must stop first.
- Any state -> `error`: recoverable failure.
- `error -> idle`: user dismisses or retries after state reset.

### State Invariants

- `listening` and `speaking` must be mutually exclusive.
- Entering `listening` must stop active TTS.
- Entering `speaking` must require no active recording.
- `transcribing` must not write prompt, memory, retrieval, game context, or proactive state.
- `ready_to_send` must not write prompt, memory, retrieval, game context, or proactive state.
- `assistant_thinking` only starts after a confirmed send or explicit Direct Conversation auto-send.
- `interrupted` is a user action summary, not an error by itself.

## Transcript Policy

Before confirmation in `confirm_send`:

- Do not write memory.
- Do not create pending memory.
- Do not inject into prompt.
- Do not run knowledge retrieval.
- Do not run game context extraction.
- Do not trigger proactive behavior.
- Do not show the full transcript in Event Stream, Debug, Prompt Preview, Raw JSON, or Overlay.

After confirmation or Direct Conversation auto-send:

- The text enters the existing chat flow as normal user input.
- Existing memory confirmation, knowledge retrieval, game context, Semantic Extraction, and proactive gates continue to apply.
- Voice should not introduce a separate memory or game-state path.
- Direct Conversation events may show mode, provider, and character count, but not the full transcript.

Empty or low-confidence transcript:

- Return to `idle` or `ready_to_send` with a safe message such as `没有识别到可用文本`.
- Do not auto-send empty text.
- Do not overwrite existing unsent chat draft unless the user explicitly accepts replacement.

## Speaking Policy

TTS may speak only safe assistant-facing output:

- Assistant final replies.
- Test Voice text.
- Future short spoken summaries derived from assistant replies.

TTS must not speak:

- Debug output.
- Prompt Preview.
- Event Stream.
- Semantic Shadow trace.
- Knowledge raw snippets.
- Memory internals or pending memory evidence.
- Raw prompt.
- Raw provider response.
- Full ASR transcript before confirmation.
- API keys, `.env`, Authorization headers, full local paths, stdout, or stderr.

TTS interruption:

- Stop active TTS when the user starts recording.
- Stop active TTS when the user clicks Stop Voice.
- Do not replay interrupted speech automatically.
- Record a safe lifecycle summary such as `语音播放已停止`, without full reply text.

## Game-Mode Behavior

Voice v2 should feel useful while the player is focused on the game screen.

- Prefer short spoken replies.
- Avoid long strategy monologues unless the user explicitly asks.
- Let full detail stay in chat text when needed.
- Avoid reading lists, debug labels, raw state, or prompt summaries aloud.
- Keep Rei's style quiet, restrained, low-emotion, and lightly caring.
- Do not hardcode Rei replies; use the normal LLM-first reply path.
- If the user interrupts, treat it as normal game flow, not failure.

Future `tts_short_reply` should prioritize one or two spoken sentences for:

- reassurance after repeated failure,
- a concise tactical hint,
- confirmation that Rei heard the user,
- a brief transition such as stopping speech or returning to listening.

## UI Requirements

### Voice Workspace

Conversation tab now shows the foundation state surface:

- current Voice state,
- input trigger mode,
- send policy,
- output policy,
- active transcript confirmation summary under confirm-send,
- Direct Conversation mode switch and opt-in summary,
- TTS playing / stopped / interrupted state,
- short friendly error messages,
- safe mode notes for hands-free and Direct Conversation.

Future tasks may add richer clear / retry / send controls here, but the normal chat composer remains the canonical transcript editing and send surface.

Input / Local ASR tab should keep:

- Local ASR readiness,
- binary / model / converter setup,
- Check Local ASR,
- record and transcribe controls,
- safe troubleshooting copy.

Output tab should keep:

- Voice Output enable / disable,
- Test Voice,
- rate and volume,
- stop voice,
- system voice availability.
- Direct Conversation note: if Voice Output is enabled, Rei speaks the assistant reply after completion; otherwise the reply remains text-only.

Voice Profile remains future-only until TTS strategy is defined.

### Home / Chat

The chat input area should show compact Voice state:

- idle / listening / transcribing / ready / thinking / speaking / error,
- a mic control,
- a stop control when listening or speaking,
- transcript ready state when confirmation is needed,
- clear and send affordances without hiding normal text input.

Voice state must not clear the user's unsent draft without a clear user action.

### Overlay Future

Overlay may later show only low-risk Voice state:

- listening,
- transcribing,
- ready to confirm,
- speaking,
- interrupted,
- error.

Overlay must not show full transcript, raw assistant reply, Debug state, prompt, memory content, API keys, `.env`, local paths, stdout, or stderr. macOS auto-show remains out of scope for this spec.

## Error Handling

All errors should be short, Chinese-first, and safe.

| Failure | User-Facing Summary | State | Safety Rule |
| --- | --- | --- | --- |
| Local ASR not configured | `本地语音识别未配置` | `error` or disabled control | Do not record for transcription. |
| ASR binary missing | `缺少本地识别程序` | `error` | Show safe basename only. |
| ASR model missing | `缺少本地语音模型` | `error` | Show safe basename only. |
| Converter missing for WebM/Ogg | `尚未配置音频转换工具` | `error` | Do not call ASR binary. |
| ASR timeout | `本地语音识别超时，可以尝试更小模型或更短录音` | `error` | Clean temp audio. |
| No transcript | `没有识别到可用文本` | `idle` | Do not send. |
| Mic denied | `麦克风权限被拒绝` | `error` | Do not retry automatically. |
| TTS unavailable | `语音播放不可用` | `error` or text-only fallback | Keep text reply. |
| Provider timeout | `回复超时，请稍后再试` | `error` | Do not replay or auto-send again. |

Event Stream and Debug may show safe status codes, duration buckets, char counts, MIME summary, and safe basenames. They must not show full transcript, audio data, raw subprocess output, raw provider response, raw prompt, secrets, or full paths.

## Privacy And Safety

Voice v2 keeps these fixed boundaries:

- Audio is not uploaded to external services.
- ASR remains local unless a future task explicitly changes scope.
- Audio is not persisted after transcription.
- Temp files are cleaned after success, failure, or timeout.
- Unconfirmed transcript stays outside memory, prompt, retrieval, game context, Semantic Extraction, and proactive behavior.
- Voice never bypasses memory confirmation.
- Voice does not create a separate proactive trigger path.
- Voice Output does not speak diagnostics or hidden context.
- Debug / Prompt Preview / Event Stream remain safe summaries.

## Implementation Handoff

Foundation and v2.1 Direct Conversation completed in the renderer:

1. Typed Voice v2 state model.
2. Renderer coordination across Web Speech, Local ASR, send confirmation, Voice Output, and interruption.
3. Voice workspace Conversation state UI while keeping confirm-send default and exposing Direct Conversation opt-in.
4. Home / Chat compact state display.
5. Direct Conversation auto-send through the normal chat flow.
6. TTS interruption wiring and mutual exclusion between speaking and listening.

Suggested later task order:

1. Extract more controller logic if the state graph grows beyond the current renderer wiring.
2. Consider hands-free only after a separate privacy, timeout, and game-mode risk design.
3. Consider short spoken reply mode after TTS strategy is clearer.
4. Consider Overlay voice state display only after Overlay safe mode remains stable.
5. Define Voice Profile only after a character-grade TTS strategy exists.

Required verification for implementation tasks should include desktop automated checks, backend tests when backend behavior changes, visual smoke for UI changes, and packaged `.app` smoke for packaged or user-visible runtime behavior.

## QA Coverage

Machine-readable scenarios live in `docs/qa/voice_interaction_v2_scenarios.json`.

Manual acceptance for this spec:

1. Confirm-send is the default.
2. Direct Conversation is visible opt-in and never implied by enabling ASR or Voice Output.
3. Direct Conversation still requires a user gesture for each recording round; hands-free / auto-listen remains future-only and not default.
4. The state machine covers `idle`, `listening`, `transcribing`, `ready_to_send`, `assistant_thinking`, `speaking`, `interrupted`, and `error`.
5. Listening and speaking are mutually exclusive.
6. Starting recording interrupts active TTS.
7. Unconfirmed transcript has no memory, prompt, retrieval, game context, Semantic Extraction, or proactive side effect.
8. Direct Conversation auto-send events do not show the full transcript in Event Stream, Debug, Raw JSON, Prompt Preview, or Overlay.
9. Voice Output auto-speaks Direct Conversation replies only when enabled, and Stop Voice interrupts playback.
10. TTS does not speak Debug, Prompt Preview, trace, memory internals, raw prompt, full transcript, paths, `.env`, or secrets.
11. Game-mode speech remains short and low-interruption.
12. Voice workspace, Home / Chat, and future Overlay state placement are defined.
