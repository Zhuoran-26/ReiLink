# Voice Input v2 Local ASR Feasibility Spike

## 1.1 当前 Web Speech Recognition 结论

Voice Input v1 依赖 Electron renderer 中的 `SpeechRecognition` / `webkitSpeechRecognition`。实测 packaged `.app` 中构造器可以存在，麦克风权限也可以是已允许，但识别服务仍会返回“语音识别服务不可用”。这说明 Web Speech Recognition 在 ReiLink 的 Electron packaged runtime 里不能作为稳定主路径。

v1 仍然有保留价值：

- 提供聊天输入区的语音入口和安全 fallback。
- 让 Settings / Debug Panel 显示当前运行环境、麦克风权限和服务状态。
- 维持 push-to-talk 的用户流程，不做 wake word 或后台常驻监听。
- 识别文本只填入输入框，不自动发送。
- 未确认文本不进入 memory、prompt、knowledge retrieval 或 game context。

结论：Web Speech Recognition 只适合作为可用性探测和临时 fallback。Voice Input v2 如果要稳定可用，应评估本地 ASR。

## 1.2 本地 ASR 候选方案

### 方案 A：whisper.cpp / local whisper binary

优点：

- 本地离线运行，符合 ReiLink local-first 的隐私方向。
- 音频不需要上传给云服务。
- 可以由 backend subprocess 调用，避免 renderer 直接管理大模型和 native binary。
- 后端可以统一处理 binary path、model path、超时、错误映射和临时文件清理。
- 可以在 Event Stream 中只记录“开始转写 / 完成 / 失败”等摘要。

风险：

- 模型文件体积大，不能直接塞进当前 spike 或普通源码提交。
- 首次配置复杂：用户需要获取模型、放置模型，并理解当前模型状态。
- 打包体积和 release 分发策略需要单独设计。
- Apple Silicon / Intel 可能需要不同 binary 或不同性能预期。
- 低端机器延迟可能明显，尤其是较大模型。
- 需要录音格式转换，whisper CLI 常见输入格式可能与浏览器采集格式不同。
- 临时音频文件必须可靠清理，清理失败也不能泄露到 UI。
- license、模型来源和模型再分发权限需要在实现前逐项确认。

### 方案 B：系统听写作为临时替代

用户可以使用 macOS 系统听写直接把文字输入到 ReiLink 聊天框。

优点：

- ReiLink 不需要实现 ASR。
- 不引入模型文件、native binary 或额外打包体积。
- 可以立刻作为 v1 fallback 的用户提示。

缺点：

- 不是 ReiLink 内置能力。
- ReiLink 无法观测转写状态、错误原因或质量。
- 不适合做未来统一的 Voice / Live2D / Overlay 交互事件基础。

### 方案 C：云 ASR / 商业 ASR

云 ASR 可以降低本地配置复杂度，但会上传音频，且引入外部服务、计费、隐私和供应商依赖。ReiLink 当前是本地优先的桌面 companion，本次 spike 不采用云 ASR，不添加任何云 ASR 代码。

## 1.3 推荐架构

### 路径 1：Renderer 录音，Backend 转写

流程：

```text
Renderer push-to-talk
-> 采集短音频
-> 交给 backend local ASR endpoint
-> backend 写入临时文件
-> backend 调用 local ASR subprocess
-> backend 返回 transcript 摘要和文本
-> renderer 填入输入框
-> 用户手动发送
```

优点：

- Renderer 只负责用户手势、录音状态和输入框，不管理模型。
- Backend 统一管理 binary path、model path、临时文件、subprocess、超时和错误。
- 可以沿用当前“不自动发送”的安全边界。
- Event Stream 可以只显示字数、状态和中文错误，不显示完整 transcript。

风险：

- Renderer 仍需实现音频采集和上传到本机 backend。
- 需要确认本机 HTTP 传输和临时文件处理的隐私边界。

### 路径 2：Renderer 调用本地 ASR binary

流程：

```text
Renderer push-to-talk
-> renderer 保存音频
-> renderer 调用或间接触发 local binary
-> transcript 回填输入框
```

优点：

- 路径看起来短。

风险：

- renderer 会接触 native binary、模型路径、临时文件和 subprocess 细节。
- Electron 安全边界更脆弱，未来 packaged 行为更难测试。
- 更容易把 raw path、subprocess output 或长 payload 泄露到 Debug / Event Stream。

推荐路径：Renderer 录音，Backend 转写。Renderer 不直接管理大模型或 subprocess；Backend 负责本地 ASR runtime；transcript 回到输入框后仍需用户手动点击发送。

## 1.4 数据与隐私边界

默认原则：

- 不上传音频。
- 不保存用户音频。
- 不把音频写入 memory、session 或 `.app`。
- 不把未确认 transcript 写入 memory。
- 不把未确认 transcript 写入 prompt。
- 不触发 knowledge retrieval。
- 不触发 game context extraction。
- 只有用户点击 `发送` 后，文本才进入现有 chat flow。

临时文件策略：

