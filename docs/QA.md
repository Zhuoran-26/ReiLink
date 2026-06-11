# Manual QA Pack / Regression Scenarios v1

## 中文

这份 QA Pack 用于在继续开发 Voice Input 后续能力、Live2D、Overlay、embedding RAG 之前，快速回归 ReiLink 当前已经稳定的交互底座。它覆盖手动检查、packaged app smoke、Knowledge Retrieval、Voice Output、Voice Input、Event Stream / Debug 隐私，以及 release 前 runtime sanity。

Voice Interaction MVP 的 GitHub 更新草稿见 `docs/release-notes/reilink-voice-mvp.md`。

配套机器可读场景文件：

- `docs/qa/retrieval_scenarios.json`
- `docs/qa/voice_input_scenarios.json`
- `docs/qa/voice_input_local_asr_scenarios.json`
- `docs/qa/overlay_scenarios.json`
- `docs/qa/session_timeline_scenarios.json`
- `docs/qa/persona_pack_scenarios.json`

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
- ReiLink 应出现在 macOS Dock 和 `⌘ + Tab` 程序切换器；点击 Dock 图标或通过 `⌘ + Tab` 切回时，应能回到主窗口，且不应因为 overlay lifecycle 反复抢焦点。
- 后端最终显示已连接，或 health endpoint 返回 `{"status":"ok"}`。
- packaged app 使用内置 backend binary 或健康的外部 backend，启动来源显示为用户可读摘要。
- bundled knowledge resources 可用。
- Settings Panel、Debug Panel、Event Stream 可见。
- `.env`、API key、memory、session 和用户数据不复制进 `.app`。
- app 退出后，由 app 自启动的 backend 没有残留进程。

### 1.5 Voice / Local ASR / Overlay Safe Mode 阶段冻结人工验收

本节用于当前阶段 Regression Freeze。它不表示 macOS Overlay auto-show 已恢复；macOS 下不自动出现小气泡是当前预期。

#### A. Desktop Window Stability

1. packaged app 启动不黑屏。
2. ReiLink 出现在 Dock。
3. ReiLink 出现在 `⌘ + Tab`。
4. 可以切到 Finder / 浏览器。
5. ReiLink 不自动抢回焦点。
6. ReiLink 不始终置顶。
7. 主窗口边框和 macOS traffic lights 不疯狂闪烁。
8. Settings 可操作。
9. 关闭 / 最小化 / 全屏按钮正常。

#### B. Overlay Safe Mode

1. Overlay 默认关闭。
2. Settings 中 Overlay safe mode 文案可见。
3. 开启 Overlay 后 ReiLink 前台不显示小气泡，这是当前预期。
4. Settings 不被遮挡。
5. Settings 可以关闭 Overlay。
6. `强制关闭悬浮层` 按钮可用。
7. 位置 / 透明度 / 消息数量配置可保存。
8. macOS 下 auto-show 暂时不出现小气泡，这是当前预期。
9. Event Stream 不泄露 raw prompt、API key、`.env`、完整路径、完整 transcript、stdout/stderr 或 raw JSON。
10. 后续恢复 auto-show 前必须人工验证 packaged `.app`。

#### C. Local ASR Native File Picker

1. Local ASR Setup 三个路径旁有 `选择...` 按钮。
2. 点击按钮会打开系统原生 file picker。
3. 取消选择不清空原路径。
4. whisper binary 选择只更新 binary path。
5. model 选择只更新 model path。
6. converter 选择只更新 converter path。
7. 保存后 Refresh Status 能读取配置。
8. Check Local ASR 能正常 probe。
9. 重启后配置仍存在。
10. 主聊天语音输入仍可识别并填入输入框。
11. transcript 不自动发送。
12. Event Stream / Debug 不显示完整路径、stdout/stderr、transcript、API key 或 `.env`。

#### D. Voice / ASR Regression

1. Voice Output 默认关闭。
2. Test Voice 可用。
3. TTS 不朗读完整敏感内容到 Event Stream。
4. Web Speech fallback 不作为可靠主路径。
5. Local ASR ready 状态可显示。
6. Record & Transcribe 可用。
7. 识别结果填入输入框但不自动发送。
8. 用户确认后才进入 chat flow。
9. accepted memory 才进入 prompt。
10. proactive 内容不进入 memory。

### 1.6 Rei Persona Pack v1 回归检查

本节用于 Persona Pack v1。它不表示用户自定义角色、Live2D、TTS 音色或 persona 自动学习已开始。

1. `personas/rei/` 包含 persona、voice、boundaries、game companion policy、memory policy、proactive policy、examples、anti examples、references 和 `version.json`。
2. 主聊天 prompt 使用 structured Rei Persona Pack，但仍保留 base system safety / app identity。
3. Prompt Preview 继续保留脱敏后的 assembled prompt preview 能力；Event Stream / 普通 Debug 摘要不显示完整 prompt 或 persona markdown。
4. Debug Panel / Prompt Preview 只显示 persona pack id、version、enabled、status、loaded_sections、injected_sections、missing_sections、fallback 状态、`persona_section_truncated`、truncated_sections、`raw_content_omitted=true` 和 `path_omitted=true`。
5. Debug Panel / Prompt Preview 不显示完整 prompt、完整 persona markdown、完整用户输入、API key、`.env`、完整本地路径、raw stdout/stderr、raw JSON 或 ASR transcript 全文。
6. Persona Pack prompt 注入必须有长度预算：persona / voice / boundaries / policies 为主，examples / anti_examples 只取少量精选；内容过长时安全截断并在 Debug summary 显示 `persona_section_truncated`。
7. Persona Pack 文件和 assembled persona prompt 不包含外部官方 IP / 既有角色标识，例如 Evangelion、Rei Ayanami、NERV、EVA、永雏塔菲、taffy-skill 的具体文本、口癖或设定。
8. 发送 `我在艾尔登法环打玛尔基特，已经死了3次，有点烦。`，Rei 应先承接挫败，再给一个轻量建议；不应变成客服腔或长篇攻略百科。
9. 发送 `玛尔基特二阶段怎么打？`，Rei 可以给简短策略，但不要默认展开完整攻略站式打法。
10. 发送 `记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。`，仍应进入 pending memory confirmation，不应直接写入长期记忆。
11. 发送 `以后不用记住这个，只是我这次随便说一下。`，不应触发 pending memory。
12. Persona Pack 不应直接触发 proactive，也不应改变 Semantic Shadow candidate-only 边界。
13. 打包验证需运行 `make package-backend` 和 `make package-desktop`；packaged `.app` 中 `personas/rei` 应作为只读 resource 可用，缺失时必须 safe fallback，不应黑屏或 backend crash。

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

