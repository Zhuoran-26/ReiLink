# Manual QA Pack / Regression Scenarios v1

## 中文

这份 QA Pack 用于在继续开发 Voice Input 后续能力、Live2D、Overlay、embedding RAG 之前，快速回归 ReiLink 当前已经稳定的交互底座。它覆盖手动检查、packaged app smoke、Knowledge Retrieval、Voice Output、Voice Input、Event Stream / Debug 隐私，以及 release 前 runtime sanity。

配套机器可读场景文件：

- `docs/qa/retrieval_scenarios.json`
- `docs/qa/voice_input_scenarios.json`
- `docs/qa/voice_input_local_asr_scenarios.json`

### 1. 基础启动检查

#### Dev App

- 启动 backend：`make dev-backend`。
- 启动 desktop：`make dev-desktop`。
- 主界面不是黑屏。
- 主聊天区、输入框、设置区、右侧面板正常显示。
- `curl http://127.0.0.1:8000/api/health` 返回 `{"status":"ok"}`。
- Settings Panel 可见。
- Debug Panel 可见。
- `事件流 / Event Stream` 标题可见，默认折叠，展开后能看到事件或“暂无事件”。
- Local Data controls 显示用户数据目录，memory / session 写入用户数据目录，不写入 `.app`。
- `.env` 不出现在 UI、Event Stream、Raw JSON 或 packaged resources 中。

#### Packaged `.app`

- 如 backend 代码、schema、knowledge loading 或 runtime 发生变化，先运行 `make package-backend`。
- 运行 `make package-desktop`。
- 直接打开 `apps/desktop/release/ReiLink-darwin-<arch>/ReiLink.app`，不要打开 dev renderer。
- UI 不是黑屏。
- 后端最终显示已连接，或 health endpoint 返回 `{"status":"ok"}`。
- packaged app 使用内置 backend binary 或健康的外部 backend，启动来源显示为用户可读摘要。
- bundled knowledge resources 可用。
- Settings Panel、Debug Panel、Event Stream 可见。
- `.env`、API key、memory、session 和用户数据不复制进 `.app`。
- app 退出后，由 app 自启动的 backend 没有残留进程。

### 2. Voice Output 回归检查

- `语音输出 / Voice Output` 默认关闭。
- `测试语音 / Test Voice` 按钮可见。
- `语速 / Rate` 和 `音量 / Volume` 控件可见。
- 默认关闭时，assistant 回复不会播放语音。
- 点击 `测试语音 / Test Voice` 后，语音开始前显示准备状态。
- Test Voice 只有在 `utterance.onstart` 后才记录“语音开始播放”。
- Test Voice 正常结束后记录“语音播放完成”。
- 播放中显示正在播放。
- 播放中 `停止语音 / Stop Voice` 可见。
- 点击 Stop Voice 可以停止当前播放，并记录“语音已停止”。
- 播放中发送新用户消息会停止当前语音。
- 关闭 Voice Output 会停止当前语音。
- Voice Output 开启时，assistant 最终回复会触发语音播放。
- 如果 5 秒内没有真实开始播放，Event Stream 显示“语音播放失败”或等价中文摘要。
- 更换系统语音包后，Test Voice 仍应允许失败并显示可理解错误，不应卡死 UI。
- Event Stream 不显示完整 assistant 回复文本。
- Event Stream 不显示完整测试语音文本。
- Event Stream 不显示 raw prompt、API key、`.env`、Authorization、完整路径或长 internal payload。

### 3. Voice Input push-to-talk 回归检查