- 如果需要落盘，backend 在用户数据目录下使用临时目录，例如 `~/Library/Application Support/ReiLink/data/tmp/voice-input`。
- 临时文件名使用随机 id，不包含用户文本。
- ASR subprocess 完成、失败或超时后立即删除临时音频。
- 删除失败时记录安全状态，不在 UI、Event Stream 或 Raw JSON 中显示完整路径。
- 后续设置可提供“不保留音频”作为默认且不可关闭的基础原则；如果未来要支持调试保留音频，需要单独的显式开发开关，不能默认启用。

Transcript 策略：

- ASR 完成后，renderer 只把 transcript 填入聊天输入框。
- Event Stream 只显示 `识别完成 / N 字`，不显示完整 transcript。
- Debug Panel 可以显示状态、模型名摘要、耗时和字数，不显示完整 transcript、raw subprocess output 或完整路径。

## 1.5 模型与 binary 策略

本次 spike 不提交模型文件，不提交 whisper binary，不下载任何模型。

后续策略建议：

- 用户手动放置模型到 `~/Library/Application Support/ReiLink/models`。
- 用户数据仍在 `~/Library/Application Support/ReiLink/data`。
- `.app` 内只放只读资源，不写入用户数据、模型、memory 或 session。
- `.env` 不复制进 `.app`。
- local ASR binary 可以先通过配置路径或环境变量探测，不默认打入 `.app`。
- 后续可以提供下载引导，但不自动下载模型，不在没有用户确认的情况下联网。
- 若未来要随 app 分发 binary，需要单独处理 Apple Silicon / Intel、签名、公证、license 和 release 体积。

## 1.6 Runtime 状态设计

建议未来状态：

| 状态 | Settings Panel | Event Stream | Debug Panel |
| --- | --- | --- | --- |
| `voice_input_unavailable` | 语音输入不可用 | 语音输入不可用 | 中文原因摘要 |
| `voice_input_web_speech_unavailable` | Web 语音识别服务不可用 | 语音识别服务不可用 | 不显示 raw error |
| `local_asr_not_configured` | 本地语音识别未配置 | 本地语音识别未配置 | binary / model 摘要 |
| `local_asr_ready` | 本地语音识别可用 | 本地语音识别可用 | 模型名摘要、设备摘要 |
| `local_asr_model_missing` | 缺少本地语音模型 | 缺少语音模型 | 不显示完整路径 |
| `local_asr_binary_missing` | 缺少本地识别程序 | 缺少识别程序 | 不显示完整路径 |
| `local_asr_binary_not_executable` | 识别程序不可执行 | 识别程序不可执行 | 不显示完整路径 |
| `local_asr_transcribing` | 正在识别 | 语音识别开始 | 耗时、音频时长摘要 |
| `local_asr_completed` | 已填入输入框 | 识别完成 / N 字 | 不显示完整 transcript |
| `local_asr_error` | 本地语音识别失败 | 语音识别失败 | 中文错误和安全状态 |

显示要求：

- 中文可读。
- 不显示完整 transcript。
- 不显示完整本地路径。
- 不显示 raw subprocess output。
- 不显示长 payload。
- 不显示 API key、Authorization、`.env` 或 raw prompt。

## 1.7 后续实现任务拆分

1. Local ASR config detection v1
   - 当前已实现：读取 `REILINK_LOCAL_ASR_BINARY` 和 `REILINK_LOCAL_ASR_MODEL`，检测 binary 是否存在且可执行、model 是否存在。
   - 当前状态：`local_asr_not_configured`、`local_asr_binary_missing`、`local_asr_binary_not_executable`、`local_asr_model_missing`、`local_asr_ready`。
   - 当前边界：只做配置检测，不调用 whisper 或任何 ASR binary，不录音，不转写，不上传音频，不下载模型，不把模型或用户数据写入 `.app`。
   - UI 只显示中文摘要和安全文件名，不显示完整路径、raw env、raw subprocess output、API key、`.env` 或 raw prompt。

2. Local ASR CLI probe v1
   - 目标：安全调用 `--help` 或轻量 probe，确认 binary 可执行。
   - 风险：subprocess 超时、签名限制、raw output 泄露。

3. Audio capture / temp file v1
   - 目标：renderer push-to-talk 采集短音频并交给 backend。
   - 风险：音频格式、权限、临时文件清理。

4. Backend ASR subprocess bridge v1
   - 目标：backend 调用 local ASR binary，返回 transcript。
   - 风险：超时、并发、错误映射、模型路径配置。

5. Renderer push-to-talk local ASR integration v1
   - 目标：把 transcript 填入输入框，不自动发送。
   - 风险：状态同步、取消识别、Event Stream 隐私。

6. Packaged `.app` local ASR smoke v1
   - 目标：验证 packaged app 中配置检测、backend 自启动、用户模型目录和 fallback。
   - 风险：未签名 binary、路径差异、退出后进程清理。

7. Local ASR QA / privacy polish v1
   - 目标：补齐机器可读场景、manual QA 和隐私回归。
   - 风险：完整 transcript、完整路径或 raw subprocess output 泄露。
