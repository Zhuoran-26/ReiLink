# Voice Profile v1

Updated: 2026-06-17

Status: implemented as a behavior policy. Voice Profile v1 decides whether an assistant reply may be spoken and whether it is spoken as full, brief, or silent. It does not add a new TTS engine, character voice, voice clone, wake-word mode, or hands-free loop.

## Current Profile

`rei_calm`

- Label: `Rei Calm / Rei 冷静陪伴`.
- Normal chat default: `full`.
- Direct Conversation default: `brief`.
- Proactive and memory prompt speaking: off by default.
- Max brief length: 2 sentences / 120 characters by default.
- Debug speaking: disabled.
- Starting a new recording interrupts active TTS.
- Test Voice remains available and uses the system `speechSynthesis` voice.

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
- max character / sentence limits,
- original and spoken character counts,
- sentence count,
- skip reason.

Voice Profile events must not include full assistant text, spoken text, prompt text, ASR transcript, secrets, raw logs, or full local paths.

## UI Surface

The Voice workspace `Voice Profile` tab shows:

- current profile,
- normal and Direct Conversation spoken modes,
- max spoken length,
- proactive and memory speaking toggles,
- never-spoken categories,
- `speechSynthesis` caveat,
- explicit note that this is not a character voice.

The full reply remains in chat regardless of spoken mode.