- 聊天输入区附近可见 `开始语音 / Start Voice`。
- Settings Panel 可见 `语音输入 / Voice Input`。
- Settings 显示本地语音识别是否可用、当前状态、语言、最近识别字数和最近错误。
- Settings / Debug Panel 显示安全诊断摘要：`语音识别功能`、`麦克风权限`、`运行环境`。
- 默认不监听；只有用户点击开始后才进入 `正在听 / Listening` 或 `正在识别 / Recognizing`。
- 不做 wake word，不做后台常驻监听。
- Voice Input v1 依赖浏览器运行时提供的 `SpeechRecognition` / `webkitSpeechRecognition`。如果 Electron / Chromium 不提供该 API，显示 `当前运行环境不支持本地语音识别`，按钮不可启动，App 不崩溃。
- 不支持本地语音识别时，Settings 应提示用户仍可使用系统听写把文本输入到聊天框。
- 如果 constructor 存在但 `start()` 失败，显示 `语音输入启动失败` 或等价中文摘要，不应误报为环境不支持。
- 如果 constructor 存在、麦克风已允许，但浏览器返回服务错误，显示 `语音识别服务不可用`，Settings 顶部应显示 `服务不可用`，不应继续显示为 `可用`。
- 如果麦克风或识别权限被拒绝，显示 `麦克风权限被拒绝` 或等价中文摘要，App 不崩溃。
- 如果没有识别到语音，显示 `没有识别到语音` 或等价中文摘要。
- 如果用户主动停止或浏览器返回 aborted，显示 `用户停止` 或等价中文摘要。
- final transcript 只填入聊天输入框，用户可以编辑。
- interim transcript 只影响识别状态，不自动发送。
- final transcript 不自动发送；只有用户点击 `发送` 后才进入现有 chat flow。
- 未确认 transcript 不进入 memory。
- 未确认 transcript 不进入 prompt / context。
- 未确认 transcript 不触发 game context extraction。
- 未确认 transcript 不触发 knowledge retrieval。
- 开始 Voice Input 时会停止当前 Voice Output 播放，并在 Event Stream 中显示安全摘要。
- `测试语音 / Test Voice` 仍然可见且可用。
- Voice Output 开启后，assistant 最终回复仍可播放。
- Voice Output 关闭时，assistant 回复不播放语音。
- Event Stream 可显示 `语音输入开始`、`语音输入完成`、`语音输入已停止`、`语音输入失败`、`语音输入不可用`。
- Event Stream 只显示字数、语言和中文状态，不显示完整 transcript、raw recognition event、permission object、audio data、raw prompt、API key、`.env`、Authorization 或完整本地路径。

#### Packaged `.app` Voice Input

- 直接打开 packaged `ReiLink.app`，不是 dev renderer。
- UI 非黑屏，backend 自启动。
- `开始语音 / Start Voice` 和 `语音输入 / Voice Input` 可见。
- Settings 显示 `语音识别功能`、`麦克风权限` 和 `运行环境：打包应用`。
- 如果 packaged 环境支持 Web Speech Recognition，点击开始后可进入听写状态，final transcript 填入输入框但不自动发送。
- 如果 packaged 环境不支持 Web Speech Recognition，显示 `当前运行环境不支持本地语音识别`，并提示可使用系统听写，不崩溃。
- 如果 packaged 环境暴露 Web Speech Recognition 但服务不可达，显示 `语音识别服务不可用` 和 `服务不可用`，并提示可使用系统听写，不崩溃。
- 如果权限被拒绝，显示 `麦克风权限被拒绝` 或等价中文错误，不崩溃。
- packaged `Info.plist` 应包含麦克风用途说明，避免权限提示缺失。
- `测试语音 / Test Voice` 仍可见。
- Knowledge Retrieval 仍可用。
- Event Stream 不泄露完整 transcript 或敏感信息。
- 退出后，由 app 自启动的 backend 没有残留进程。

### 4. Voice Input v2 local ASR feasibility / 本地语音识别可行性

设计文档见 `docs/voice-input-local-asr-spike.md`，机器可读场景见 `docs/qa/voice_input_local_asr_scenarios.json`。