- 聊天输入区附近可见主语音按钮；Web Speech fallback 时显示 `开始语音 / Start Voice`，Local ASR ready 时显示 `开始本地语音 / Start Local ASR`。
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
- 主语音按钮和 `语音输入 / Voice Input` 可见。
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

设计文档见 `docs/voice-input-local-asr-spike.md`，真实手动配置指南见 `docs/local-asr-manual-setup.md`，机器可读场景见 `docs/qa/voice_input_local_asr_scenarios.json`。

#### Local ASR v1 Release Regression / 本地语音输入 v1 发布回归

Local ASR v1 已达到 packaged app 可配置 MVP：用户可在 Settings 中保存本地 ASR binary、model 和 converter 路径，主聊天语音按钮在 ready 时优先使用本地 ASR，transcript 只填入输入框且不会自动发送。每次修改 Overlay、Live2D、RAG、packaging、voice 或 debug surfaces 前后，都应先按本清单做 release regression。

1. Clean packaged app startup:
   - 运行 `make package-backend`。
   - 运行 `make package-desktop`。
   - 直接打开 packaged `ReiLink.app`，不要打开 dev renderer。
   - App 非黑屏，后端自启动，顶部或 Settings 显示已连接。
   - `.env` 不复制进 `.app`。
   - memory / session / settings 写入用户数据目录，不写入 `.app`。
   - 退出 app 后，由 app 自启动的 backend 没有残留监听进程。
2. No-env Local ASR setup:
   - 不依赖 `REILINK_LOCAL_ASR_BINARY` / `REILINK_LOCAL_ASR_MODEL` / `REILINK_AUDIO_CONVERTER_BINARY`。
   - Settings -> Voice Input -> `本地 ASR 配置 / Local ASR Setup` 可见。
   - ASR binary path、model path 和 audio converter path 旁边可见 `选择...` 按钮。
   - 可手动输入路径，或点击 `选择...` 打开系统原生 file picker 后填入对应路径；取消选择不应清空原路径。
   - 点击 `保存配置 / Save`，再点击 `重新检测 / Refresh Status`。
   - Local ASR status 变为 ready。
   - UI 只显示 safe basename：`whisper-cli`、`ggml-base.bin`、`ffmpeg`。
   - Debug Panel / Event Stream / Raw JSON 不显示完整路径。
3. Persistence after restart:
   - 关闭 packaged app 后重新打开。
   - Local ASR 配置仍存在，source 显示为用户配置。
   - Status 仍可 ready，`Check Local ASR` 仍可启动。
4. Local ASR operations:
   - `Check Local ASR` succeeded。
   - `Audio Capture Test` succeeded。
   - `Record & Transcribe` succeeded。
   - 主聊天框语音按钮可用，并使用 Local ASR，而不是 Web Speech unavailable fallback。
   - 真实 transcript 填入输入框，不自动发送。
   - 用户可编辑 transcript；只有用户手动点击发送后才进入 chat flow。
5. Simplified Chinese output:
   - 如果 whisper 输出繁体中文，ReiLink 应规范化为简体中文。
   - transcript 中英文和数字不应被破坏。
   - Event Stream / Debug Panel 不显示完整 transcript。
6. Privacy / safety checks:
   - 禁止显示 full ASR binary path、full model path、full converter path、full temp audio path。
   - 禁止显示 raw stdout、raw stderr、raw exception、full transcript、audio content、base64 audio。
   - 禁止显示 API key、`.env`、Authorization、raw prompt 或 long internal payload。
   - 允许显示 safe basename、configured boolean、source (`user_settings` / `env` / `none`)、transcript char count、language、conversion status、cleanup status、duration_ms 和 MIME summary。
7. Clear configuration fallback:
   - 点击 `清除配置 / Clear`。
   - Local ASR 回到 env fallback 或未配置。
   - 主聊天语音按钮显示安全 fallback，App 不崩溃。
   - Debug Panel / Event Stream 不泄露已清除的完整路径。
   - packaged app 退出后，由 app 自启动的 backend 没有残留监听进程。
8. Known limitations:
   - ReiLink 不内置 whisper binary、model 或 ffmpeg。
   - 真实识别准确率取决于模型大小、录音质量和硬件性能。
   - `base` 模型是速度 / 准确率折中；更大模型可能更准确但更慢。
   - packaged `.app` 若用户未配置路径，会显示安全 fallback。
   - native file picker 只填入 Settings 输入框，不读取模型内容、不复制文件、不上传文件；仍需点击 `保存配置 / Save` 才持久化。

