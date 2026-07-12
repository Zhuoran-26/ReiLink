# ReiLink

> A local-first AI game companion desktop runtime.

[简体中文](README.md) | English

[![Status](https://img.shields.io/badge/status-pre--release-6b5cff)](docs/PROJECT_STATUS.md)
[![Platform](https://img.shields.io/badge/platform-macOS-111827)](#quick-start)
[![Desktop](https://img.shields.io/badge/desktop-Electron-47848f)](https://www.electronjs.org/)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Language](https://img.shields.io/badge/language-TypeScript%20%2F%20Python-3178c6)](#architecture)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

ReiLink is a Chinese-first AI companion runtime for single-player game players. It brings game context, player dialogue, confirmed memory, local knowledge packs, voice input/output, and safe runtime events into one desktop app.

ReiLink is not a generic chatbot and not a guide-site clone. Final replies remain persona + LLM generated; game context, memory, and knowledge retrieval only provide supporting context. The current companion persona is an original Rei-like minimal style and does not use Evangelion, Rei Ayanami, NERV, or any official IP elements.

## Table Of Contents

- [What Is ReiLink?](#what-is-reilink)
- [Current Status](#current-status)
- [Highlights](#highlights)
- [Feature Matrix](#feature-matrix)
- [Architecture](#architecture)
- [Agent Turn Flow](#agent-turn-flow)
- [Voice Interaction v2.2](#voice-interaction-v22)
- [Knowledge Retrieval](#knowledge-retrieval)
- [Local-first And Privacy](#local-first-and-privacy)
- [Quick Start](#quick-start)
- [Local ASR Setup](#local-asr-setup)
- [Packaging](#packaging)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Known Limitations](#known-limitations)
- [License](#license)

## What Is ReiLink?

Most game companions drift toward either generic chat or static guide lookup. ReiLink explores a quieter middle ground:

- the player controls input, sending, and memory writes;
- the companion stays restrained, low-emotion, and low-interruption;
- local knowledge provides factual context only when relevant;
- long-term memory is written only after user confirmation;
- voice input defaults to editable confirm-send, while explicitly enabled Direct Conversation auto-sends only a user-triggered recording that passes guards;
- user data, settings, knowledge packs, and audio handling stay local-first.

The project is currently built for local demos, portfolio presentation, code review, and product/runtime iteration. It is not a commercial installer.

## Current Status

- Current development milestone: **Voice v2.2 release hardening**.
- The `dev/codex-reilink` branch contains the latest Voice, Local ASR, Knowledge Retrieval, and Context & Memory work.
- The current development line includes Voice v2.2 (confirm-send, Direct Conversation, Voice Profile, TTS Strategy / Provider Registry), Local ASR, Knowledge Retrieval, Candidate Memory, Memory Retrieval, Session Archive Runtime, Archive Search, and Archive-to-Memory Candidate Bridge.
- Public release tags may lag behind the dev branch. GitHub updates, release tags, push, and merge still require manual review.
- The macOS packaged app has been smoke-tested repeatedly, but ReiLink remains pre-release.

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for detailed project state.

## Highlights

- Chinese-first AI companion chat with an original minimal persona.
- [DeepSeek](https://api-docs.deepseek.com/) compatible provider and `fast` / `pro` / `auto` model routing.
- Confirmable Memory: long-term memory is written only after user acceptance.
- Context & Memory System: Candidate Memory, accepted-memory retrieval, Persona-Memory Eval, Session Archive safe summaries, Archive Search, and explicit Archive-to-Memory Candidate Bridge.
- Game Context: current game, boss, progression, frustration state, and manual current-game override.
- Local sample knowledge packs for [Elden Ring](data/knowledge/games/elden_ring) and [Hollow Knight](data/knowledge/games/hollow_knight).
- Knowledge Retrieval v1: local keyword retrieval, top-k snippets, grounding/gating, explicit game-name switching, and casual-chat isolation.
- Voice v2.2: confirm-send by default, explicit Direct Conversation, a nine-state model, full / brief / silent Voice Profile policy, interruptible system TTS, and safe Event Stream lifecycle summaries.
- Voice Input: Local ASR through user-configured [whisper.cpp](https://github.com/ggerganov/whisper.cpp) compatible binary, model, and [ffmpeg](https://ffmpeg.org/) compatible converter; no cloud ASR path.
- Event Stream / Debug Panel: safe summaries without raw prompts, API keys, full paths, or full transcripts.
- macOS packaged app runtime foundation: bundled backend binary, bundled knowledge resources, and user data outside the `.app`.

## Feature Matrix

| Area | Capability | Status | Notes |
| --- | --- | --- | --- |
| Persona | Original Rei-like minimal companion | MVP | Original persona, no official IP elements. |
| Dialogue | LLM-first reply generation | Done | Game context / memory / knowledge provide context only. |
| Memory | Candidate / Retrieval / Archive | Done | Only accepted / active long-term memory can enter prompt; archive does not enter prompt directly. |
| Game Context | Boss / deaths / frustration / session | MVP | Rule-first with limited LLM semantic fallback. |
| Knowledge Retrieval | Local keyword retrieval | MVP | No embeddings, vector DB, or hybrid retrieval yet. |
| Session Archive | Recent session safe summaries | MVP | Manual archive, search, delete, clear, and explicit candidate scan; no raw prompt or transcript storage. |
| Voice Interaction | confirm-send + Direct Conversation | v2.2 | Direct Conversation is explicit and user-triggered each round; it is not hands-free. |
| Voice Output | System Speech Synthesis + Voice Profile | v2.2 | full / brief / silent; system speech is the only selectable provider and is not character-grade voice acting. |
| Voice Input | Local ASR | MVP | User-managed binary, model, and converter required; audio is transferred only to the local backend. |
| Event Stream | Safe lifecycle events | Done | No raw prompt, API key, full path, or full transcript. |
| Packaging | macOS `.app` | MVP | User data stays outside the `.app`; unsigned local build. |
| Overlay | macOS safe mode | MVP / frozen | Foundation exists; auto-show intentionally fails closed. |
| Live2D | Avatar layer | Planned | Not implemented. |
| Embedding / Hybrid RAG | Vector / hybrid retrieval | Planned | Current retrieval is keyword-based. |

## Architecture

ReiLink uses an [Electron](https://www.electronjs.org/) desktop shell, a [React](https://react.dev/) / [TypeScript](https://www.typescriptlang.org/) / [Vite](https://vite.dev/) renderer, and a local [FastAPI](https://fastapi.tiangolo.com/) backend. Packaged builds use [PyInstaller](https://pyinstaller.org/) for the backend binary. Diagrams use [Mermaid](https://mermaid.js.org/) and render directly on GitHub.

```mermaid
flowchart LR
  Player["Player"] --> UI["React Renderer<br/>Chat / Settings / Debug"]
  UI --> Events["Event Bus<br/>Safe event summaries"]
  UI --> VoiceOut["Voice Output<br/>System TTS"]
  UI --> Audio["Voice Input<br/>MediaRecorder"]

  subgraph Desktop["Electron Desktop"]
    UI
    Events
    VoiceOut
    Audio
  end

  UI --> API["FastAPI Backend"]
  Audio --> API

  subgraph Runtime["Backend Runtime"]
    API --> Agent["Dialogue Agent"]
    Agent --> Persona["Persona"]
    Agent --> Memory["Confirmed Memory"]
    Agent --> Game["Game Context"]
    Agent --> Retrieval["Knowledge Retrieval"]
    Agent --> Router["Model Router"]
    API --> ASR["Local ASR Bridge"]
    ASRSettings["Local ASR Settings"] --> ASR
    ASR --> TempAudio["Temporary Audio Files<br/>default cleanup"]
    ASR --> Converter["Audio Converter<br/>ffmpeg-compatible"]
    ASR --> Whisper["Local ASR Binary<br/>whisper.cpp-compatible"]
  end

  Retrieval --> Packs["Bundled Knowledge Packs"]
  Memory --> UserData["Local User Data"]
  UserData --> ASRSettings
  Router --> DeepSeek["DeepSeek-compatible API"]

  Packs -. "read-only resource" .-> Runtime
  UserData -. "local persistence" .-> Runtime
```

The renderer owns interaction, audio capture, Voice state, system TTS, and safe event display. The backend owns the Agent runtime, knowledge retrieval, memory, game context, model routing, Local ASR subprocess boundaries, and user data directories. Local ASR settings are stored in Local User Data, and temporary audio files are cleaned by default after processing. Confirm-send fills the input box; explicit Direct Conversation enters the same chat path only after a user-triggered recording passes guards. Unconfirmed or guarded transcripts do not enter memory, prompt, knowledge retrieval, game context, or proactive behavior.

## Agent Turn Flow

ReiLink does not send user text straight into a generic chatbot. Each turn prepares game context, memory candidates, local knowledge, prompt assembly, model routing, and safe output surfaces.

```mermaid
flowchart TD
  U["User message"] --> GC["Game context extraction"]
  U --> MC["Memory candidate detection"]
  U --> KR["Local knowledge retrieval"]

  GC --> CTX["Current turn context"]
  MC --> PM["Pending memory<br/>written only after accept"]
  KR --> KG["Top-k local snippets"]

  Persona["Persona"] --> Prompt["Prompt assembly"]
  LongMemory["Confirmed Memory<br/>long-term memory"] --> Prompt
  CTX --> Prompt["Prompt assembly"]
  KG --> Prompt
  Prompt --> Router["Model routing<br/>fast / pro / auto"]
  Router --> LLM["DeepSeek-compatible Provider"]
  LLM --> Reply["Rei reply"]

  Reply --> UI2["Chat UI"]
  Reply --> TTS["Optional voice output"]
  Reply --> ES["Event Stream<br/>safe summary"]

  PM -. "after user confirmation" .-> LongMemory
```

Prompt assembly includes persona, confirmed memory, current turn context, and relevant knowledge snippets. Memory is not written automatically. Knowledge is injected only when relevant. Casual chat does not force retrieval. Event Stream shows safe summaries only.

## Voice Interaction v2.2

Voice v2.2 is a user-triggered voice conversation foundation, not a real-time voice agent. `confirm_send` remains the default. Direct Conversation must be enabled explicitly, and every round still starts with an explicit recording action; there is no always-listening loop or wake word.

### Voice Input / Local ASR

- Local ASR is the stable path; Web Speech remains an environment-dependent fallback.
- Users configure the ASR binary, model, and converter in Settings. ReiLink does not bundle those third-party assets.
- The renderer transfers short recordings to the local backend, which runs local ASR and cleans temporary files. No cloud ASR path is integrated.
- `confirm_send`: the transcript enters the editable composer and waits for user confirmation.
- `direct_conversation`: after a user-triggered recording, empty text, short text, short recordings, and likely partial phrases are guarded; only passing text enters the existing chat flow automatically.
- Unconfirmed or guarded transcripts do not write memory, trigger proactive behavior, or enter prompt, retrieval, game context, or Semantic Extraction.

### State / Direct Conversation

The current states are `idle`, `listening`, `transcribing`, `auto_sending`, `ready_to_send`, `assistant_thinking`, `speaking`, `interrupted`, and `error`. Recording and playback are mutually exclusive; starting another recording or pressing Stop Voice attempts to interrupt speech.

### Voice Output / Profile

- The only enabled and selectable provider is `system_speech_synthesis`, backed by the platform `speechSynthesis` implementation.
- Local TTS is a disabled `not_implemented` placeholder. External TTS is a disabled `not_configured` placeholder.
- Voice Profile `rei_calm` defaults normal chat to `full` and Direct Conversation to deterministic `brief`; `silent` is also supported without removing the text reply.
- Test Voice is a separate explicit action, not automatic assistant-reply policy.
- ReiLink does not integrate an external TTS API or TTS API key. Platform `speechSynthesis` internals are owned by the OS / runtime.

```mermaid
sequenceDiagram
  participant User as User
  participant UI as Renderer
  participant Backend as Local Backend
  participant ASR as Local ASR
  participant Chat as Existing Chat Flow

  User->>UI: Explicitly start and stop recording
  UI->>Backend: Transfer short audio locally
  Backend->>ASR: Transcribe locally
  ASR-->>UI: transcript
  alt confirm_send
    UI->>UI: Fill composer and wait
    User->>Chat: Confirm send
  else direct_conversation and guard passes
    UI->>Chat: Auto-send
  else guard blocks
    UI->>UI: Wait for confirmation or retry
  end
  Chat-->>UI: Text reply
  opt Voice Output enabled and profile is not silent
    UI->>UI: Play system speech with Stop control
  end
```

Voice / TTS Event Stream payloads retain only safe metadata such as type, source, provider / status / profile, guard reason, and lengths. They do not retain full transcripts, assistant replies, or spoken text. See [`docs/voice_interaction_v2_spec.md`](docs/voice_interaction_v2_spec.md) for the current specification and [`docs/release_voice_v2_2_hardening_checklist.md`](docs/release_voice_v2_2_hardening_checklist.md) for release gates.

## Knowledge Retrieval

Current retrieval is local keyword retrieval, not embedding or vector search.

- Supported sample packs: Elden Ring and Hollow Knight.
- Retrieval statuses include `used`, `not_found`, `below_threshold`, `no_pack`, and `not_game_related`.
- Grounding/gating keeps low-relevance snippets out of prompts.
- Casual chat does not force knowledge injection.
- Explicit game names from user messages take priority over current game context.

Knowledge packs live under [`data/knowledge/games`](data/knowledge/games). Authoring guidance is in [`docs/KNOWLEDGE_PACK_AUTHORING.md`](docs/KNOWLEDGE_PACK_AUTHORING.md).

## Local-first And Privacy

Local-first means local user data, memory, settings, knowledge packs, audio handling, and Local ASR are kept on the device. LLM inference can still use a configured provider such as DeepSeek.

- Local memory, session, settings, and logs are written to the user data directory, not packaged app resources.
- Packaged app user data directory: `~/Library/Application Support/ReiLink/data`.
- Local ASR settings example path: `~/Library/Application Support/ReiLink/data/local_asr_settings.json`.
- API keys and local environment files are not bundled into the `.app`.
- Pending memory requires user confirmation.
- Session Archive stores safe summaries only; Archive Search does not enter prompt, and Archive-to-Memory Bridge only creates pending candidates.
- Local ASR audio is short-lived temporary data and is cleaned after processing.
- Voice / TTS Event Stream does not retain full transcripts, assistant replies, or spoken text. Debug / Raw JSON also avoids raw prompts, raw subprocess output, API keys, Authorization data, full local paths, audio content, and base64 audio.

## Quick Start

### 1. Requirements

- macOS for the current packaged app path.
- Python backend environment.
- Node.js / npm desktop environment.
- Optional real LLM provider credentials.
- Optional Local ASR tools: whisper.cpp-compatible binary, compatible model file, and converter.

### 2. Backend / Desktop Dev

```bash
make install-backend
make install-desktop
make doctor
make dev-backend
make dev-desktop
```

`make dev` does not manage long-running processes. Start backend and desktop separately.

### 3. Provider Setup

Configure the LLM provider in the local backend environment. Do not commit real keys or local environment files. `LLM_PROVIDER=mock` can be used for no-key local demos.

Health checks:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/setup/status
```

### 4. Optional Local ASR Setup

Real Local ASR requires user-managed local tools outside the repo and outside the packaged app:

- whisper.cpp-compatible CLI binary
- compatible local model file
- ffmpeg-like converter for browser WebM / Ogg recordings

Then configure the paths from Settings -> Voice Input -> `本地 ASR 配置 / Local ASR Setup`. See [`docs/local-asr-manual-setup.md`](docs/local-asr-manual-setup.md).

### 5. Packaging

```bash
make package-backend
make package-desktop
```

The local unsigned macOS app is generated at `apps/desktop/release/ReiLink-darwin-<arch>/ReiLink.app`.

## Local ASR Setup

Configuration priority:

1. Settings user configuration.
2. Local ASR environment fallback.
3. Unconfigured safe fallback.

The Settings API returns configured booleans, source, and basenames only. Full paths are stored only in local configuration or shown in user-edited inputs. ReiLink does not bundle, auto-fetch, or ship whisper binaries, models, ffmpeg, or third-party executables.

## Packaging

Packaged app backend priority:

1. Healthy external backend on `127.0.0.1:8000`.
2. User-configured backend binary.
3. Bundled backend binary inside the `.app`.
4. Repo-local fallback in development.

Packaged resources are read-only. Memory, session, settings, logs, and Local ASR settings live outside the `.app`. The current macOS app is an unsigned local build without installer, notarization, auto updater, or Windows / Linux packaging.

## Documentation

| Document | Purpose |
| --- | --- |
| [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) | Current project state and scope. |
| [`docs/QA.md`](docs/QA.md) | Manual QA and release regression checklist. |
| [`docs/release_voice_v2_2_hardening_checklist.md`](docs/release_voice_v2_2_hardening_checklist.md) | Current Voice v2.2 automated, manual, and packaged release gates. |
| [`docs/releases/reilink-voice-v2.2.md`](docs/releases/reilink-voice-v2.2.md) | Voice v2.2 release notes draft. |
| [`docs/voice_interaction_v2_spec.md`](docs/voice_interaction_v2_spec.md) | Current Voice v2.2 state and Direct Conversation specification. |
| [`docs/voice_profile_v1.md`](docs/voice_profile_v1.md) | Current full / brief / silent output policy. |
| [`docs/tts_provider_registry.md`](docs/tts_provider_registry.md) | Current TTS provider capability and placeholder boundaries. |
| [`docs/qa/voice_v2_2_release_matrix.json`](docs/qa/voice_v2_2_release_matrix.json) | Machine-readable mapping from Voice v2.2 release gates to component QA and automated tests. |
| [`docs/release_context_memory_hardening_checklist.md`](docs/release_context_memory_hardening_checklist.md) | Context & Memory release hardening checklist. |
| [`docs/releases/reilink-v0.2-pre.4-context-memory.md`](docs/releases/reilink-v0.2-pre.4-context-memory.md) | Context & Memory v0.2-pre.4 release notes draft. |
| [`docs/memory_architecture_v0.md`](docs/memory_architecture_v0.md) | Memory layers, Candidate Memory, Retrieval, and archive bridge boundaries. |
| [`docs/session_archive_v1_architecture.md`](docs/session_archive_v1_architecture.md) | Session Archive / Search / Archive-to-Memory Bridge architecture. |
| [`docs/local-asr-manual-setup.md`](docs/local-asr-manual-setup.md) | Real Local ASR setup and smoke flow. |
| [`docs/voice-input-local-asr-spike.md`](docs/voice-input-local-asr-spike.md) | Historical Local ASR spike; use the Voice v2.2 spec for current status. |
| [`docs/release-notes/reilink-voice-mvp.md`](docs/release-notes/reilink-voice-mvp.md) | Historical Voice MVP release note, superseded by the v2.2 draft. |
| [`docs/qa/retrieval_scenarios.json`](docs/qa/retrieval_scenarios.json) | Machine-readable Knowledge Retrieval regression scenarios. |
| [`docs/qa/voice_input_scenarios.json`](docs/qa/voice_input_scenarios.json) | Machine-readable Voice Input fallback scenarios. |
| [`docs/qa/voice_input_local_asr_scenarios.json`](docs/qa/voice_input_local_asr_scenarios.json) | Machine-readable Local ASR release regression scenarios. |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Common startup and runtime troubleshooting. |

## Roadmap

### v0.2 Runtime Foundation

The current development line has largely completed this MVP foundation.

- Voice Output MVP.
- Local ASR Voice Input MVP.
- Knowledge Retrieval v1.
- Candidate Memory v1 / Memory Retrieval v1.
- Session Archive Runtime / Search / Archive-to-Memory Candidate Bridge.
- Event Stream / Debug privacy guardrails.
- Packaged app runtime foundation.

### v0.2.x Stabilization

- Context & Memory release hardening.
- Voice v2.2 release hardening and QA consolidation.
- Packaged app smoke coverage for user-visible runtime changes.
- Local ASR setup helper and accuracy / timeout tuning.
- More robust QA regression flows.

### v0.3 Gameplay Presence

- Overlay v1.
- Better gameplay session awareness.
- Low-interruption proactive companion display.

### v0.4 Character Presence

- Live2D avatar layer.
- Character state machine.
- More natural local character TTS exploration.

### Later

- Embedding / hybrid retrieval.
- More games and richer knowledge packs.
- Installer / updater.

## Known Limitations

- Pre-release / portfolio-oriented project.
- macOS-first.
- No installer, code signing, notarization, or auto updater.
- No cloud account or sync.
- No bundled whisper binary, model, ffmpeg, or third-party executable.
- System TTS may sound unnatural and is not character-grade voice acting.
- Local ASR accuracy depends on model size, microphone quality, noise, and hardware.
- Voice v2.2 is not a hands-free or always-listening agent; there is no wake word, speaker diarization, or automatic next recording round.
- No local neural TTS, external / streaming TTS provider, custom character voice, voice cloning, or cloud audio upload.
- Overlay auto-show remains in macOS fail-closed safe mode.
- No Live2D yet.
- No embedding, vector DB, hybrid retrieval, semantic archive search, prompt archive retrieval, or external memory provider yet.
- Knowledge packs are samples, not complete guide libraries.
- Current packaged app is a local unsigned development build.

## License

MIT License. See [LICENSE](LICENSE).