- 当前 Web Speech Recognition 在 Electron packaged app 中可能暴露 API，但识别服务不可用；Voice Input v1 的预期是显示 `语音识别服务不可用` 或明确 unavailable fallback，不崩溃。
- v1 仍保留输入框入口、安全 fallback、系统听写提示和“不自动发送”的边界。
- 当前 Local ASR Config Detection v1 只检测配置，不执行 whisper / ASR binary，不录音，不转写，不上传音频，不下载模型，不把模型或用户数据写入 `.app`。
- Local ASR 配置来源仅为 `REILINK_LOCAL_ASR_BINARY` 和 `REILINK_LOCAL_ASR_MODEL`。
- Settings / Debug Panel 应显示 `本地语音识别 / Local ASR` 状态；状态包括未配置、缺少本地识别程序、识别程序不可执行、缺少本地语音模型、已就绪。
- 未配置：两个环境变量都为空，或只配置了识别程序但未配置模型；显示用户可读中文提示，Voice Input 仍回退到系统听写提示。
- 缺少本地识别程序：配置了 binary 但文件不存在；UI 只显示安全文件名，不显示完整路径。
- 识别程序不可执行：binary 文件存在但没有执行权限；UI 只显示中文状态和安全文件名，不显示完整路径。
- 缺少本地语音模型：binary 可执行但 model 文件不存在；UI 只显示安全模型名，不显示完整路径。
- 已就绪：binary 存在且可执行、model 存在；当前仍不会自动识别语音，也不会调用 whisper。
- Local ASR CLI Probe v1 只在配置已就绪时允许点击 `检查本地 ASR / Check Local ASR`；配置未就绪、缺少识别程序或缺少模型时按钮不可用。
- Probe 只执行本地识别程序的 `--help` 或 `-h` 启动检查，超时时间短；成功只代表 binary 可以启动，不代表模型兼容，也不代表可以转写语音。
- Probe 不录音，不读取音频，不传入音频路径，不传入模型路径，不创建临时音频文件，不上传音频。
- Probe 不填入聊天输入框，不自动发送，不写 memory / prompt，不触发 knowledge retrieval 或 game context extraction。
- Probe UI 只显示 `未检查`、`正在检查`、`可以启动`、`启动失败`、`启动超时`、`配置未就绪` 等中文摘要和安全文件名。
- Probe UI、Debug Panel、Raw JSON 不显示完整路径、raw stdout、raw stderr、raw exception、raw env、API key、`.env`、Authorization 或 raw prompt。
- Packaged `.app` 中未配置时应安全显示配置未就绪；配置 fake binary / fake model 时可手动验证 `可以启动`，退出后 backend 无残留。
- Audio Capture / Temp File v1 只在用户点击 `测试录音 / Test Recording` 后请求麦克风权限；权限拒绝时显示 `麦克风权限被拒绝` 或等价中文 fallback。
- 录音测试默认录制短音频，最长不超过 5 秒；用户可点击 `停止录音 / Stop Recording` 提前停止。
- Renderer 使用 `MediaRecorder` 生成音频 blob，只发送到本机 backend audio probe endpoint；不调用 whisper，不调用 local ASR binary，不调用云 ASR，不转写。
- Backend audio probe 最大上传大小为 2MB；过大返回 `录音文件过大`，无效 MIME 或空数据返回 `录音数据无效`。
- Backend audio probe 写入系统临时目录，立即删除临时音频；清理失败时显示 `临时音频清理失败`，不暴露完整路径。
- Audio Capture UI、Debug Panel 和 Event Stream 只显示录音时长、大小、MIME 和清理状态，不显示音频内容、base64、完整临时路径、raw exception、API key、`.env`、Authorization 或 raw prompt。
- Audio Capture 不填入聊天输入框，不自动发送，不写 memory / prompt，不触发 knowledge retrieval 或 game context extraction。
- Backend ASR Transcription Bridge v1 只在 Local ASR config status 为 `local_asr_ready` 时启用 `录音并转写 / Record & Transcribe`。
- config not ready 时，转写按钮不可用；backend 返回 `local_asr_transcription_not_ready`，不运行 binary。
- config ready 时，用户点击后才请求麦克风权限，录制短音频并上传到本机 backend transcription endpoint。
- Backend transcription 写入系统临时目录 `reilink-local-asr-*`，调用 configured local ASR binary，传入 model path 和 temp audio path，随后清理临时音频。
- 默认 ASR command 使用 subprocess list args：`[binary, "-m", model_path, "-f", audio_path, "-nt"]`，可追加安全 language 参数；不使用 `shell=True`。
- Transcription timeout 为 30 秒；timeout 时返回 `local_asr_transcription_timed_out` 或等价安全状态。
- fake binary smoke：配置 `REILINK_LOCAL_ASR_BINARY` 和 `REILINK_LOCAL_ASR_MODEL`，fake binary 输出固定 transcript，确认输入框被回填。
- 正常 transcript 只填入聊天输入框，用户可编辑；不会自动发送。
- 未确认 transcript 不写 memory，不进入 prompt / retrieval / game context，也不触发 semantic/game extraction。
- 空 transcript 返回 `local_asr_transcription_no_text`，UI 显示中文提示，不改输入框。
- fake binary nonzero 返回 `local_asr_transcription_failed`，不显示 raw stdout / stderr。
- subprocess OS error 返回 `local_asr_transcription_error`，不显示 raw exception。
- cleanup succeeded 时 response / UI 显示临时音频已清理。
- cleanup failed 时返回 `local_asr_transcription_cleanup_failed`，不显示 temp path、raw exception 或 transcript。
- Event Stream 只显示 `本地语音识别开始`、`本地语音识别完成`、`本地语音识别失败`、字数、duration、size、MIME、cleanup 和安全 status。
- Event Stream、Debug Panel、Raw JSON 不显示完整 transcript、raw stdout、raw stderr、完整 binary/model/temp path、audio content、base64、API key、`.env`、Authorization 或 raw prompt。
- packaged `.app` smoke 需要确认未配置时 Local Transcribe disabled；可选 fake binary / fake model smoke 确认 packaged app 仍不泄露 transcript 或路径。
- Packaged `.app` 应包含麦克风用途说明：`ReiLink 需要麦克风权限用于用户主动触发的语音输入测试。`
- Local ASR QA 后续重点是：转写中状态、错误中文映射、临时音频清理、packaged `.app` fallback 和 Event Stream 隐私。
- 用户临时替代方案：使用系统听写直接输入到聊天框。
- 默认不上传外部服务，不保存音频，不自动发送 transcript。
- 未确认 transcript 不进入 memory、prompt、knowledge retrieval 或 game context。
- 当前配置检测不会产生音频或 transcript。Event Stream / Debug / Raw JSON 不显示完整 transcript、完整音频路径、raw subprocess output、API key、`.env`、Authorization、完整本地路径或 raw prompt。