- 当前 Web Speech Recognition 在 Electron packaged app 中可能暴露 API，但识别服务不可用；Local ASR ready 时主聊天语音按钮应走本地转写，Local ASR not ready 时才显示 `语音识别服务不可用` 或明确 unavailable fallback，不崩溃。
- v1 仍保留输入框入口、安全 fallback、系统听写提示和“不自动发送”的边界。
- 当前 Local ASR Config Detection v1 只检测解析后的配置，不执行 whisper / ASR binary，不录音，不转写，不上传音频，不下载模型，不把模型或用户数据写入 `.app`。
- Local ASR 配置来源优先级：Settings 中的用户配置优先，其次是 `REILINK_LOCAL_ASR_BINARY` / `REILINK_LOCAL_ASR_MODEL` / `REILINK_AUDIO_CONVERTER_BINARY` 环境变量 fallback，最后是未配置。
- Settings 的 `本地 ASR 配置 / Local ASR Setup` 可保存本地识别程序、模型文件和音频转换工具路径；路径可手动输入，也可通过原生 file picker 填入。保存位置为 backend `settings.data_dir/local_asr_settings.json`，不写入 repo、`.env` 或 packaged `.app`。
- Settings API `GET /api/voice-input/local-asr/settings` 只返回 configured booleans、source 和安全 basename；`PUT` 只保存路径字符串，不执行、不下载、不复制；`DELETE` 清除用户配置并回落到 env 或 none。
- 完整路径只允许出现在 Settings 编辑输入框、file picker 返回填入值和本地 settings JSON 文件中；Event Stream、Debug Panel、Raw JSON、chat 和文档示例不得出现真实用户名路径。
- Settings / Debug Panel 应显示 `本地语音识别 / Local ASR` 状态；状态包括未配置、缺少本地识别程序、识别程序不可执行、缺少本地语音模型、已就绪。
- 未配置：用户配置和 env fallback 都没有可用 binary/model，或只配置了识别程序但未配置模型；显示用户可读中文提示，Voice Input 仍回退到系统听写提示。
- 缺少本地识别程序：配置了 binary 但文件不存在；UI 只显示安全文件名，不显示完整路径。
- 识别程序不可执行：binary 文件存在但没有执行权限；UI 只显示中文状态和安全文件名，不显示完整路径。
- 缺少本地语音模型：binary 可执行但 model 文件不存在；UI 只显示安全模型名，不显示完整路径。
- 已就绪：binary 存在且可执行、model 存在；主聊天语音按钮会优先使用 Local ASR，但仍只在用户点击后录音和转写。
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
- 主聊天语音按钮 provider selection：Local ASR ready 优先使用 `local_asr`；Local ASR not ready 且 Web Speech 可用时回退 `web_speech`；两者都不可用时显示安全 unavailable fallback。
- Local ASR ready 时，主聊天语音按钮即使在 Web Speech service unavailable 的运行环境中也应可用，并显示 `本地语音识别可用`、`正在录音`、`正在本地转写` 或 `转写完成，请确认后发送`。
- Backend ASR Transcription Bridge v1 只在 Local ASR config status 为 `local_asr_ready` 时启用主聊天语音按钮的本地转写路径和 `录音并转写 / Record & Transcribe`。
- config not ready 时，转写按钮不可用；backend 返回 `local_asr_transcription_not_ready`，不运行 binary。
- config ready 时，用户点击主聊天语音按钮或 Settings 的 `Record & Transcribe` 后才请求麦克风权限，录制短音频并上传到本机 backend transcription endpoint。
- Backend transcription 写入系统临时目录 `reilink-local-asr-*`，必要时先做音频格式转换，再调用 configured local ASR binary，传入 model path 和可识别的 temp audio path，随后清理原始和转换后的临时音频。
- Backend 默认使用安全语言 `zh` 调用 whisper-like CLI；renderer 可传 `zh-CN`，backend 会归一为 `zh`，不安全或不支持的 language 不会进入 subprocess command。
- Local ASR transcript 在返回 renderer / 填入输入框前会 trim、折叠空白、去重复换行，并做轻量繁体到简体中文规范化；该规范化只作用于 ASR transcript，不改用户手打文本、assistant 回复、memory 或 knowledge pack。
- 简体规范化示例：`瑪爾基特怎麼打` -> `玛尔基特怎么打`，`我想問一下這個 Boss 怎麼處理` -> `我想问一下这个 Boss 怎么处理`；英文、数字和已是简体的文本应保持合理不变。
- WAV / PCM 输入不转换；browser 常见 `audio/webm` / `video/webm` / `audio/ogg` 等非 WAV 输入需要转换。
- 音频转换工具由用户通过 Settings 或 `REILINK_AUDIO_CONVERTER_BINARY` fallback 配置；当前项目不内置、不下载、不提交 ffmpeg 或第三方二进制。
- 默认 converter command 使用 subprocess list args：`[converter, "-y", "-i", input_path, "-ar", "16000", "-ac", "1", output_wav_path]`；不使用 `shell=True`。
- 未配置或不可用 converter 时，WebM/Ogg 转写返回 `audio_conversion_not_configured` 安全摘要，不调用 local ASR binary。
- converter 失败或超时时返回 `audio_conversion_failed` / `audio_conversion_timed_out`，不显示 raw stdout / stderr / exception / 完整 converter path。
- converter 成功时，response / UI 显示 `audio_conversion_succeeded`、source MIME、`converted_mime_type=audio/wav`、safe converter name 和原始/转换临时文件清理状态。
- 默认 ASR command 使用 subprocess list args：`[binary, "-m", model_path, "-f", audio_path, "-nt", "-l", "zh"]`；不使用 `shell=True`。
- Transcription timeout 为 30 秒；timeout 时返回 `local_asr_transcription_timed_out` 和 `本地语音识别超时，可以尝试更小模型或更短录音`。
- Audio conversion timeout 为 10 秒；timeout 时不继续调用 local ASR。
- fake binary smoke：通过 Settings 或 env fallback 配置 fake binary / fake model，fake binary 输出固定 transcript，确认输入框被回填。
- Settings 显示安全 model basename。`ggml-base.bin` 通常速度和准确率较均衡；tiny 更快但更不准，small / medium / large 可能更准但更慢或超时。ReiLink 不内置模型。
- 真实准确率排查建议：尽量说短句、靠近麦克风、降低背景噪声；需要更高准确率时可尝试更大模型，但要接受更慢或超时风险。
- 正常 transcript 只填入聊天输入框，用户可编辑或删除；不会自动发送，UI 应显示 `转写完成，请确认后发送`。
- 未确认 transcript 不写 memory，不进入 prompt / retrieval / game context，也不触发 semantic/game extraction。
- 主聊天语音按钮的 transcript 同样只填入输入框；用户手动点击发送后才进入 chat flow。
- 空 transcript 返回 `local_asr_transcription_no_text`，UI 显示 `没有识别到可用文本`，不改输入框。
- fake binary nonzero 返回 `local_asr_transcription_failed`，不显示 raw stdout / stderr。
- subprocess OS error 返回 `local_asr_transcription_error`，不显示 raw exception。
- cleanup succeeded 时 response / UI 显示临时音频已清理。
- cleanup failed 时返回 `local_asr_transcription_cleanup_failed`，不显示 temp path、raw exception 或 transcript。
- Event Stream 只显示 `本地语音识别开始`、`本地语音识别完成`、`本地语音识别失败`、字数、language、是否 `已规范为简体中文`、duration、size、MIME、conversion status、target MIME、cleanup、安全 model / binary basename 和安全 status。
- Event Stream、Debug Panel、Raw JSON 不显示完整 transcript、raw stdout、raw stderr、完整 binary/model/temp path、audio content、base64、API key、`.env`、Authorization 或 raw prompt。
- packaged `.app` smoke 需要确认未配置时 Local Transcribe disabled；可选 fake binary / fake model smoke 确认 packaged app 仍不泄露 transcript 或路径。
- Packaged `.app` 应包含麦克风用途说明：`ReiLink 需要麦克风权限用于用户主动触发的语音输入测试。`
- Local ASR QA 后续重点是：主聊天按钮 provider selection、转写中状态、错误中文映射、临时音频清理、packaged `.app` fallback 和 Event Stream 隐私。
- 用户临时替代方案：使用系统听写直接输入到聊天框。
- 默认不上传外部服务，不保存音频，不自动发送 transcript。
- 未确认 transcript 不进入 memory、prompt、knowledge retrieval 或 game context。
- 当前配置检测不会产生音频或 transcript。Event Stream / Debug / Raw JSON 不显示完整 transcript、完整音频路径、raw subprocess output、API key、`.env`、Authorization、完整本地路径或 raw prompt。

