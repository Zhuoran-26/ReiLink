# Local ASR Manual Setup / 本地 ASR 手动配置

This guide is for optional, manual verification of ReiLink Local ASR with a user-provided whisper.cpp-compatible binary, model file, and optional audio converter. It does not mean ReiLink bundles, downloads, or redistributes any ASR model, whisper binary, ffmpeg binary, or third-party converter.

本文档用于手动配置和验证 ReiLink 本地语音识别链路。它不代表 ReiLink 内置、下载或再分发 whisper binary、模型文件、ffmpeg binary 或任何第三方转换工具。

## 1. Scope / 范围

- Local ASR is optional. When it is not configured, ReiLink keeps safe Voice Input fallback behavior.
- ReiLink does not commit, bundle, or automatically download a whisper binary.
- ReiLink does not commit, bundle, or automatically download a model file.
- ReiLink does not commit, bundle, or automatically download ffmpeg or any audio converter.
- The transcript only fills the chat input. ReiLink does not auto-send it.
- Before the user clicks send, the transcript does not enter memory, prompt preview, knowledge retrieval, or game context.
- Local ASR uses `zh` as the backend whisper language by default. UI language may show `zh-CN`; the backend normalizes that to `zh` before launching the local CLI.
- ASR transcripts are trimmed, whitespace-collapsed, and lightly normalized from Traditional Chinese to Simplified Chinese before they fill the input. This only applies to ASR transcripts.
- Local ASR paths can be typed or selected with native file picker buttons in Settings, then saved into the backend user data directory. They are not written into the repo, `.env`, or packaged `.app`.

## 2. Prerequisites / 前置条件

Prepare these locally, outside the repo and outside the packaged `.app`:

- A whisper.cpp-compatible CLI binary, such as `whisper-cli`, or an equivalent local ASR binary.
- A local whisper model file, such as a ggml-format model compatible with that binary.
- A local audio converter, such as an ffmpeg-like executable, if the recorder output is not WAV / PCM.
- macOS microphone permission for the ReiLink dev app or packaged `.app`.
- A ReiLink dev app or packaged `.app` build.

Use the corresponding project or vendor's official instructions to prepare those tools. Do not add automatic download scripts, model files, or binary files to this repository.

Model tradeoff:

- `ggml-base.bin` is a balanced starting point for speed and accuracy.
- `tiny` is usually faster but less accurate.
- `small`, `medium`, or larger models may be more accurate, but can be slower and may hit the 30 second transcription timeout.
- ReiLink shows only the safe model basename in Settings / Debug Panel and does not bundle a model.

## 3. Suggested Local Paths / 建议路径

Suggested user-managed locations:

```text
~/Library/Application Support/ReiLink/models
~/Library/Application Support/ReiLink/bin
```

These are only suggestions. You can use any stable local path that you control.

Do not place model files or binaries inside:

- the ReiLink repo
- `apps/desktop/release/.../ReiLink.app`
- any `.app/Contents/Resources` directory

Do not commit model files, whisper binaries, converter binaries, or local path configuration.

## 4. Configuration Sources / 配置来源

Recommended path:

1. Open Settings -> Voice Input.
2. In `本地 ASR 配置 / Local ASR Setup`, enter the local ASR binary path, model path, and optional audio converter path, or use the `选择...` buttons beside each field.
3. Click `保存配置 / Save`.
4. Click `重新检测 / Refresh Status`.

The saved file lives under the backend user data directory as:

```text
<settings.data_dir>/local_asr_settings.json
```

It stores only the user-provided path strings. The save action does not execute, download, or copy any binary or model.

The native file picker only fills the selected path into the matching input field. Canceling the picker keeps the existing input unchanged, and selecting a file does not read model contents, copy files, upload files, or save the setting until you click `保存配置 / Save`.

Environment variables are still supported as fallback when no saved user setting exists.

Configure these in the shell or app launch environment you use for ReiLink:

```bash
export REILINK_LOCAL_ASR_BINARY="/absolute/path/to/whisper-cli"
export REILINK_LOCAL_ASR_MODEL="/absolute/path/to/ggml-model.bin"
export REILINK_AUDIO_CONVERTER_BINARY="/absolute/path/to/ffmpeg"
```

Notes:

- `REILINK_LOCAL_ASR_BINARY` should point to an executable ASR CLI.
- `REILINK_LOCAL_ASR_MODEL` should point to an existing local model file.
- `REILINK_AUDIO_CONVERTER_BINARY` is optional for WAV / PCM input, but usually needed for browser-recorded WebM / Ogg.
- Saved user settings take priority over env fallback. Clearing saved settings returns ReiLink to env fallback or unconfigured state.
- ReiLink UI, Debug Panel, Raw JSON, and Event Stream show safe filenames, not full configured paths.
- Do not paste full local paths into public issues, screenshots, logs, or docs.
- Do not commit these environment variables, model files, or binary files.

For packaged `.app` runs, Settings persistence is preferred because environment variable propagation can differ from a dev shell. Do not edit the packaged `.app` to store paths.

## 5. Verification Flow / 验证流程

Run these steps in order:

1. Start ReiLink.
2. Open Settings -> Voice Input.
3. In `本地 ASR 配置 / Local ASR Setup`, save or confirm the safe basenames for:
   - binary configured
   - model configured
   - converter configured when needed
   You can type paths manually or use the `选择...` buttons; either way, click `保存配置 / Save` before refreshing status.
4. Check Local ASR config status:
   - ready / missing / not executable
5. Click `Check Local ASR`.
   - Expected: the local ASR binary can start.
   - This only proves the binary launches. It does not prove model compatibility or transcription quality.
6. Click `Audio Capture Test`.
   - Expected: recording completes, duration / size / MIME are shown, and temporary audio is cleaned.
7. If the recorded MIME is WebM / Ogg and `Record & Transcribe` reports conversion not configured, save an audio converter path in Settings or configure `REILINK_AUDIO_CONVERTER_BINARY` fallback.
   - Expected conversion status: `audio_conversion_succeeded`, or `audio_conversion_not_needed` for WAV / PCM.
8. Click `Record & Transcribe`.
   - Expected: the cleaned transcript fills the chat input.
   - Expected: Traditional Chinese output, if any, is lightly normalized to Simplified Chinese before it appears in the input.
   - Expected: ReiLink does not auto-send the transcript.
9. Review, edit, or delete the transcript manually.
10. Click send only when you decide the transcript should enter chat.
11. Expand Event Stream / Debug Panel and confirm:
    - no full transcript
    - no full binary / model / converter / audio path
    - no raw stdout / stderr
    - no API key, `.env`, Authorization header, or raw prompt

## 6. Release regression checklist / 发布回归清单

Use this checklist before freezing a release that touches voice input, Settings, Debug/Event surfaces, packaged runtime, or local data behavior.

1. Packaged app clean-start:
   - Run `make package-backend`.
   - Run `make package-desktop`.
   - Open packaged `ReiLink.app` directly, not the dev renderer.
   - Confirm the app is not a black screen and the backend becomes connected.
   - Confirm `.env`, memory, session, settings, and user data are not copied into `.app`.
   - Quit the app and confirm no app-owned backend process remains listening.
2. No-env setup:
   - Start without relying on `REILINK_LOCAL_ASR_BINARY`, `REILINK_LOCAL_ASR_MODEL`, or `REILINK_AUDIO_CONVERTER_BINARY`.
   - Open Settings -> Voice Input -> `本地 ASR 配置 / Local ASR Setup`.
   - Enter the ASR binary path, model path, and audio converter path manually, or use the `选择...` buttons.
   - Canceling the native file picker does not clear existing input values.
   - Save, then refresh status.
   - Confirm status becomes ready and UI shows only safe basenames.
3. Save / refresh / restart persistence:
   - Close and reopen packaged app.
   - Confirm source is user settings, safe basenames remain visible, and `Check Local ASR` can still start.
4. Local operation checks:
   - `Check Local ASR` succeeds.
   - `Audio Capture Test` succeeds and cleans temporary audio.
   - `Record & Transcribe` succeeds and fills the input.
   - The main chat voice button uses Local ASR when ready.
5. Transcript checks:
   - Traditional Chinese ASR output is normalized to Simplified Chinese.
   - English and numbers are not damaged by normalization.
   - Transcript only fills the input and is not sent automatically.
   - The user can edit or delete the transcript before manual send.
6. Privacy checks:
   - Event Stream, Debug Panel, and Raw JSON do not show full binary/model/converter paths, full temp audio paths, raw stdout/stderr, raw exceptions, full transcript, audio content, base64, API keys, `.env`, Authorization, raw prompt, or long internal payloads.
   - Safe basename, configured booleans, source, character count, language, conversion status, cleanup status, duration, and MIME summary are allowed.
7. Clear config fallback:
   - Click `清除配置 / Clear`.
   - Confirm Local ASR returns to env fallback or unconfigured state.
   - Confirm the main chat voice button shows a safe fallback and the app does not crash.
   - Confirm cleared full paths are not shown in Event Stream, Debug Panel, or Raw JSON.