#### Local ASR real compatibility QA

本矩阵用于真实 whisper.cpp 兼容性准备，不要求把 whisper binary、模型文件、ffmpeg 或任何第三方二进制提交进仓库。当前 bridge 仍假设 whisper.cpp-like CLI：`-m <model>`、`-f <audio>`、`-nt` 和可选 `-l <language>`；真实兼容性必须在用户本机手动验证。

5.1 未配置：

- 清空 `REILINK_LOCAL_ASR_BINARY` 和 `REILINK_LOCAL_ASR_MODEL`。
- Settings 显示 Local ASR not configured / 本地语音识别未配置。
- `录音并转写 / Record & Transcribe` disabled，backend 不启动 binary。

5.2 fake binary：

- 使用临时 fake executable 和临时 fake model file，不提交到 repo。
- fake binary 可分别输出纯文本、timestamp 文本、带日志文本、空文本和超长文本。
- 期望 config ready，probe succeeded，transcribe 返回 fake transcript 或 no_text。
- transcript 只填入输入框，不自动发送。
- Event Stream / Debug / Raw JSON 不显示 full transcript、raw stdout/stderr、完整 binary/model/temp path。

5.3 real whisper binary + model：

- 用户本地自行准备真实 whisper.cpp binary 和 model，推荐模型目录：`~/Library/Application Support/ReiLink/models`。
- 设置 `REILINK_LOCAL_ASR_BINARY` 和 `REILINK_LOCAL_ASR_MODEL`。
- 打开 dev app，运行 `Check Local ASR`，确认只显示安全文件名。
- 运行 `Audio Capture Test`，记录安全 MIME summary，例如 `audio/webm`、`audio/wav` 或 `unknown`。
- 运行 `Record & Transcribe`，检查 transcript 是否进入输入框且不会自动发送。
- 检查 Event Stream 不显示完整 transcript。
- 检查是否出现 `当前录音格式可能需要后续转换为 WAV`；如果真实 whisper 无法读取 `audio/webm`，后续拆 `Audio Format Conversion v1`。