#### Real Local ASR optional smoke / 真实本地 ASR 可选冒烟

本冒烟只用于开发者或用户本机手动验证真实 whisper.cpp / model / converter 链路，不是自动测试依赖，也不代表 ReiLink 内置模型、ASR binary 或 converter binary。详细配置步骤见 `docs/local-asr-manual-setup.md`。

- 用户自行准备本地 whisper.cpp-compatible binary、model 文件和可选 converter；不要下载或提交到 repo。
- 优先在 Settings -> Voice Input -> `本地 ASR 配置 / Local ASR Setup` 输入，或通过 `选择...` 按钮选择并保存本地 binary / model / converter 路径；env fallback 仍可用于开发或启动脚本。
- Settings -> Voice Input 中 config detection 应显示 ready；缺少文件或不可执行时只显示安全摘要。
- `Check Local ASR` 应返回 succeeded；失败或超时只显示中文安全状态。
- `Audio Capture Test` 应录音成功，显示 duration、size、MIME，并清理临时音频。
- audio conversion 应显示 `audio_conversion_succeeded`，或在 WAV / PCM 输入时显示 conversion not needed。
- `Record & Transcribe` 应返回已 trim / 折叠空白 / 简体规范化后的 transcript，并只填入输入框。
- 主聊天语音按钮应显示本地 ASR 可用；点击后录音、转写，并把 transcript 只填入主聊天输入框。
- transcript 不自动发送；用户检查后才手动点击发送。
- 未发送前不得写入 memory / prompt / knowledge retrieval / game context。
- Event Stream / Debug Panel 不显示完整 transcript、完整路径、raw stdout、raw stderr、API key、`.env` 或 Authorization。
- packaged `.app` optional smoke 需要确认非黑屏、backend health ok、Voice Input / Local ASR Setup 入口可见、Settings 保存后重启仍持久化，退出后没有 backend 残留。

#### Local ASR real compatibility QA

本矩阵用于真实 whisper.cpp 兼容性准备，不要求把 whisper binary、模型文件、ffmpeg 或任何第三方二进制提交进仓库。当前 bridge 仍假设 whisper.cpp-like CLI：`-m <model>`、`-f <audio>`、`-nt` 和 `-l zh`；真实兼容性必须在用户本机手动验证。

5.1 未配置：

- 清空 Settings 中的 Local ASR 用户配置，并清空 `REILINK_LOCAL_ASR_BINARY` / `REILINK_LOCAL_ASR_MODEL` env fallback。
- Settings 显示 Local ASR not configured / 本地语音识别未配置。
- `录音并转写 / Record & Transcribe` disabled，backend 不启动 binary。

5.2 fake binary：

- 使用临时 fake executable 和临时 fake model file，不提交到 repo。
- fake binary 可分别输出纯文本、timestamp 文本、带日志文本、空文本和超长文本。
- 期望 config ready，probe succeeded，transcribe 返回已清洗 / 简体规范化的 fake transcript 或 no_text。
- transcript 只填入输入框，不自动发送。
- Event Stream / Debug / Raw JSON 不显示 full transcript、raw stdout/stderr、完整 binary/model/temp path。

5.3 real whisper binary + model：

