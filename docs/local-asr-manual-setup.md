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

## 4. Environment Variables / 环境变量

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
- ReiLink UI and Debug Panel show safe filenames, not full configured paths.
- Do not paste full local paths into public issues, screenshots, logs, or docs.
- Do not commit these environment variables, model files, or binary files.

For packaged `.app` runs, environment variable propagation can differ from a dev shell. Launch the app from an environment where these variables are present, or use your own local launcher outside the repo. Do not edit the packaged `.app` to store paths.

## 5. Verification Flow / 验证流程

Run these steps in order:

1. Start ReiLink.
2. Open Settings -> Voice Input.
3. Check Local ASR config status:
   - binary configured
   - model configured
   - ready / missing / not executable
4. Click `Check Local ASR`.
   - Expected: the local ASR binary can start.
   - This only proves the binary launches. It does not prove model compatibility or transcription quality.
5. Click `Audio Capture Test`.
   - Expected: recording completes, duration / size / MIME are shown, and temporary audio is cleaned.
6. If the recorded MIME is WebM / Ogg and `Record & Transcribe` reports conversion not configured, set `REILINK_AUDIO_CONVERTER_BINARY` and restart ReiLink from that environment.
   - Expected conversion status: `audio_conversion_succeeded`, or `audio_conversion_not_needed` for WAV / PCM.
7. Click `Record & Transcribe`.
   - Expected: the cleaned transcript fills the chat input.
   - Expected: Traditional Chinese output, if any, is lightly normalized to Simplified Chinese before it appears in the input.
   - Expected: ReiLink does not auto-send the transcript.
8. Review, edit, or delete the transcript manually.
9. Click send only when you decide the transcript should enter chat.
10. Expand Event Stream / Debug Panel and confirm:
    - no full transcript
    - no full binary / model / converter / audio path
    - no raw stdout / stderr
    - no API key, `.env`, Authorization header, or raw prompt

## 6. Troubleshooting / 排查

| Status | Meaning | What to check |
| --- | --- | --- |
| `local_asr_not_configured` | Local ASR env is missing or incomplete. | Set both local ASR binary and model environment variables in the app launch environment. |
| `local_asr_binary_missing` | The configured binary file was not found. | Check that the file exists locally and the app was launched with the intended env. |
| `local_asr_binary_not_executable` | The configured binary exists but cannot execute. | Check local file permissions and macOS security prompts. |
| `local_asr_model_missing` | The configured model file was not found. | Check that the model file exists locally and is not inside the repo or `.app`. |
| `local_asr_probe_failed` | The binary started but probe returned failure. | Check whether the binary supports a help-style launch and is compatible with ReiLink's current assumptions. |
| `local_asr_probe_timed_out` | The probe did not finish in time. | Try a lighter binary, check whether the binary is blocked by the system, or run manual CLI checks outside ReiLink. |
| `audio_conversion_not_configured` | Recorded audio needs conversion but no usable converter is configured. | Set `REILINK_AUDIO_CONVERTER_BINARY` to a local ffmpeg-like executable and restart ReiLink from that environment. |
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

## 7. Privacy / 隐私边界

- ReiLink does not upload audio to external services.
- ReiLink does not use cloud ASR.
- ReiLink does not save audio by default.
- Temporary audio is cleaned after completion, failure, timeout, or error.
- Transcript only fills the input.
- Transcript normalization is local and limited to ASR transcript cleanup. It does not modify typed user text, assistant replies, memory, or knowledge files.
- Before the user clicks send, transcript does not enter memory, prompt preview, knowledge retrieval, or game context.
- Event Stream does not show the full transcript.
- Event Stream / Debug Panel may show safe character count, duration, MIME, conversion status, cleanup status, safe binary/model basename, language, and whether the transcript was `已规范为简体中文`.
- Debug Panel does not show raw stdout / stderr, raw exception, full transcript, or full local paths.

## 8. Known Limitations / 已知限制

- Real whisper.cpp CLI flags can differ between versions and builds.
- ReiLink currently assumes a whisper.cpp-like command shape.
- Audio conversion requires a user-configured local converter.
- Packaged `.app` environment variables may not match a dev shell environment.
- Larger models can be slow.
- Lower-performance machines can hit transcription or conversion timeouts.
- Different microphones, permissions, and system privacy settings can affect recording.
- `local_asr_probe_succeeded` only proves the binary can start; it does not guarantee model compatibility or transcript quality.
- Simplified Chinese normalization is a lightweight local mapping for common ASR output. It is not full language correction, translation, or game-term correction.