5.4 packaged app：

- 未配置时安全 fallback，Local Transcribe disabled 或显示配置未就绪。
- fake binary optional；real whisper optional manual。
- 不显示完整路径、raw stdout / stderr、`.env`、API key 或 Authorization。
- `Audio Capture Test`、`Record & Transcribe`、`Test Voice` 和 Knowledge Retrieval 入口仍可见。
- 退出后 backend 无残留。

### 5. Knowledge Retrieval 回归检查

#### Elden Ring 命中

示例输入：

- `Margit 怎么打？`
- `Tree Sentinel 有什么打法？`（若当前 sample pack 尚无 Tree Sentinel 条目，用 `水鸟乱舞怎么躲？` 做稳定回归）
- `Elden Ring 里 Margit 有什么注意点？`

期望：

- selected game 为 Elden Ring / 艾尔登法环。
- retrieval status 为 `used`。
- Event Stream 显示“已使用本地知识”。
- Debug Panel 显示 matched terms、score、snippet preview。
- prompt/context 中有截断后的本地知识块。
- 不显示完整 knowledge entry 正文。
- 不显示 API key、raw prompt、`.env` 或完整本地路径。

#### Hollow Knight 命中

示例输入：

- `Hornet 怎么打？`
- `Hollow Knight 里 Greenpath 要注意什么？`

期望：

- selected game 为 Hollow Knight / 空洞骑士。
- retrieval status 为 `used`。
- Event Stream 显示“已使用本地知识”。
- 不误用 Elden Ring knowledge。

#### 跨游戏显式切换

当前上下文为 Elden Ring，用户输入：

- `我在玩 Hollow Knight，Hornet 怎么打？`
- `Hollow Knight 里的 Hornet 怎么打？`
- `空洞骑士里的 Hornet 怎么打？`

当前上下文为空洞骑士，用户输入：

- `Elden Ring 里的 Margit 怎么打？`
- `法环 Margit 怎么打？`

期望：

- 使用用户明确写出的游戏 knowledge。
- 不使用当前上下文里的另一个游戏 knowledge。
- 当用户明确写出另一个游戏名时，用户这句里的游戏名优先于当前游戏上下文。
- 如果用户没有明确写出游戏名，但当前游戏存在，则继续使用当前游戏。
- 如果既没有明确游戏名，也没有当前游戏，不做宽泛跨游戏检索。
- `Hollow Knight 里的 Hornet 怎么打？` 的检索词应聚焦 `Hornet`，不靠 `hollow` / `knight` 命中。
- `法环 Margit 怎么打？` 的检索词应聚焦 `Margit`，不靠 `elden` / `ring` 命中。
- Debug / Event Stream 显示可读中文摘要。
- 如果手动选择当前游戏，手动选择优先，并显示冲突或当前来源摘要。

#### 闲聊不触发 knowledge

示例输入：

- `今天有点累`
- `你在吗`
- `陪我聊一会`
- `谢谢`
- `我先休息一下`

期望：

- retrieval status 为 `not_game_related`。
- 不注入 knowledge prompt。
- Event Stream 可显示“这次不是游戏知识问题”。
- Rei 正常陪伴式回复。
- 不强行引用攻略。

#### 低相关不注入

示例输入：

- `这个东西怎么弄`
- `刚才那个有点难`
- `我不知道下一步怎么办`

期望：

- 如果只有弱命中，retrieval status 为 `below_threshold`。
- 不注入 knowledge prompt。
- 不强行引用攻略。
- Event Stream 和 Debug Panel 显示“相关性不足，未使用”或等价中文摘要。

#### no_pack 场景

示例输入：

- `我在玩只狼，弦一郎怎么打？`

期望：

- selected game 可识别为 Sekiro / 只狼。
- retrieval status 为 `no_pack`。
- 不崩溃。
- 不注入空 knowledge 模板。
- Event Stream 显示安全中文摘要。

#### not_found 场景

示例输入：

- 在当前游戏为 Elden Ring 时输入：`艾尔登法环里完全不存在的月光蘑菇钥匙在哪？`