- 用户本地自行准备真实 whisper.cpp binary 和 model，推荐模型目录：`~/Library/Application Support/ReiLink/models`。
- 通过 Settings 保存真实 whisper.cpp binary 和 model 路径，或设置 `REILINK_LOCAL_ASR_BINARY` 和 `REILINK_LOCAL_ASR_MODEL` env fallback。
- 打开 dev app，运行 `Check Local ASR`，确认只显示安全文件名。
- 运行 `Audio Capture Test`，记录安全 MIME summary，例如 `audio/webm`、`audio/wav` 或 `unknown`。
- 运行 `Record & Transcribe`，检查 transcript 是否以简体规范化结果进入输入框且不会自动发送。
- 运行主聊天语音按钮，确认 Web Speech 不可用时仍走 Local ASR，状态不是 `语音识别服务不可用`。
- 检查 Event Stream 不显示完整 transcript。
- 如果录音格式是 `audio/webm` / Ogg，检查未配置 converter 时是否显示 `尚未配置音频转换工具`；通过 Settings 或 `REILINK_AUDIO_CONVERTER_BINARY` fallback 配置 converter 后再验证转换状态、target MIME 和清理状态。
- 如果真实转写不准，先尝试更短录音、更近麦克风、更低噪声；再考虑从 tiny/base 调整到更大模型，同时观察是否触发 30 秒 timeout。

5.4 packaged app：

- 未配置时安全 fallback，Local Transcribe disabled 或显示配置未就绪。
- fake binary optional；real whisper optional manual。
- 不显示完整路径、raw stdout / stderr、`.env`、API key 或 Authorization。
- `Audio Capture Test`、`Record & Transcribe`、主聊天语音按钮、`Test Voice` 和 Knowledge Retrieval 入口仍可见。
- 退出后 backend 无残留。

### 5. Overlay v1.1 回归检查

机器可读场景见 `docs/qa/overlay_scenarios.json`。

- `Overlay / 游戏悬浮层` 默认关闭。
- Settings 中可用普通按钮切换 Overlay 开启 / 关闭，并可设置位置预设、背景透明度和显示消息数量；关闭 app 再打开后仍保持上次设置。
- Settings 中应存在可靠关闭入口：`强制关闭悬浮层` 点击后应立即把 overlay_enabled 设为关闭并隐藏 / 销毁 overlay window。
- Overlay 位置预设只使用右上、右中、右下、左上、左中、左下；默认 `右中`，移动时应保持在 primary display workArea 内。
- Overlay 背景透明度范围为 0.35～0.95，默认 0.72；调整后只影响浮层背景，文字仍应清晰可读。
- Overlay 显示消息数量只能是 1～3，默认 2。
- ReiLink 主窗口前台点击开启时只保存 enabled 状态，不应立即出现盖在 Settings 上方的 overlay window；macOS 当前采用 emergency fail-closed 策略，切换到其他 app 后也可以继续保持隐藏，优先保证 ReiLink 不抢焦点、不闪烁。
- Overlay window 应是透明、无边框、always-on-top，并保持小窗口 bounds，不应是主窗口大小或整屏大小；非 macOS 可使用 `skipTaskbar`，macOS 不应让 overlay window 隐藏整个 ReiLink Dock / `⌘ + Tab` 入口。
- Overlay renderer 应只显示 overlay bubble / placeholder；不得渲染完整 ReiLink sidebar、聊天主界面、Settings、Debug Panel、输入框或完整 App layout。
- Overlay 整体是半透明短消息层，不应像普通桌面通知窗口。
- Overlay 不抢主窗口焦点；开启、更新内容和关闭时主聊天输入仍可继续使用。
- ReiLink 主窗口或 Settings 位于前台时，Overlay 即使已开启也应隐藏或销毁，不遮挡 Settings、select/dropdown、slider、button 或 macOS 关闭 / 最小化 / 全屏按钮。
- 非 macOS 切换到其他 app 或游戏窗口后，如果 `overlay_enabled=true`，Overlay 可以重新显示；macOS 当前允许 fail-closed，不自动显示 overlay，以避免 app activation / focus loop。切回 ReiLink 主窗口后 overlay 应保持隐藏。
- Overlay 不接收输入，不显示输入框、按钮、debug 面板、Raw JSON、memory 或 prompt。
- 没有消息时显示克制 placeholder，例如 `Rei 正安静待机。`。
- assistant 最终回复完成后，Overlay 只显示截断后的 Rei 短摘要；不要显示完整 assistant reply。
- proactive short hint 可作为 Rei 短消息显示；不影响主窗口聊天流程。
- Overlay 最多显示最近 1～3 条安全短消息，每条消息应保留 `Rei` 小标识或等价头像占位。
- 关闭 Overlay 后悬浮窗消失，主窗口聊天和 Voice Output / Voice Input / Knowledge Retrieval 不受影响。
- Event Stream 可显示 `悬浮层开关变化`、`悬浮层设置变化`、`悬浮层位置更新`、`悬浮层显示`、`悬浮层隐藏`、`悬浮层暂时隐藏`、`悬浮层内容更新` 或等价中文安全摘要。
- Event Stream 只显示来源、消息数量、字符数、窗口状态、位置预设和透明度数值，不显示完整 assistant reply、完整用户输入、memory、raw prompt、API key、`.env`、Authorization、完整路径、完整 transcript、raw stdout 或 raw stderr。
- Debug Raw JSON 的 settings 可显示 overlay 开关、位置、透明度和消息数量，不显示 overlay 消息文本。
- Dev smoke 至少覆盖：启动不黑屏、Settings 中 Overlay 配置可见、默认关闭、前台开启不覆盖 Settings、位置切换生效、透明度变化可读、消息数量限制生效、不抢焦点、不接收输入、发送消息后只更新短摘要、关闭 / 强制关闭后隐藏、Event Stream 安全事件可见；非 macOS 可额外验证切走后小型 overlay bubble 出现。
- Packaged `.app` smoke 如本次未执行，需要在 release 前补做：直接打开 packaged app，确认 app 出现在 Dock / `⌘ + Tab`，窗口模式和全屏模式都不闪烁、不始终置顶、不自动抢回焦点，并验证 Settings 开启 / 关闭 / 强制关闭 / 位置 / 透明度。
- 本阶段不实现 HUD / 敌人 / 玩家位置识别，不做画面理解，不做自动避让，不做拖拽或锁定位置。

