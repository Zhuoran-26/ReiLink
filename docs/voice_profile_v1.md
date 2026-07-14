# Voice Profile v1

Updated: 2026-07-12

Document status: current component specification for Voice v2.2.

Status: implemented as a behavior policy and wired through TTS Strategy v0 plus TTS Provider Registry / Capability Surface v0. Voice Profile v1 decides whether an assistant reply may be spoken and whether it is spoken as full, brief, or silent. TTS Provider Registry v0 currently exposes only the system-provided `system_speech_synthesis` strategy around renderer-side `speechSynthesis`; it reserves disabled metadata for future local / external providers but does not add a real external provider, local model provider, character voice, voice clone, wake-word mode, or hands-free loop.

## Current Profile

`rei_calm`

- Label: `Rei Calm / Rei 冷静陪伴`.
- Normal chat default: `full`.
- Direct Conversation default: `brief`.
- Proactive and memory prompt speaking: off by default.
- Max brief length: 2 sentences / 120 characters by default.
- Debug speaking: disabled.
- Starting a new recording interrupts active TTS.
- Stop Voice interrupts active TTS and shows a short stopped / interrupted state.
- Test Voice remains available and uses the `system_speech_synthesis` provider backed by system `speechSynthesis`.
- Test Voice is an explicit user action. It does not represent automatic assistant-reply policy and does not write a chat message.
- TTS unavailable never removes the full text reply.

## TTS Provider Registry v0

- Current provider id: `system_speech_synthesis`.
- Current provider role: system-provided fallback around browser / Electron `speechSynthesis`.
- The underlying strategy owns speak / stop / availability fallback; Voice Output owns lifecycle status and safe Event Stream summaries.
- The Voice workspace displays the current provider as `System Speech Synthesis`.
- Provider status is `available` when `speechSynthesis` and `SpeechSynthesisUtterance` exist, otherwise `unavailable`.
- Current capabilities: system-provided speech, no provider streaming, no character voice, no ReiLink-configured network provider, no TTS API key, supports stop / interrupt.
- Reserved provider ids: `local_tts` and `external_tts`.
- `local_tts` is disabled, not selectable, and `not_implemented`.
- `external_tts` is disabled, not selectable, and `not_configured`.
- Future local TTS, external TTS, and character voice providers are not implemented.
- ReiLink passes selected text to the platform `speechSynthesis` implementation. This layer does not call an external TTS endpoint, configure a TTS API key, upload an audio file, or read a local TTS model path; it makes no broader claim about undocumented platform internals.
- Unknown or disabled provider ids safely fall back to `system_speech_synthesis`; if system speech is unavailable, Voice Output emits a safe unavailable event and keeps the reply as text.

## Spoken Modes

`full`

- Speak the sanitized assistant reply after the reply completes.
- Strip code blocks, inline code, tables, and markdown structure before speaking.
- The full chat text remains visible.

`brief`

- Speak the first one or two natural Chinese sentences by default.
- Cap spoken text by configured character length.
- Keep the full assistant reply visible in chat.
- Use rule-based excerpting only; do not call an extra LLM and do not hardcode Rei replies.

`silent`

- Skip speech.
- Keep the assistant reply visible in chat.
- Emit only safe skip metadata.
- This controls automatic assistant-reply speech; an explicit Test Voice action remains separate.

## Never Spoken

Voice Profile v1 must skip:

- Debug output.
- Prompt Preview.
- Event Stream.
- Semantic Shadow trace.
- Knowledge trace.
- Persona summary or persona markdown.
- Memory internals, memory prompts, pending memory evidence, and confirmed memory raw detail.
- Raw prompt or raw provider response.
- API keys, Authorization headers, `.env`, stdout, stderr, and full local paths.
- JSON payloads, trace-like structured content, code blocks, and setup/backend/provider long error text.

If sanitized spoken text is empty, speech is skipped.

## Event Privacy

Voice Profile events may include:

- profile id,
- source,
- spoken mode,
- TTS strategy id,
- TTS provider id,
- TTS provider status,
- TTS provider fallback flag,
- max character / sentence limits,
- original and spoken character counts,
- sentence count,
- skip reason.

Voice Profile events must not include full assistant text, spoken text, prompt text, ASR transcript, secrets, raw logs, or full local paths.

TTS lifecycle events may include strategy id, provider id, provider status, provider fallback flag, source, profile, character count, stop reason, safe stop status such as `interrupted` / `stopped`, unavailable / error reason, and a short status string. They must not include the full assistant reply, Test Voice text, spoken text, prompt text, ASR transcript, persona markdown, `.env`, API keys, raw provider responses, raw config, local model paths, stdout, stderr, or full local paths.

## UI Surface

The Voice workspace `Voice Profile` tab shows:

- current profile,
- normal and Direct Conversation spoken modes,
- max spoken length,
- proactive and memory speaking toggles,
- never-spoken categories,
- current `System Speech Synthesis` provider and `speechSynthesis` caveat,
- explicit note that this is not a character voice.
- Stop Voice / interrupted feedback that confirms playback was stopped without exposing spoken text.

The full reply remains in chat regardless of spoken mode.