期望：

- selected game 为 Elden Ring / 艾尔登法环。
- retrieval status 为 `not_found`。
- 不注入空 knowledge 模板。
- 不强行编知识包内容。

### 6. Debug / Event Stream 隐私检查

必须不能出现：

- API key value。
- Authorization header。
- `.env` 完整路径。
- backend binary 完整路径。
- complete local filesystem paths。
- raw prompt。
- full assistant reply。
- full Test Voice text。
- full Voice Input transcript。
- raw recognition event。
- full knowledge pack content。
- long backend/internal payload。

允许出现：

- `api_key_loaded: true/false`。
- selected game。
- retrieval status。
- result count。
- matched terms。
- score。
- snippet preview。
- TTS lifecycle 摘要。
- Voice Input lifecycle 摘要、字数、语言和中文错误。
- backend health summary。

### 7. Packaged `.app` Release Smoke Checklist

- 如果 backend 代码、schema、knowledge loading 或 runtime 发生变化，重新运行 `make package-backend`。
- 重新运行 `make package-desktop`。
- 直接打开 packaged `ReiLink.app`，不是 dev renderer。
- UI 非黑屏。
- backend 自启动，或复用健康外部 backend。
- bundled knowledge resources 可用。
- `语音输出 / Voice Output` 和 `测试语音 / Test Voice` 可见。
- `语音输入 / Voice Input` 和 `开始语音 / Start Voice` 可见。
- Voice Input supported / unsupported / permission fallback 可读，不崩溃。
- Knowledge Retrieval 可用。
- Event Stream 不泄露敏感内容。
- memory / session 写入用户数据目录，不写入 `.app`。
- `.env` 不复制进 `.app`。
- app 退出后，自启动 backend 无残留。

### 8. Release 前 Runtime Sanity

- `make lint`
- `make test-desktop`
- `make typecheck`
- `git diff --check`
- `make test-backend`
- `make validate-knowledge`
- 如果 e2e 已存在：`cd apps/desktop && npm run test:e2e`
- 如果 runtime / packaging / backend binary / knowledge loading 变更：`make package-backend && make package-desktop`
- packaged `.app` smoke 至少覆盖：非黑屏、backend health ok、bundled knowledge、Voice Output controls、Event Stream privacy。

### 9. Known Limitations

- `below_threshold` 依赖当前知识包内容和评分阈值，手动测试时可优先用机器可读场景文件里的弱相关示例。
- `no_pack` 依赖 catalog 中仍有 planned / unsupported 游戏；当前可用 `只狼` 做手动场景。
- Voice Input v1 只使用 Web Speech Recognition，不接商业 ASR，不上传音频，不保存音频。真实识别取决于 dev / packaged Electron 的 Chromium runtime 是否暴露该 API，以及 macOS 麦克风权限。
- 如果 Electron runtime 不支持 Web Speech Recognition，当前预期是明确 unavailable fallback；用户可临时使用系统听写输入到聊天框。Local ASR staged foundation 已接入 config detection、CLI probe、audio probe 和 backend transcription bridge，但真实 whisper.cpp / model 兼容性与 audio format conversion 仍属后续手动 QA / 实现任务。
- Voice Output 的真实播放取决于系统语音包和浏览器 speech synthesis 支持；失败必须被 UI 允许并可见，不应被视为崩溃。
- Manual QA 不替代 automated tests；它用于 release 前的人眼回归与打包行为确认。

## English

This QA Pack is a reusable manual regression checklist for ReiLink before future Voice / Local ASR expansion, Live2D, Overlay, and embedding RAG work. It focuses on the current foundations: local runtime, Voice Output, Voice Input fallback, Local ASR staged foundation, Knowledge Retrieval, Event Stream, Debug privacy, and packaged app smoke testing.

Machine-readable scenarios live at:

- `docs/qa/retrieval_scenarios.json`
- `docs/qa/voice_input_scenarios.json`
- `docs/qa/voice_input_local_asr_scenarios.json`

Use the Chinese checklist above as the source of truth for manual runs. Keep results short and concrete: pass/fail, exact app mode, exact commit, and any visible privacy issue.