#### Overlay v1.1 Regression Freeze / Safe Mode

当前稳定状态：

- Overlay 默认关闭。
- Settings 可开启 / 关闭 Overlay，且位置、透明度、显示消息数设置可保存。
- `强制关闭悬浮层` 可用，用于异常时立即关闭并保存 `overlay_enabled=off`。
- ReiLink 主窗口或 Settings 前台时 Overlay 不显示，优先保证 Settings 和窗口按钮可操作。
- macOS 下 overlay auto-show 当前 fail-closed：开启后切到其他 app 也不会自动显示小气泡，这是当前预期。
- 主窗口稳定性优先于 Overlay 显示；如两者冲突，继续保持 Overlay fail-closed。

以下问题必须回归防止复发：

- Overlay 不能渲染完整 ReiLink App，只能渲染 OverlayApp / bubble surface。
- Overlay 不能遮挡 Settings、select/dropdown、slider、button。
- Overlay 不能遮挡 macOS traffic lights。
- Overlay 不能导致 Settings 无法关闭 Overlay。
- Overlay 不能导致 ReiLink 从 Dock 或 `⌘ + Tab` 消失。
- Overlay 不能导致主窗口疯狂闪烁。
- Overlay 不能导致 ReiLink 始终置顶。
- Overlay 不能导致切到其他 app 后自动抢回焦点。
- Overlay 不能破坏主窗口关闭 / 最小化 / 全屏按钮。
- Overlay content / Event Stream 不能泄露 raw prompt、API key、`.env`、完整路径、完整 transcript、stdout/stderr 或 raw JSON。

后续恢复 macOS auto-show 前必须满足：

- 不调用 `mainWindow.focus()` 抢焦点。
- 不让 overlay window 触发 app activation loop。
- 不使用会隐藏整个 ReiLink app 的 macOS `skipTaskbar` 策略。
- Overlay route 必须稳定只渲染 OverlayApp，不渲染完整 App。
- 主窗口前台时 overlay 必须隐藏或销毁。
- 用户必须始终能从 Settings 关闭 Overlay，并能使用 `强制关闭悬浮层` 兜底。
- Dock / `⌘ + Tab` 必须保持 ReiLink 可见。
- packaged `.app` 必须人工验证窗口模式和全屏模式。

packaged `.app` 手动 smoke 最低步骤：

1. 打开 packaged ReiLink。
2. 确认窗口不闪烁。
3. 确认 ReiLink 不始终置顶。
4. 确认 Dock 可见。
5. 确认 `⌘ + Tab` 可见。
6. 切到 Finder / 浏览器。
7. 切到其他 app 后确认 ReiLink 不抢回焦点。
8. 切回 ReiLink。
9. 在 Settings 开启 / 关闭 Overlay。
10. 点击 `强制关闭悬浮层`。
11. 确认 Overlay 不遮挡 Settings。
12. 确认 Overlay 不导致 ReiLink 左上角窗口按钮消失。
13. 确认 macOS 下 auto-show 暂时不出现小气泡，这是当前预期。

### 5.5 Game Session Timeline / 本局时间线回归检查

机器可读场景见 `docs/qa/session_timeline_scenarios.json`。

