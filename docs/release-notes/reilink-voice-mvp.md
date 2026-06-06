# ReiLink Voice Interaction MVP

Draft release notes for the Voice Interaction MVP stage on `dev/codex-reilink`.

## Highlights

- Voice Output v1: optional local system TTS through renderer-side `speechSynthesis`.
- Voice Output controls: Settings toggle, `测试语音 / Test Voice`, rate, volume, Stop Voice, and safe lifecycle events.
- Voice Input v2 path: Local ASR with user-configured whisper.cpp-compatible binary, model, and audio converter.
- Main chat voice button now prefers Local ASR when ready, with Web Speech kept as fallback.
- Transcript-first UX: recognized text fills the chat input and waits for user confirmation before sending.
- Local ASR settings persistence: binary, model, and converter paths can be saved from Settings and live in the user data directory.
- Audio conversion bridge: browser-recorded WebM/Ogg can be converted to 16 kHz mono WAV through a user-configured converter.
- ASR transcript cleanup: `zh-CN` / `zh_Hans` normalize to whisper `zh`, and ASR output is lightly normalized to Simplified Chinese before filling the input.
- Debug / Event Stream privacy guardrails: no full transcript, full local path, raw subprocess output, API key, `.env`, Authorization, audio content, or base64 audio.
- Knowledge Retrieval v1.x improvements: local keyword retrieval, grounding / gating, explicit game-name switching, and casual-chat isolation.
- QA / regression scenarios: Voice Output, Web Speech fallback, Local ASR packaged smoke, privacy, and release regression checks are documented and machine-readable.

## Upgrade / Setup Notes

- Existing users can continue without Local ASR configured; ReiLink falls back safely.
- Local ASR users should configure paths in Settings -> Voice Input -> `本地 ASR 配置 / Local ASR Setup`.
- Saved Local ASR settings are stored under the backend user data directory, for example `~/Library/Application Support/ReiLink/data/local_asr_settings.json`.
- Do not commit model files, whisper binaries, converter binaries, `.env`, or local path configuration.
- ReiLink does not download or bundle whisper/model/ffmpeg assets.
- Packaged `.app` users should prefer Settings persistence because shell environment propagation can differ from dev startup.

## Known Limitations

- System TTS is not character-grade voice acting.
- Names such as "Rei" and some tone/phrasing may sound unnatural with system voices.
- ASR accuracy depends on model size, microphone quality, background noise, and local hardware performance.
- `ggml-base.bin` is a speed / accuracy compromise; larger models may be more accurate but slower or more likely to time out.
- ReiLink does not bundle whisper binary, model files, ffmpeg, or other third-party binaries.
- Native file picker is not implemented yet; Local ASR setup currently uses text path inputs.
- No wake word or continuous listening.
- No cloud ASR or commercial ASR.
- No audio retention by default.
- No embedding, vector database, or hybrid retrieval yet.

## QA References

- Manual QA pack: [`docs/QA.md`](../QA.md)
- Local ASR setup guide: [`docs/local-asr-manual-setup.md`](../local-asr-manual-setup.md)
- Local ASR design background: [`docs/voice-input-local-asr-spike.md`](../voice-input-local-asr-spike.md)
- Project status: [`docs/PROJECT_STATUS.md`](../PROJECT_STATUS.md)
- Machine-readable Local ASR scenarios: [`docs/qa/voice_input_local_asr_scenarios.json`](../qa/voice_input_local_asr_scenarios.json)
