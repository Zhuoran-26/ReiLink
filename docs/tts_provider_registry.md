# TTS Provider Registry v0

Updated: 2026-07-12

Document status: current component specification for Voice v2.2.

Status: implemented as renderer-side provider metadata and capability surface. The only enabled and selectable provider is `system_speech_synthesis`, backed by Electron / browser `speechSynthesis`. `local_tts` and `external_tts` are reserved descriptors only; they are disabled, not selectable, and do not call any local model path, API key, network service, or external runtime.

## Goals

- Keep TTS provider metadata in one renderer registry.
- Show current provider status and capabilities in Voice Output surfaces.
- Reserve future provider ids without making them selectable.
- Keep Direct Conversation and Voice Profile behavior unchanged.
- Emit only safe Event Stream provider summaries.

## Provider Descriptors

Current provider ids:

- `system_speech_synthesis`
- `local_tts`
- `external_tts`

Provider status values:

- `available`
- `unavailable`
- `not_configured`
- `not_implemented`

Each provider descriptor includes:

- id,
- label,
- status,
- enabled,
- selectable,
- description,
- privacy summary,
- fallback summary,
- capability flags.

Capability flags:

- `streaming`
- `customVoice`
- `localOnly`
- `requiresNetwork`
- `requiresApiKey`
- `supportsInterrupt`

## Current Registry

`system_speech_synthesis`

- Enabled: yes.
- Selectable: yes.
- Status: `available` when renderer `speechSynthesis` and `SpeechSynthesisUtterance` exist; otherwise `unavailable`.
- Capabilities: system-provided speech, no provider streaming, no character voice, no ReiLink-configured network provider, no TTS API key, and Stop / interrupt support.
- Privacy: ReiLink passes the selected text to the platform `speechSynthesis` implementation. ReiLink itself does not call an external TTS endpoint, configure a TTS API key, or upload an audio file. This is an application integration boundary, not a claim about undocumented platform internals.

`local_tts`

- Enabled: no.
- Selectable: no.
- Status: `not_implemented`.
- Purpose: future local TTS placeholder.
- Privacy: the current runtime does not read local model paths or call a local TTS runtime.

`external_tts`

- Enabled: no.
- Selectable: no.
- Status: `not_configured`.
- Purpose: future external TTS placeholder.
- Privacy: the current runtime does not save API keys and does not upload text or audio to an external TTS service.

## Resolution Rules

- The registry resolves legal enabled providers directly.
- Unknown provider ids safely fall back to `system_speech_synthesis`.
- Disabled or non-selectable provider ids safely fall back to `system_speech_synthesis`.
- If the system provider is unavailable, Voice Output emits a safe unavailable event and keeps the assistant reply as text.
- No unimplemented provider is called.

## UI Surface

Voice Output surfaces show:

- current TTS provider,
- provider status,
- privacy boundary,
- capability summary,
- fallback summary,
- disabled future provider placeholders.

The UI does not expose a working provider selector in v0.

## Event Privacy

TTS lifecycle events may include:

- provider id,
- provider status,
- provider fallback flag,
- strategy id,
- source,
- Voice Profile mode,
- character count,
- stop / unavailable / error reason,
- short status string.

They must not include:

- full assistant reply,
- spoken text,
- Test Voice text,
- raw prompt,
- persona markdown,
- ASR transcript,
- raw provider response,
- API keys,
- `.env`,
- local model paths,
- full local paths,
- raw config,
- stdout or stderr.

## Non-Goals

- No real local TTS integration.
- No real external TTS integration.
- No TTS API key setup.
- No ReiLink-managed text or audio upload to a TTS provider.
- No character voice or voice clone.
- No provider streaming.
- No change to Direct Conversation reply selection.