- Debug Panel 中应出现 `Session Timeline / 本局时间线` 折叠区。
- 默认折叠；展开后如本局尚无关键变化，应显示 `本局还没有记录到关键变化。`。
- Timeline 只保存在当前 renderer session 内，不写入 `.app`，不替代 Event Stream、memory 或聊天记录。
- Timeline 可记录安全摘要：切换游戏、检测到 Boss、死亡次数变化、挫败状态变化、击败 Boss、使用知识、主动陪伴已显示、记忆已接受、记忆已忽略。
- Game Context 变化应显示类似 `切换游戏：Elden Ring` 的短摘要。
- Game Session 变化应显示类似 `检测到 Boss：Margit`、`死亡次数更新：3`、`挫败状态升高：2`、`击败 Boss：Margit`。
- 死亡次数必须区分绝对值和增量：`已经死了3次`、`我现在死了4次`、`目前死了5次` 应设置为对应数字；`又死了两次` 应在当前次数上增加 2；`死麻了`、`一直死`、`打不过` 不应乱写具体 death count。
- `我有点冷静下来了` 或等价表达应让 Game Session 挫败状态缓和，并在 Timeline 显示 `挫败状态缓和` 或等价安全摘要。
- 显式游戏切换必须覆盖 `我换到空洞骑士了`、`我现在玩空洞骑士`、`今天打空洞骑士`、`我回法环了`、`我现在在艾尔登法环`；后续 Boss / Knowledge Retrieval 应跟随新的 current game。
- Boss alias 回归必须覆盖 `恶兆妖鬼玛尔基特 / 玛尔基特 / Margit` 和 Hollow Knight 的 `假骑士 / False Knight`。
- 被动死亡表达必须记录为失败尝试而不是击败：`我在大树守卫，被杀了4次，有点烦`、`我被大树守卫杀了4次`、`被玛尔基特杀了3次`、`被假骑士打死两次` 应更新 Boss、death count 与 failed activity，不应出现 boss_cleared。
- Semantic Extraction Debug 应显示安全 trace：`source`、`confidence`、`fallback_reason`、`skip_reason`、`applied_updates`，以及 `llm_shadow_status`、`llm_shadow_summary`、`llm_shadow_diff`。被动死亡 / near-clear / 指代不明 / 中文游戏失败 slang 等容易误判表达应能看到安全原因；provider 不可用、Shadow Mode 失败、invalid JSON 或 no meaningful update 时也应显示安全 skip / parse reason，不应 silent no-op。
- 语义识别置信度验收：高置信规则可以直接应用；被动死亡、near-clear、未知 Boss 指代、低置信失败表达等歧义风险表达应降低调度置信度以允许 LLM Shadow Mode 产出候选；最终显示的 confidence 只用 high / medium / low，不展示 raw prompt、raw JSON 或完整用户输入。
- LLM Shadow Mode 只用于可观测性：LLM 影子候选可以显示候选 game / boss / death_count / frustration / boss_cleared / memory / proactive signal 与规则差异，但不能直接修改当前游戏状态、memory 或 proactive 调度。
- 低置信语义触发词只能作为 trace / Shadow Mode 线索，不应为了测试把 slang 或模糊别名硬编码成最终 Boss、death count 或 boss_cleared；v2 状态更新只来自规则路径，影子候选即使成功也只显示候选和差异。
- Shadow Mode 真实 provider 回归必须确认复用主 backend provider config，优先使用 fast / lightweight model，并在 API chat 中后台补 Debug 诊断，不拖慢主回复路径；如果主聊天 provider 可用，Shadow 不应误报 `provider_unavailable`。
- Shadow Mode 真实 provider JSON 稳定性回归必须确认：请求使用紧凑 JSON-only contract，不要求模型输出解释；解析器可安全恢复严格 JSON、Markdown code fence、前后夹杂简短说明的首个 JSON object，以及数组中的首个 object；无法恢复时显示 `shadow_invalid_json` 安全终态。
- Shadow Mode provider 兼容性回归必须覆盖：首次 `response_format: json_object` 返回 invalid JSON 时，后台 Shadow 可做一次无 `response_format` 的兼容 retry；compat retry 仍 invalid JSON 时，可再做一次 ultra-compact flat JSON fallback。ultra 成功显示 `shadow_succeeded / 模式 ultra_compact`，ultra 仍失败显示 `shadow_invalid_json` 与 attempts 诊断。timeout、auth_failed、provider_unavailable、provider_error 不应 retry。
- Shadow Mode final event 安全诊断必须覆盖：`response_format_used`、`compat_retry_used`、`ultra_compact_used`、`attempts`、`last_failure`、`json_recovery_stage`、`finish_reason`、`content_length_bucket`、`first_char_type`；这些字段不得包含 raw provider response、raw prompt、完整用户输入、路径、API key、`.env`、stdout/stderr。
- 如果 ultra-compact fallback 在真实 provider 下仍不稳定，但终态、attempts 和安全诊断清楚，主聊天不受影响，Shadow 不污染状态，则记录为 known limitation：`真实 provider 下 LLM Shadow candidate 成功率仍不稳定；当前阶段保留 Shadow diagnostics，不继续阻塞后续 Persona Pack。`
- Shadow Mode 后台任务回流必须覆盖：Event Stream 可先显示 `shadow_deferred` / 已调度，但 15～25 秒内应追加安全终态事件，例如 `shadow_succeeded`、`shadow_timeout`、`shadow_invalid_json`、`shadow_auth_failed`、`shadow_provider_unavailable`、`shadow_provider_error`、`shadow_cancelled` 或 `shadow_expired`；不得永久停留在“后台等待”。
- Shadow Mode 回归必须覆盖 provider unavailable、auth_failed、invalid JSON、timeout / provider error：这些场景都要安全降级，不显示 raw provider response、raw prompt、完整路径、API key、`.env`、stdout/stderr 或完整用户输入。
- Semantic Shadow QA Freeze 人工验收 A / Basic shadow trace：输入 `我在那个骑马金甲大哥那里又寄了几次。` 后，主聊天应正常回复；Event Stream 可先显示 `shadow_deferred`，但 15～25 秒内必须出现 `shadow_succeeded`、`shadow_timeout`、`shadow_invalid_json`、`shadow_provider_error`、`shadow_auth_failed`、`shadow_provider_unavailable`、`shadow_cancelled` 或 `shadow_expired` 之一，不得永久停在后台等待。
- Semantic Shadow QA Freeze 人工验收 B / Hollow Knight fuzzy reference：输入 `空洞骑士里那个一开始拿锤子的家伙把我打爆了。` 后应产生 shadow final event；成功时显示安全 candidate summary，失败时显示明确 failure reason 和 attempts 诊断。
- Semantic Shadow QA Freeze 人工验收 C / Slang failure：输入 `这树守卫给我薄纱了四回，真的烦。` 后应产生 rule / shadow trace；Shadow 可以显示候选理解或失败诊断，但不应直接写状态。
- Semantic Shadow QA Freeze 人工验收 D / Safety：Shadow Event Stream 不得显示完整用户输入、raw prompt、raw LLM JSON、API key、`.env`、完整本地路径、stdout/stderr 或 ASR transcript。
- Semantic Shadow QA Freeze 人工验收 E / Non-application boundary：无论 Shadow 成功还是失败，都不能直接改 Game Context、创建 pending memory、触发 proactive 或写长期记忆；如果规则路径独立命中，应在 trace 中能区分 applied_updates 来源。
- Semantic Shadow QA Freeze 人工验收 F / Diagnostics：Shadow final event 可显示 `response_format_used`、`compat_retry_used`、`ultra_compact_used`、`attempts`、`last_failure`、`json_recovery_stage`、`finish_reason`、`content_length_bucket`、`first_char_type` 等短标签诊断，但不得显示 raw response。
- 已击败 Boss 后继续问打法时，纯攻略 / 位置 / build 提问不应把已 cleared Boss 重新写成 current boss。Rei 可以轻轻承接“已经打过”的上下文，但不能只用反问阻断；仍应回答用户实际攻略 / 复盘需求。
- 显式记忆回归：`记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打` 应创建 pending memory；`以后不用记住这个，只是我这次随便说一下` 不应创建 pending memory。
- Knowledge Retrieval 使用成功时应显示 `使用知识` 类摘要，只允许游戏名或安全 topic/title；不得显示完整 snippet、knowledge 文件路径或 prompt。
- Proactive 显示时应记录 `主动陪伴已显示` 和安全 trigger 标签，不显示完整 proactive / assistant 文本。
- 主动陪伴场景区分验收：
  - 明确烦躁、红温、破防或 frustration count 升高时，优先归为挫败场景，文案应是短疑问句，如 `你还好吗？`。
  - 单纯 death count 增长且没有明确挫败信号时，归为反复死亡场景，文案应是短疑问句，如 `没关系吧？`。
  - 没有状态性信号但长时间无回复时，才归为沉默陪伴，文案应是低打扰短疑问句，如 `还在吗？`。
  - 主动陪伴应在最近 Rei 正常回复后一段时间才触发，不应紧跟普通 assistant reply 插话。
  - 重置记忆、清空 pending memory、重置 game session、Settings / Local ASR 保存或刷新、Debug reset 后应短暂抑制 proactive，并同步已观察到的 death / frustration 状态。
  - 用户表达冷静或 Game Session 进入 `frustration_calm` 后，不应继续用旧死亡 / 旧挫败状态触发 repeated_death 或 frustration_loop。
  - 非沉默类型触发后不能连续触发同一类型；如果后续场景变成另一类，可以由另一类接管。沉默陪伴允许在冷却后重复，但仍受 idle threshold 和 cooldown 控制。