## 7. Troubleshooting / 排查

| Status | Meaning | What to check |
| --- | --- | --- |
| `local_asr_not_configured` | Local ASR user settings and env fallback are missing or incomplete. | Save both local ASR binary and model paths in Settings, or set both environment variables in the app launch environment. |
| `local_asr_binary_missing` | The configured binary file was not found. | Check that the file exists locally and that Settings or env fallback points to the intended file. |
| `local_asr_binary_not_executable` | The configured binary exists but cannot execute. | Check local file permissions and macOS security prompts. |
| `local_asr_model_missing` | The configured model file was not found. | Check that the model file exists locally and is not inside the repo or `.app`. |
| `local_asr_probe_failed` | The binary started but probe returned failure. | Check whether the binary supports a help-style launch and is compatible with ReiLink's current assumptions. |
| `local_asr_probe_timed_out` | The probe did not finish in time. | Try a lighter binary, check whether the binary is blocked by the system, or run manual CLI checks outside ReiLink. |
| `audio_conversion_not_configured` | Recorded audio needs conversion but no usable converter is configured. | Save a local ffmpeg-like executable path in Settings, or set `REILINK_AUDIO_CONVERTER_BINARY` fallback. |
| `audio_conversion_failed` | Converter started but did not produce a usable WAV file. | Check converter compatibility and whether it can read the recorded MIME format. |
| `audio_conversion_timed_out` | Converter exceeded the conversion timeout. | Try a faster converter, shorter recording, or a lower-load machine. |
| `local_asr_transcription_no_text` | ASR completed but no safe transcript was parsed. | Check microphone input, model language fit, model quality, and output format compatibility. ReiLink shows `没有识别到可用文本`. |
| `local_asr_transcription_timed_out` | ASR did not finish before timeout. | ReiLink shows `本地语音识别超时，可以尝试更小模型或更短录音`. Try a smaller model, shorter recording, or faster local hardware. |
| `local_asr_transcription_failed` | ASR command failed or returned nonzero. | Check binary/model compatibility and current command strategy assumptions. |
| `audio_probe_cleanup_failed` | Audio probe temporary cleanup failed. | Retry and check local filesystem permissions; do not share full temp paths publicly. |

ReiLink intentionally keeps these diagnostics high-level. It should not expose full paths, raw subprocess output, or raw exception text in user-visible surfaces.

Accuracy tips:

- Speak short phrases.
- Keep the microphone close and reduce background noise.
- Try `base` before larger models; move to a larger model only when accuracy matters more than speed.
- If larger models time out, use a shorter recording or a smaller model.
- ReiLink does not run LLM correction, translation, term correction, or cloud ASR on the transcript.

## 8. Privacy / 隐私边界

- ReiLink does not upload audio to external services.
- ReiLink does not use cloud ASR.
- ReiLink does not save audio by default.
- Temporary audio is cleaned after completion, failure, timeout, or error.
- Transcript only fills the input.
- Transcript normalization is local and limited to ASR transcript cleanup. It does not modify typed user text, assistant replies, memory, or knowledge files.
- Before the user clicks send, transcript does not enter memory, prompt preview, knowledge retrieval, or game context.
- Full paths may appear in Settings editing inputs and `<settings.data_dir>/local_asr_settings.json`; they should not appear in Event Stream, Debug Panel, Raw JSON, chat, screenshots, or docs.
- Event Stream does not show the full transcript.
- Event Stream / Debug Panel may show safe character count, duration, MIME, conversion status, cleanup status, safe binary/model/converter basename, language, and whether the transcript was `已规范为简体中文`.
- Debug Panel does not show raw stdout / stderr, raw exception, full transcript, or full local paths.

## 9. Known Limitations / 已知限制

- Real whisper.cpp CLI flags can differ between versions and builds.
- ReiLink currently assumes a whisper.cpp-like command shape.
- Audio conversion requires a user-configured local converter.
- Saved Settings are preferred for packaged `.app`; environment variables may not match a dev shell environment.
- Larger models can be slow.
- Lower-performance machines can hit transcription or conversion timeouts.
- Different microphones, permissions, and system privacy settings can affect recording.
- `local_asr_probe_succeeded` only proves the binary can start; it does not guarantee model compatibility or transcript quality.
- Simplified Chinese normalization is a lightweight local mapping for common ASR output. It is not full language correction, translation, or game-term correction.