- Pending Memory 接受或忽略时应记录 `记忆已接受` / `记忆已忽略`，不显示 memory 原文、evidence 或 raw payload。
- `清空时间线` 应只清空当前 timeline，不清空 Event Stream、聊天、memory、game session 或 Local ASR 设置。
- Timeline 最多保留最近有限条目，长摘要应截断。
- Timeline 不显示 raw prompt、完整 user message、完整 assistant reply、完整 ASR transcript、memory 原文全文、knowledge snippet 全文、API key、`.env`、完整本地路径、raw stdout/stderr 或 raw JSON。
- Voice Output、Local ASR、Overlay safe mode 和 Event Stream 原有行为不应受影响。

### 6. Knowledge Retrieval 回归检查

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

### 7. Debug / Event Stream 隐私检查

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

### 8. Packaged `.app` Release Smoke Checklist

- 如果 backend 代码、schema、knowledge loading 或 runtime 发生变化，重新运行 `make package-backend`。
- 重新运行 `make package-desktop`。
- 直接打开 packaged `ReiLink.app`，不是 dev renderer。
- UI 非黑屏。
- backend 自启动，或复用健康外部 backend。
- bundled knowledge resources 可用。
- `语音输出 / Voice Output` 和 `测试语音 / Test Voice` 可见。
- `语音输入 / Voice Input` 和主语音按钮可见。
- Voice Input supported / unsupported / permission fallback 可读，不崩溃。
- Knowledge Retrieval 可用。
- Event Stream 不泄露敏感内容。
- memory / session 写入用户数据目录，不写入 `.app`。
- `.env` 不复制进 `.app`。
- app 退出后，自启动 backend 无残留。

### 9. Release 前 Runtime Sanity

- `make lint`
- `make test-desktop`
- `make typecheck`
- `git diff --check`
- `make test-backend`
- `make validate-knowledge`
- 如果 e2e 已存在：`cd apps/desktop && npm run test:e2e`
- 如果 runtime / packaging / backend binary / knowledge loading 变更：`make package-backend && make package-desktop`
- packaged `.app` smoke 至少覆盖：非黑屏、backend health ok、bundled knowledge、Voice Output controls、Event Stream privacy。

### 10. Known Limitations

- `below_threshold` 依赖当前知识包内容和评分阈值，手动测试时可优先用机器可读场景文件里的弱相关示例。
- `no_pack` 依赖 catalog 中仍有 planned / unsupported 游戏；当前可用 `只狼` 做手动场景。
- Voice Input v1 保留 Web Speech fallback；Local ASR ready 时主聊天语音按钮优先走本地转写。不接商业 ASR，不上传外部服务，不保存音频。
- 如果 Electron runtime 不支持 Web Speech Recognition，当前预期是 Local ASR ready 时主按钮仍可用；Local ASR not ready 时显示明确 unavailable fallback，用户可临时使用系统听写输入到聊天框。真实 whisper.cpp / model / converter 兼容性仍属后续手动 QA。
- Voice Output 的真实播放取决于系统语音包和浏览器 speech synthesis 支持；失败必须被 UI 允许并可见，不应被视为崩溃。
- Manual QA 不替代 automated tests；它用于 release 前的人眼回归与打包行为确认。

## English

This QA Pack is a reusable manual regression checklist for ReiLink before future Voice / Local ASR expansion, Live2D, Overlay, and embedding RAG work. It focuses on the current foundations: local runtime, Voice Output, Voice Input fallback, Local ASR staged foundation, Knowledge Retrieval, Event Stream, Debug privacy, and packaged app smoke testing.

Machine-readable scenarios live at:

- `docs/qa/retrieval_scenarios.json`
- `docs/qa/voice_input_scenarios.json`
- `docs/qa/voice_input_local_asr_scenarios.json`
- `docs/qa/persona_pack_scenarios.json`

Real Local ASR manual setup and optional smoke guidance lives at `docs/local-asr-manual-setup.md`.

Use the Chinese checklist above as the source of truth for manual runs. Keep results short and concrete: pass/fail, exact app mode, exact commit, and any visible privacy issue.
