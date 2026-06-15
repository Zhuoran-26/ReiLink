# Project Status

## 中文

Updated: 2026-06-16

### 当前阶段

当前阶段：`v0.2-pre productization / 产品化补齐预发布阶段`。

`reilink-mvp-v0.1.1` 已经作为公开展示版本发布，用于 GitHub / portfolio / interview 展示。`reilink-v0.2-pre` 已作为预发布版本公开，当前 `dev/codex-reilink` 已进一步补齐 standalone runtime / productization foundation，并阶段性完成 Voice Interaction MVP：可选系统 TTS、本地 ASR 主聊天输入、transcript-first 用户确认发送、Local ASR Settings 持久化和 release regression freeze。当前已完成 Overlay v1 Foundation，并进入 Voice / Local ASR / Overlay Safe Mode regression freeze 阶段。

截至本次阶段冻结，Voice Output v1 / v1.1、Local ASR v1、Local ASR Native File Picker v1 和 Overlay v1.1 macOS safe mode 已作为当前稳定回归基线记录。macOS Overlay auto-show 仍故意 fail-closed，后续恢复必须单独立项并通过 packaged `.app` QA checklist。

v0.2-pre 的重点不是新增核心玩法或扩大业务范围，而是让首次启动、开发启动、公开展示、standalone runtime、本地数据目录、多游戏知识维护和 release readiness 更清晰、更稳定。

产品方向：

- 中文优先的单机游戏 AI companion。
- LLM-first 回复生成。
- 游戏上下文、记忆和知识层提供辅助信息。
- 当前 sample companion 是 ReiLink 原创 Rei-like persona，不使用官方 IP；v1.1.2 已开始使用中文优先的结构化 Persona Pack 校准冷静寡言陪伴风格。

### 当前分支

```text
dev/codex-reilink
```

### 稳定基线说明

`PROJECT_STATUS.md` 不维护实时 latest commit hash。需要确认最新提交、稳定基线或发布点时，以 `git log --oneline`、release tag 和当前 git history 为准。

本文件只记录阶段性状态：MVP v0.1.1 已作为公开展示版本发布；v0.2-pre 已公开为 pre-release；当前开发继续在 `dev/codex-reilink` 上补齐 runtime / product foundation。精确状态以 git log / tag 为准。

### 已完成主要能力

- FastAPI backend 与 Electron / React desktop shell。
- DeepSeek-compatible provider。
- Model routing：`fast` / `pro` / `auto`。
- Minimal default persona，guarded 作为 fallback。
- Multi-part replies。
- Settings Panel。
- Game Session State。
- Semantic Extraction，包含 rule-first、LLM Shadow Mode 与安全 trace 可观察性。
- Pending Memory confirmation。
- Proactive Companion，包含 cooldown、系统操作抑制、最近回复冷却、场景优先级与同类触发去重。
- Local Game Detector。
- Manual Game Context Control。
- Unsupported Game fallback。
- Game Catalog / Multi-game Knowledge Interface。
- Knowledge Pack Manifest v1。
- Knowledge Retrieval：本地 keyword retrieval、grounding / gating、闲聊隔离、显式游戏名切换。
- Elden Ring sample knowledge pack。
- Hollow Knight sample knowledge pack。
- Voice Output：`语音输出 / Voice Output`、Test Voice、rate / volume、中文语音优先和 Event Stream 安全摘要。
- Voice Input v1 fallback：push-to-talk Web Speech UI、安全 fallback、不自动发送。
- Main chat Local ASR voice input：Local ASR ready 时主聊天语音按钮优先走本地录音/转写，Web Speech 作为 fallback。
- Voice Interaction MVP：系统 TTS + 用户配置 Local ASR + transcript-first UX + 隐私安全事件摘要。
- Overlay v1.1：默认关闭的独立透明悬浮层、Settings 开关、位置预设、背景透明度、1～3 条安全短消息气泡和 overlay lifecycle Event Stream。
- Game Session Timeline / Session Notes v1：Debug Panel 中的当前本局安全摘要时间线。
- Event Bus / Event Stream。
- Prompt Preview。
- Rei Persona Pack v1.1.2：中文优先的结构化原创 persona 文件、冷静寡言风格校准、真人感与关系类表层重复回归修正、safe loader、prompt assembly 接入和 Debug Prompt Preview 安全摘要。
- Debug Dashboard。
- UI/UX Information Architecture v0：规划 Home / Chat、Memory、Game、Voice、Overlay、Settings、Developer / Debug 和 Future Presentation / Avatar 的未来产品表面。
- UI Surface v0：左侧 workspace launcher、默认 Home / Chat、右侧 workspace panel、Memory / Game / Voice / Overlay / Settings / Developer Debug / Future Avatar 分层入口、panel tabs、关闭按钮和 Escape 关闭。
- QA / Regression scenarios。
- UI polish。

### v0.2-pre 新增 / 补齐能力

- First Run / Provider Setup。
- Dev Startup / Health Check。
- Public Readiness。
- Public screenshots and showcase assets。
- Local Game Detector。
- Manual Game Context Control。
- Unsupported Game fallback。
- Knowledge Pack Manifest。
- Knowledge Pack Validation Tool。
- Knowledge Pack Authoring Guide。
- Backend bundle spike。
- Standalone App Packaging v1。
- Bundled backend binary。
- Bundled knowledge resources。
- Bundled runtime resources：legacy persona、structured `personas/rei` pack、persona style 和 game registry 等只读资源随 packaged app 分发。
- Backend runtime priority：external backend、configured binary、bundled binary、repo fallback。
- User data dir：packaged app 使用 `~/Library/Application Support/ReiLink/data`。
- Local Data Controls：Settings 中查看 / 打开本地数据目录，并复用 Demo Reset / reset controls。
- Audio Capture / Temp File probe。
- Local ASR staged foundation and main chat integration：feasibility plan、config detection、CLI probe、Backend ASR Transcription Bridge、Audio Format Conversion bridge、whisper-like output parsing hardening、manual setup guide、主聊天语音按钮 provider selection。
- Local ASR Settings persistence / Setup UI：Settings 中保存、清除、刷新本地 ASR binary / model / converter 路径，提供原生文件选择按钮，保存到用户数据目录并 fallback 到 env。

### 当前 Voice / Local ASR 状态

- Voice Output v1 / v1.1 已稳定：默认关闭，Test Voice、rate / volume 和系统中文语音优先可用；Event Stream 只记录播放生命周期安全摘要。
- Local ASR v1 已稳定：使用用户本地 whisper-like binary、model 和 ffmpeg / converter；ReiLink 不内置 whisper binary、model 或 ffmpeg，不接云 ASR，不上传音频。
- Local ASR transcript-first 边界保持稳定：识别结果只填入输入框，不自动发送；用户确认点击发送后才进入 chat flow；未确认 transcript 不进入 memory、prompt、knowledge retrieval 或 game context。
- Local ASR Settings 支持路径持久化；Settings 输入框显示完整本地路径是正常编辑行为，但 Event Stream / Debug / Raw JSON 不显示完整路径。
- Local ASR Native File Picker v1 已加入：用户可为 binary、model、converter 点击 `选择...` 打开系统原生文件选择器；file picker 只填入路径，不读取、不复制、不上传文件，仍需用户点击保存配置。

- Voice Output 已完成并可用：支持 Test Voice、rate / volume、中文语音优先，`tts_started` 只在真实 `utterance.onstart` 后触发，`tts_completed` / `tts_error` 映射到安全中文摘要。
- Voice Output 当前使用系统 `speechSynthesis`，不是角色级配音；“Rei”等名字和语气可能不自然，后续可研究本地角色 TTS 或更自然的 voice provider，但当前不接商业 TTS。
- Voice Input v1 已完成 push-to-talk fallback：Web Speech transcript 只填入输入框，不自动发送；未确认 transcript 不进入 memory、prompt、knowledge retrieval 或 game context。
- Electron packaged 环境中的 Web Speech Recognition 服务不可靠，当前不作为稳定主路径；Local ASR ready 时主聊天语音按钮优先使用本地 ASR。
- Local ASR 已接入主聊天语音按钮：provider selection 为 `local_asr` -> `web_speech` -> `unavailable`；本地转写成功后 transcript 只填入输入框，仍需手动发送。
- Local ASR v1.1 已补齐输出规范化和 UX polish：`zh-CN` 归一为 whisper `zh`，ASR transcript 返回前 trim / 折叠空白 / 轻量繁转简，成功状态提示 `转写完成，请确认后发送`，timeout 提示可尝试更小模型或更短录音。
- Local ASR Setup UI v1 已补齐：用户可在 Settings -> Voice Input 手动输入或通过原生文件选择器填入本地 ASR binary、model 和 converter 路径；用户配置优先，env fallback 次之，完整路径不进入 Event Stream / Debug / Raw JSON。
- Local ASR v1 已达到 packaged app 可配置 MVP：真实用户手动验证已通过，包括 packaged `.app` 非黑屏、后端自启动、无 shell env 配置、Settings 持久化、重启后配置仍存在、Check Local ASR 可启动、主聊天按钮显示本地语音识别可用。
- Local ASR release regression checklist 已建立在 `docs/QA.md` 和 `docs/qa/voice_input_local_asr_scenarios.json`，覆盖 packaged clean start、no-env setup、settings persistence、主聊天语音按钮、简体化、不自动发送、隐私和 clear fallback。
- Local ASR staged foundation 已完成：feasibility plan、config detection、CLI probe、Audio Capture / Temp File probe、Backend ASR Transcription Bridge、Audio Format Conversion bridge 和 whisper-like parsing QA。
- Audio Format Conversion v1 已支持通过 Settings 用户配置或 `REILINK_AUDIO_CONVERTER_BINARY` fallback 把 WebM/Ogg 等录音格式转为 WAV；未配置或失败时安全短路，不调用 ASR。
- Local ASR 当前不提交 whisper binary，不提交 model，不提交 ffmpeg / converter binary，不接入云 ASR 或商业 ASR。
- Local ASR manual setup guide 已新增；真实 whisper.cpp / model / converter 仍由用户手动配置，不随 app 内置。
- 真实 whisper 手动 smoke 仍是 manual release regression，不是自动测试依赖。

### 当前 Overlay 状态

- Overlay v1.1 已建立底座：Settings 中新增 `Overlay / 游戏悬浮层`，默认关闭，开关、位置、透明度和消息数量持久化在 app settings。
- Overlay v1 Foundation 和 v1.1 配置项已实现，但当前 macOS 状态应描述为 safe mode / experimental freeze，而不是完整可用的游戏悬浮气泡功能。
- Overlay v1.1 Regression Freeze 已确认当前安全基线：用户手动测试已验证 ReiLink 主窗口不再闪烁、不始终置顶、可切出 / 切回、Dock 和 `⌘ + Tab` 可见、Settings 和 `强制关闭悬浮层` 可操作。
- Electron main process 可创建独立 overlay window；窗口为 frameless、transparent、always-on-top、不可聚焦，并忽略鼠标输入。非 macOS 可使用 `skipTaskbar`；macOS 当前避免让 overlay window 影响整个 ReiLink Dock / app switcher 入口。
- Overlay 已和 ReiLink 主窗口解耦显示：ReiLink 主窗口 / Settings 前台时会销毁或隐藏运行时 overlay window，避免遮挡 Settings、select/dropdown 或 macOS window controls。macOS 当前采用 emergency fail-closed 策略，切到游戏或其他 app 后也不自动显示 overlay，优先保证主窗口不闪烁、不置顶、不抢焦点。
- Settings 中的 Overlay 开关使用普通按钮组，并提供 `强制关闭悬浮层` 兜底入口；用户在 ReiLink 主窗口前台开启 Overlay 时只改变持久化 enabled 状态，不会立刻把 always-on-top window 显示到主窗口上方。
- Overlay renderer 通过 packaged/dev 共用的 `index.html?overlay=1#overlay` 标记加载，视觉上是右侧轻量半透明 Rei 短消息气泡层，不渲染完整 ReiLink sidebar、Settings、Debug 或聊天输入。
- Overlay 支持右上、右中、右下、左上、左中、左下位置预设；默认右中，并按 primary display workArea 计算窗口位置。
- Overlay 支持 0.35～0.95 背景透明度；默认 0.72，只影响背景层，不降低文字透明度。
- Overlay 只显示最近 1～3 条安全短摘要；默认 2 条，没有内容时显示 `Rei 正安静待机。`。
- assistant 最终回复和 proactive message 只会把截断/脱敏后的安全摘要推送到 overlay；不会传 raw prompt、完整 assistant reply、完整用户输入、memory、debug raw JSON、完整 transcript、API key、`.env`、完整路径、raw stdout 或 raw stderr。
- Event Stream 已加入 overlay lifecycle 安全事件：开关变化、设置变化、位置更新、窗口显示/隐藏、内容更新和错误摘要；内容更新只显示来源、字数和消息数量。
- 当前不实现 HUD / 敌人 / 玩家位置识别，不做画面理解或自动避让，不做拖拽或锁定位置。
- 后续需单独恢复 macOS overlay auto-show，并在恢复前通过 checklist 验证：不调用 `mainWindow.focus()` 抢焦点、不触发 app activation loop、不隐藏 Dock / `⌘ + Tab`、主窗口前台时 overlay 隐藏、Settings 始终可关闭 Overlay、packaged `.app` 人工验证通过。当前优先保证主窗口稳定性、Dock / `⌘ + Tab` 可见和 Settings 可关闭。

### 当前 Game Session Timeline 状态

- Game Session Timeline / Session Notes v1 已加入 Debug Panel，入口为 `Session Timeline / 本局时间线`，默认折叠，不影响主聊天、Voice / Local ASR 或 Overlay safe mode。
- Timeline 是当前 renderer session 内的游戏过程安全摘要，不是 memory、prompt raw log 或完整聊天记录；v1 不持久化，刷新或重启后清空。
- 当前可从安全 Event Bus 事件生成短摘要：游戏切换、Boss 检测、死亡次数变化、挫败状态变化、Boss 击败、知识检索使用、主动陪伴显示、pending memory 接受 / 忽略。
- 每条 item 只显示时间和短摘要，例如 `切换游戏：Elden Ring`、`检测到 Boss：Margit`、`死亡次数更新：3`、`使用知识：Margit phase 2 tips`、`记忆已接受`。
- Session Timeline v1 manual acceptance bugfix 已补齐：死亡次数会区分绝对值表达（如 `已经死了3次`、`我现在死了4次`）和增量表达（如 `又死了两次`）；`我有点冷静下来了` 可记录挫败状态缓和；`我换到空洞骑士了`、`我回法环了`、`我现在在艾尔登法环` 等显式游戏切换会更新 Game Context；`假骑士 / False Knight` 可在 Hollow Knight 上下文中识别为 Boss。
- 被动死亡表达已纳入 Game Session / Semantic Extraction 回归：`我被大树守卫杀了4次`、`被玛尔基特杀了3次`、`被假骑士打死两次` 等应记录为 failed attempt 与 death count，不应误判为 boss_cleared。
- Semantic Extraction v2 进入 LLM Shadow Mode：规则仍是唯一状态落地路径；LLM 只生成结构化影子候选用于 Debug / Event Stream / QA 观察，不直接写入 current game、Boss、death count、frustration、boss_cleared、memory 或 proactive。
- Semantic Extraction Debug 现在显示安全 trace：`source`（rule / none）、`confidence`（high / medium / low）、`fallback_reason`、`skip_reason`、`applied_updates`，以及 `llm_shadow_status` / `llm_shadow_summary` / `llm_shadow_diff`。Debug / Event Stream 只显示安全摘要，不显示完整 user message、raw prompt、raw JSON、路径或 transcript。
- Semantic Shadow 真实 provider 路径复用主 backend provider config，优先使用 fast / lightweight model；在 API chat 中规则提取同步完成，真实 LLM Shadow 作为后台 Debug 诊断补齐，避免拖慢主回复路径。
- Semantic Shadow 真实 provider 请求已收敛为三段式后台诊断：normal compact JSON + `response_format`、无 `response_format` 的 compat retry、以及最后的 ultra-compact flat JSON fallback。三段都只对 `invalid_json` 继续尝试；timeout / auth_failed / provider_unavailable / provider_error 不 retry。解析器只做安全轻量恢复，可接受严格 JSON、Markdown code fence、前后夹杂简短说明的首个 JSON object，以及数组中的首个 object。
- Semantic Shadow final event 会附带安全诊断字段：`response_format_used`、`compat_retry_used`、`ultra_compact_used`、`attempts`、`last_failure`、`json_recovery_stage`、`finish_reason`、`content_length_bucket`、`first_char_type`。这些字段只用于 Debug / Event Stream 定位 provider 兼容性问题，不包含 raw provider response、raw prompt、完整用户输入、密钥或路径。若 ultra-compact 仍无法稳定成功，当前阶段保留 Shadow diagnostics，不继续阻塞后续 Persona Pack。
- Semantic Shadow 后台诊断现在有安全 lifecycle event queue：`shadow_deferred` 只表示已调度，不作为永久终态；前端低频 polling 后应追加 `shadow_succeeded`、`shadow_timeout`、`shadow_invalid_json`、`shadow_auth_failed`、`shadow_provider_unavailable`、`shadow_provider_error`、`shadow_cancelled` 或 `shadow_expired`。这些事件只用于 Debug / Event Stream 可观测性，不写 game state、memory 或 proactive。
- Semantic Shadow event queue 是内存态，重启后清空，最多保留最近 100 条；它用于 QA / Debug 回流，不是持久化 timeline 或聊天记录。
- Semantic Shadow QA Freeze 状态：可观察复杂中文游戏表达（例如“骑马金甲大哥”“一开始拿锤子的家伙”“薄纱四回”）的低置信 trace、后台终态和安全 candidate summary；Shadow 成功只代表候选理解成功，不代表状态已应用。
- 真实 provider 仍可能返回 timeout、invalid_json、empty content 或 `finish_reason=length`。当前阶段把这些作为已知限制处理：Event Stream 必须显示明确终态和安全诊断，主聊天不受影响，Shadow 不污染 game state / memory / proactive，并且不继续阻塞后续 Persona Pack。
- 置信度设计保持可解释：高置信规则直接应用；被动死亡、near-clear、指代不明、中文游戏失败 slang 等“容易误判”的表达会降低调度置信度以触发 LLM 影子识别。provider 不可用、auth_failed、timeout、invalid JSON、provider error 或 no meaningful update 时也会记录安全 trace，而不是 silent no-op；若 JSON 被安全恢复，只显示 `JSON 已安全恢复` 这类摘要，不显示 raw provider response。
- 低置信 slang / 未知 Boss 指代只作为 trace / Shadow Mode 触发线索，不应为了测试硬编码成最终 Boss、death count 或 boss_cleared；即使 LLM 影子候选给出推测，v2 也只显示候选与规则差异，不自动应用状态更新。
- Proactive Companion 现在先判断场景，再决定低打扰短问句：明确烦躁 / 红温 / frustration count 优先归为挫败（如 `你还好吗？`），单纯死亡次数增长归为反复死亡（如 `没关系吧？`），没有状态性信号时才用沉默陪伴（如 `还在吗？`），深夜活跃局面用深夜提醒。非沉默类型触发后会等待用户回应并避免连续触发同一类型；沉默陪伴允许在冷却后重复，但仍受 idle threshold / cooldown 控制。
- 系统操作（重置记忆、清空 pending memory、重置 game session、Settings / Local ASR 保存或刷新、Debug reset 等）会短暂抑制主动陪伴，并同步已观察到的死亡 / 挫败计数，避免操作后立刻弹出旧状态 proactive。
- 显式记忆指令已加强：`记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打` 会生成 pending memory；`不用 / 不要 / 别记住` 等否定记忆请求不会生成 pending memory。
- 已击败 Boss 后继续问攻略时，纯攻略 / 位置 / build 提问不会把刚 cleared 的 Boss 重新写成 current boss；Rei 可以轻轻承接“已经打过”的上下文，但仍应继续回答实际问题，不应只停在反问上阻断需求。
- Timeline 最多保留最近有限条目，并对摘要做截断和脱敏；不显示 raw prompt、完整 user message、完整 assistant reply、完整 ASR transcript、memory 原文全文、knowledge snippet 全文、API key、`.env`、完整本地路径、raw stdout/stderr 或 raw JSON。
- Debug Panel 提供 `清空时间线`，只清空当前 timeline，不清空 Event Stream、聊天、memory、game session 或 Local ASR 设置。

### 当前 Persona Pack 状态

- Rei Persona Pack v1.1.2 已建立在 `personas/rei/`，包含 persona、voice、boundaries、game companion policy、memory policy、proactive policy、style calibration、response patterns、examples、anti examples、references 和 version metadata。
- v1.1.2 的 runtime-facing persona markdown 已改为中文优先，目标是更稳定地呈现冷静、寡言、低情绪、有距离感、少量但真实关心的游戏陪伴风格。
- v1.1.2 风格校准已进一步收敛到“表达通道窄”的原创冷感画像：不是无情或空白，而是反应压低、先观察事实、少解释感受；同时补充了非硬编码的重复回复防护，允许相近意思的自然变体，但禁止机械复读、滥用固定过渡词或把关系类回复写成“接”类元语言模板。v1.1.2 还扩展 `docs/qa/persona_regression_cases.json`，把关系类手测失败模式整理为可持续回归样例。
- Persona Pack 是 ReiLink 原创角色设定组织方式，不使用 Evangelion、Rei Ayanami、NERV、现有虚拟主播、公开人物或任何官方 IP 元素。
- 后端 Persona Pack loader 只从 repo 内 `personas/rei/` 或 packaged read-only resources 读取；不接受用户本地任意 persona 路径，不读取用户文件。
- 缺少 pack、缺少非关键 markdown 或 invalid `version.json` 时 fail-soft：主聊天继续使用内置 Rei guardrails，Debug / Prompt Preview 只显示安全状态、缺失 section 和错误 code。
- 主聊天 prompt 现在在基础系统安全 / 应用身份后注入 structured Rei Persona Pack，再继续使用游戏上下文、已确认长期记忆、知识检索和当前用户输入；pack 不能覆盖安全、隐私、待确认记忆流程、知识依据或主动陪伴门控。
- Persona Pack prompt 注入有固定长度预算：persona、style calibration、voice、response patterns、boundaries 和 policy sections 为主，examples / anti_examples 只注入少量精选；内容过长时安全截断并在 Debug summary 显示 `persona_section_truncated` 和 truncated_sections。
- Debug / Prompt Preview 保留脱敏后的 assembled prompt preview 能力，但普通 Debug / Event Stream 不展示完整 prompt 或 persona markdown。Prompt Preview 只显示 Persona Pack id、version、enabled、status、loaded_sections、injected_sections、missing_sections、fallback / truncation summary、`raw_content_omitted=true` 和 `path_omitted=true`，不展示完整 persona markdown、API key、`.env`、完整本地路径、stdout/stderr、raw JSON 或 ASR transcript 全文。
- Persona Pack v1.1.2 不做用户自定义角色、Persona 自动学习、Voice Profile、TTS 音色、Live2D 或 LLM-primary 状态写入；memory、proactive 和 Semantic Shadow 的状态写入边界保持不变。

### 当前 UI Surface / IA 状态

- UI/UX Information Architecture v0 已记录在 `docs/ui_ux_information_architecture.md`，配套机器可读场景位于 `docs/qa/ui_ux_information_architecture_scenarios.json`。
- UI Surface v0 已在 desktop renderer 实现。左侧入口现在是 workspace launcher，默认进入 Home / Chat，右侧不再默认堆叠全部 feature 和 Debug 面板。
- 已实现的 workspace：Memory、Game、Voice、Overlay、Settings、Developer / Debug、Future Presentation / Avatar。每个 workspace 以应用内 panel 打开，带 tabs、关闭按钮和 Escape 关闭，并保留聊天历史与未发送输入。
- 推荐的一级模块是 Home / Chat、Memory、Game、Voice、Overlay、Settings、Developer / Debug、Future Presentation / Avatar。普通用户默认进入 Home / Chat，Developer / Debug 不应默认淹没普通体验。
- 推荐 surface 模型是 in-app Panel Launcher & Workspace Shell：优先使用应用内 workspace / drawer / modal，暂不把普通模块拆成 Electron child window，以降低 packaged app、焦点和测试风险。
- Voice 的产品位置升级为一级模块：当前仍是 Local ASR transcript-first + Voice Output；未来直接语音对话需要单独 Voice Interaction v2 Spec，覆盖 `idle`、`listening`、`transcribing`、`ready_to_send`、`assistant_thinking`、`speaking`、`interrupted`、`error` 等状态。
- Overlay 的产品位置升级为一级模块，但当前仍是 macOS safe mode；auto-show 保持 fail-closed，未来只作为 Game-safe companion surface 显示最近 1～2 句、安全语音状态和低打扰提示。
- Memory 应成为普通用户可理解的一级模块，承接 pending / confirmed / ignored / search / source summary / session archive；Candidate Memory 或 Hermes-style memory 进入实现前应先完成 UI surface。
- Developer / Debug 应集中承接 Event Stream、Prompt Preview、Semantic Shadow trace、Knowledge trace、Persona Pack safe summary 和 Runtime status，并继续禁止 raw prompt、API key、`.env`、完整路径、stdout/stderr、完整 persona markdown 和完整 assistant reply。
- Live2D / Avatar 只作为未来 presentation layer 预留，不应先于 Voice、Overlay、Memory 和 Debug split。

### 当前 Knowledge Retrieval 状态

- Knowledge layer 已从 knowledge pack infrastructure 推进到本地 keyword retrieval 闭环。
- 已支持 top-k / snippet / context limit、grounding / gating、低相关不注入 prompt、闲聊不强行注入 knowledge。
- 用户显式游戏名优先于 current game context，跨游戏 query 有隔离。
- 当前支持 Elden Ring / 艾尔登法环 / 法环 与 Hollow Knight / 空洞骑士 sample packs。
- QA scenarios 已沉淀在 `docs/qa/retrieval_scenarios.json`，并由 backend tests 校验。
- 当前没有 embedding、vector database、hybrid retrieval 或外部攻略站 crawling。

### Runtime / Packaging 注意

- packaged `.app` 已多次验证，但 dev renderer 正常不等于 packaged `.app` 正常。
- 修改 backend binary、schema、runtime、knowledge loading 或 user-visible packaged behavior 时，需要运行 `make package-backend` 和 `make package-desktop`，并做 packaged smoke。
- `.env`、API key、memory、session、settings、logs 和本地用户数据不复制进 `.app`。
- packaged app 使用内置只读 resources 与 `~/Library/Application Support/ReiLink/data` 用户数据目录；`personas/rei` 随只读 resources 打包，缺失时后端必须 fallback 而不是崩溃。

### 后续重点

- Debug Split v1。
- Core UI Visual Polish v1。
- Voice Interaction v2 Spec。
- Hermes-style Memory Architecture v0。
- Candidate Memory v1。
- v0.2 stable packaging polish。
- Installer / DMG spike。
- Code signing / notarization research。
- Windows packaging。
- Knowledge pack expansion。
- Embedding / hybrid retrieval research。
- Local ASR model setup helper。
- Local ASR accuracy tuning、timeout tuning 和 optional larger model guidance。
- Character TTS / natural voice output。
- Overlay v1.1 packaged release smoke。
- Overlay v1.2 Drag / Lock Mode。
- Overlay 自动避让和 HUD-aware placement research。
- Persona / Memory Eval Runner v0。
- Live2D Presentation Policy。
- Live2D v1。
- Multi-companion system。

### 当前数据范围

- `elden_ring` 和 `hollow_knight` 是当前已接入的 sample knowledge packs。
- `sekiro`、`baldurs_gate_3`、`cyberpunk_2077`、`monster_hunter` 等条目可作为 planned / detected_only 状态展示，但没有完整知识包。
- 游戏注册表位于 `data/games/game_registry.json`。
- 知识目录位于 `data/knowledge/games/catalog.json`。
- 每个已支持知识包应包含 `manifest.json` 和 `snippets.json`。
- 本地知识包可用 `make validate-knowledge` 校验。
- 新增知识包规范见 `docs/KNOWLEDGE_PACK_AUTHORING.md`。

### 明确不在当前范围

- Steam login / Steam Web API。
- 外部抓取攻略站。
- RAG / vector database / embeddings。
- Cloud ASR / commercial ASR。
- Bundled whisper binary、model files 或 ffmpeg binary。
- Live2D / Vision / advanced Overlay interactions。
- Multi-character system。

### 验证基线

最近实现基线已按任务记录通过；精确 commit 以 git history 为准：

```text
backend tests: passed
desktop tests: passed
desktop build: passed
lint: passed
desktop e2e: passed
make validate-knowledge: passed
git diff --check: passed
```

文档-only 更新通常只需要运行 `git diff --check`，除非任务修改了 backend 或 frontend 文件。

## English

Updated: 2026-06-16

### Current Stage

Current stage: `v0.2-pre productization / 产品化补齐预发布阶段`.

`reilink-mvp-v0.1.1` has been published as the public showcase version for GitHub, portfolio, and interview presentation. `reilink-v0.2-pre` has been published as a pre-release, and the current `dev/codex-reilink` branch has further filled in standalone runtime / productization foundation while completing a staged Voice Interaction MVP: optional system TTS, main-chat Local ASR input, transcript-first user-confirmed sending, Local ASR Settings persistence, and release regression freeze. Overlay v1 Foundation is complete, and the project is now in Voice / Local ASR / Overlay Safe Mode regression freeze.

As of this freeze, Voice Output v1 / v1.1, Local ASR v1, Local ASR Native File Picker v1, and Overlay v1.1 macOS safe mode are the current stable regression baseline. macOS Overlay auto-show intentionally remains fail-closed and must be restored only in a separate task with packaged-app QA.

The v0.2-pre focus is not adding major core features or expanding product scope. It is making first run, developer startup, public presentation, standalone runtime, local data directories, multi-game knowledge maintenance, and release readiness clearer and more stable.

Product direction:

- Chinese-first AI companion for single-player game players.
- LLM-first response generation.
- Game context, memory, and knowledge provide supporting context.
- The current sample companion is an original ReiLink Rei-like persona and does not use official IP; v1.1.2 now uses a Chinese-first structured Persona Pack to calibrate a cold, quiet companion style.

### Current Branch

```text
dev/codex-reilink
```

### Stable Baseline Note

`PROJECT_STATUS.md` does not maintain a real-time latest commit hash. To confirm the latest commit, stable baseline, or release point, use `git log --oneline`, release tags, and the current git history.

This file records stage-level status only: MVP v0.1.1 has been published as the public showcase version; v0.2-pre has been published as a pre-release; active development continues on `dev/codex-reilink` for runtime / product foundation. Exact status should come from git log / tags.

### Completed Major Capabilities

- FastAPI backend and Electron / React desktop shell.
- DeepSeek-compatible provider.
- Model routing: `fast` / `pro` / `auto`.
- Minimal default persona with guarded fallback.
- Multi-part replies.
- Settings Panel.
- Game Session State.
- Semantic Extraction with rule-first handling, LLM Shadow Mode, and privacy-safe trace observability.
- Pending Memory confirmation.
- Proactive Companion with cooldowns, system-action suppression, recent-reply grace, scene priority, and same-trigger de-duplication.
- Local Game Detector.
- Manual Game Context Control.
- Unsupported Game fallback.
- Game Catalog / Multi-game Knowledge Interface.
- Knowledge Pack Manifest v1.
- Knowledge Retrieval: local keyword retrieval, grounding / gating, casual-chat isolation, and explicit game-name switching.
- Elden Ring sample knowledge pack.
- Hollow Knight sample knowledge pack.
- Voice Output: Voice Output settings, Test Voice, rate / volume, Chinese voice preference, and safe Event Stream summaries.
- Voice Input v1 fallback: push-to-talk Web Speech UI, safe fallback, and no auto-send.
- Main chat Local ASR voice input: when Local ASR is ready, the main chat voice button prefers local record/transcribe, with Web Speech kept as fallback.
- Voice Interaction MVP: system TTS + user-configured Local ASR + transcript-first UX + privacy-safe event summaries.
- Overlay v1.1: default-off independent transparent overlay, Settings toggle, position presets, background opacity, 1-3 safe short Rei message bubbles, and overlay lifecycle Event Stream events.
- Game Session Timeline / Session Notes v1: current-session safe summary timeline in the Debug Panel.
- Event Bus / Event Stream.
- Prompt Preview.
- Rei Persona Pack v1.1.2: Chinese-first structured original persona files, cold quiet companion calibration, human-feel and relationship-surface repetition regression fixes, safe loader, prompt assembly integration, and safe Debug Prompt Preview summary.
- Debug Dashboard.
- UI/UX Information Architecture v0: planning for future product surfaces across Home / Chat, Memory, Game, Voice, Overlay, Settings, Developer / Debug, and Future Presentation / Avatar.
- UI Surface v0: left workspace launcher, default Home / Chat, right workspace panel, separated Memory / Game / Voice / Overlay / Settings / Developer Debug / Future Avatar entries, panel tabs, close button, and Escape close.
- QA / Regression scenarios.
- UI polish.

### v0.2-pre Additions / Productization Work

- First Run / Provider Setup.
- Dev Startup / Health Check.
- Public Readiness.
- Public screenshots and showcase assets.
- Local Game Detector.
- Manual Game Context Control.
- Unsupported Game fallback.
- Knowledge Pack Manifest.
- Knowledge Pack Validation Tool.
- Knowledge Pack Authoring Guide.
- Backend bundle spike.
- Standalone App Packaging v1.
- Bundled backend binary.
- Bundled knowledge resources.
- Bundled runtime resources: read-only resources such as legacy persona data, structured `personas/rei` pack, persona style, and the game registry are distributed with the packaged app.
- Backend runtime priority: external backend, configured binary, bundled binary, repo fallback.
- User data dir: the packaged app uses `~/Library/Application Support/ReiLink/data`.
- Local Data Controls: Settings can show / open the local data directory and reuse Demo Reset / reset controls.
- Audio Capture / Temp File probe.
- Local ASR staged foundation and main chat integration: feasibility plan, config detection, CLI probe, Backend ASR Transcription Bridge, Audio Format Conversion bridge, whisper-like output parsing hardening, manual setup guide, and main chat voice provider selection.
- Local ASR Settings persistence / Setup UI: users can save, clear, refresh, and fill local ASR binary / model / converter paths with native file picker buttons in Settings; saved user data falls back to env when absent.

### Current Voice / Local ASR Status

- Voice Output v1 / v1.1 is stable: default off, Test Voice, rate / volume, and Chinese system voice preference are available, with privacy-safe Event Stream lifecycle summaries.
- Local ASR v1 is stable: it uses user-provided local whisper-like binaries, model files, and ffmpeg / converter binaries. ReiLink does not bundle whisper, models, ffmpeg, cloud ASR, or commercial ASR.
- Local ASR keeps the transcript-first boundary: recognized text only fills the input, is not auto-sent, and enters chat flow only after the user confirms by sending. Unconfirmed transcripts do not enter memory, prompt, retrieval, or game context.
- Local ASR Settings persist user paths. Full local paths may appear in Settings edit inputs as normal editable values, but not in Event Stream / Debug / Raw JSON.
- Local ASR Native File Picker v1 is available for binary, model, and converter paths. The picker only fills the path field; it does not read, copy, upload, or save files until the user saves settings.

- Voice Output is implemented and usable: Test Voice, rate / volume, Chinese voice preference, `tts_started` only after the real `utterance.onstart`, and safe Chinese Event Stream summaries.
- Voice Output currently uses system `speechSynthesis`, not character-grade voice acting; names like "Rei" and the tone may sound unnatural. A local character TTS or more natural voice provider can be researched later, but commercial TTS is not part of the current scope.
- Voice Input v1 push-to-talk fallback is implemented: Web Speech transcripts only fill the input and are not auto-sent; unconfirmed transcripts do not enter memory, prompt, knowledge retrieval, or game context.
- Web Speech Recognition is not reliable in the packaged Electron runtime and is not the stable main path; when Local ASR is ready, the main chat voice button prefers Local ASR.
- Local ASR is wired into the main chat voice button: provider selection is `local_asr` -> `web_speech` -> `unavailable`; successful local transcripts only fill the input and still require manual send.
- Local ASR v1.1 now includes transcript output polish: `zh-CN` is normalized to whisper `zh`, ASR transcripts are trimmed / whitespace-collapsed / lightly normalized to Simplified Chinese before filling the input, success asks the user to confirm before sending, and timeouts suggest a smaller model or shorter recording.
- Local ASR Setup UI v1 is complete: users can type or use native file picker buttons to fill local ASR binary, model, and converter paths from Settings -> Voice Input; saved user settings take priority over env fallback, and full paths stay out of Event Stream / Debug / Raw JSON.
- Local ASR v1 has reached a packaged-app configurable MVP: real user manual validation has passed for non-black packaged startup, backend auto-start, no-shell-env setup, Settings persistence, restart persistence, Check Local ASR startup, and main-chat local voice availability.
- Local ASR release regression checklists now live in `docs/QA.md` and `docs/qa/voice_input_local_asr_scenarios.json`, covering packaged clean start, no-env setup, settings persistence, main-chat voice button behavior, Simplified Chinese transcript output, no auto-send, privacy, and clear fallback.
- Local ASR staged foundation is complete: feasibility plan, config detection, CLI probe, Audio Capture / Temp File probe, Backend ASR Transcription Bridge, Audio Format Conversion bridge, and whisper-like parsing QA.
- Audio Format Conversion v1 can use Settings user configuration or `REILINK_AUDIO_CONVERTER_BINARY` fallback to convert WebM/Ogg-style recordings to WAV; missing or failed converters short-circuit safely and do not call ASR.
- Local ASR does not commit a whisper binary, model file, ffmpeg / converter binary, cloud ASR, or commercial ASR integration.
- The Local ASR manual setup guide has been added; real whisper.cpp / model / converter remains user-configured and is not bundled with the app.
- Real whisper manual smoke remains a manual release regression check and is not an automated test dependency.

### Current Overlay Status

- Overlay v1.1 is in place: Settings now includes `Overlay / 游戏悬浮层`, defaults to off, and persists enabled state, position, opacity, and message count through app settings.
- Overlay v1 Foundation and v1.1 configuration are implemented, but the current macOS state should be described as safe mode / experimental freeze, not as a fully available in-game bubble overlay.
- Overlay v1.1 Regression Freeze has a confirmed safety baseline: user manual testing verified that the ReiLink main window no longer flickers, no longer stays always-on-top, can switch away and back, remains visible in Dock and `⌘ + Tab`, and keeps Settings plus `强制关闭悬浮层` operable.
- The Electron main process can create a separate overlay window that is frameless, transparent, always-on-top, non-focusable, and ignores mouse input. Non-macOS can use `skipTaskbar`; macOS currently avoids letting the overlay window affect the whole ReiLink Dock / app switcher entry.
- Overlay visibility is separated from the enabled setting: the runtime overlay window is destroyed or hidden while the ReiLink main window / Settings is foreground, so it does not cover Settings, select/dropdown controls, or macOS window controls. macOS currently uses an emergency fail-closed policy and does not auto-show overlay after switching away, prioritizing normal main-window focus behavior.
- The Settings Overlay control uses regular buttons and includes a `强制关闭悬浮层` fallback; enabling Overlay while ReiLink is foreground only persists enabled state and does not immediately show an always-on-top window above the main UI.
- The overlay renderer loads through the shared packaged/dev `index.html?overlay=1#overlay` marker and renders a restrained right-side translucent Rei short-message bubble layer without the full ReiLink sidebar, Settings, Debug, or chat input.
- Overlay supports top-right, middle-right, bottom-right, top-left, middle-left, and bottom-left presets; the default is middle-right and bounds are calculated within the primary display workArea.
- Overlay supports 0.35-0.95 background opacity; the default is 0.72 and only affects the background layer, not text alpha.
- Overlay shows only the latest 1-3 safe short summaries; the default is 2, and with no content it shows `Rei 正安静待机。`.
- Completed assistant replies and proactive messages send only truncated/redacted safe summaries to overlay; raw prompt, full assistant reply, full user input, memory, debug raw JSON, full transcript, API keys, `.env`, full paths, raw stdout, and raw stderr are excluded.
- Event Stream includes safe overlay lifecycle events for enabled changes, settings changes, position updates, show/hide, content updates, and errors; content updates expose only source, character count, and message count.
- The current scope does not include HUD / enemy / player-position detection, vision, automatic avoidance, dragging, or locking.
- A later macOS-specific overlay pass should restore auto-show only after passing the checklist: no `mainWindow.focus()` focus stealing, no app activation loop, no hidden Dock / `⌘ + Tab`, overlay hidden while the main window is foreground, Settings always able to disable Overlay, and packaged `.app` manual verification complete. The current priority is main-window stability, Dock / `⌘ + Tab` visibility, and keeping Settings able to disable Overlay.

### Current Game Session Timeline Status

- Game Session Timeline / Session Notes v1 is available in the Debug Panel as `Session Timeline / 本局时间线`; it is folded by default and does not affect main chat, Voice / Local ASR, or Overlay safe mode.
- The timeline is a current renderer-session-only safe game-process summary. It is not memory, not a raw prompt log, and not a full chat transcript; v1 is not persisted and clears on refresh or restart.
- It can generate short items from safe Event Bus events for game switches, boss detection, death count changes, frustration changes, boss clears, knowledge usage, proactive messages, and pending memory accept / ignore actions.
- Each item shows only time plus a short summary, such as `切换游戏：Elden Ring`, `检测到 Boss：Margit`, `死亡次数更新：3`, `使用知识：Margit phase 2 tips`, or `记忆已接受`.
- The Session Timeline v1 manual-acceptance bugfix now distinguishes absolute death counts (`已经死了3次`, `我现在死了4次`) from incremental counts (`又死了两次`), records calm/frustration easing, recognizes explicit Elden Ring / Hollow Knight switches, and resolves `假骑士 / False Knight` in Hollow Knight context.
- Passive death statements are covered by Game Session / Semantic Extraction regression: `我被大树守卫杀了4次`, `被玛尔基特杀了3次`, and `被假骑士打死两次` should become failed attempts with death counts, not boss_cleared.
- Semantic Extraction v2 now uses LLM Shadow Mode: rules remain the only state-application path; the LLM produces structured shadow candidates only for Debug / Event Stream / QA observability and does not directly write current game, Boss, death count, frustration, boss_cleared, memory, or proactive state.
- Semantic Extraction Debug now exposes a safe trace: `source` (rule / none), `confidence` (high / medium / low), `fallback_reason`, `skip_reason`, `applied_updates`, plus `llm_shadow_status`, `llm_shadow_summary`, and `llm_shadow_diff`. Debug / Event Stream summaries do not expose full user messages, raw prompts, raw JSON, paths, or transcripts.
- The real-provider Semantic Shadow path reuses the main backend provider config and prefers the fast / lightweight model; during API chat, rule extraction stays synchronous while the real LLM Shadow diagnostic runs as a background Debug update so the main reply path is not delayed.
- Real-provider Semantic Shadow requests now use a three-step background diagnostic path: normal compact JSON with `response_format`, compatibility retry without `response_format`, and a final ultra-compact flat JSON fallback. Only `invalid_json` advances to the next attempt; timeout, auth_failed, provider_unavailable, and provider_error do not retry. The parser only performs safe lightweight recovery for strict JSON, Markdown code fences, brief prose around the first JSON object, and arrays containing a first object.
- Semantic Shadow final events include safe diagnostics: `response_format_used`, `compat_retry_used`, `ultra_compact_used`, `attempts`, `last_failure`, `json_recovery_stage`, `finish_reason`, `content_length_bucket`, and `first_char_type`. These fields are Debug / Event Stream observability only and do not include raw provider responses, raw prompts, full user input, secrets, or paths. If ultra-compact fallback still cannot stabilize the real provider, this stage keeps Shadow diagnostics and should not block the next Persona Pack work.
- Background Semantic Shadow diagnostics now use a safe lifecycle event queue: `shadow_deferred` only means scheduled, not a permanent terminal state; renderer polling should append `shadow_succeeded`, `shadow_timeout`, `shadow_invalid_json`, `shadow_auth_failed`, `shadow_provider_unavailable`, `shadow_provider_error`, `shadow_cancelled`, or `shadow_expired`. These events are observability-only and do not write game state, memory, or proactive state.
- The Semantic Shadow event queue is in-memory, clears on restart, and keeps at most the latest 100 events. It is for QA / Debug return flow, not persistent timeline or chat history.
- Semantic Shadow QA Freeze status: low-confidence traces, background terminal events, and safe candidate summaries are observable for complex Chinese game expressions such as rider-gold-armor aliases, first-hammer-enemy aliases, and slang failure counts. A successful Shadow means only candidate understanding succeeded; it does not mean state was applied.
- Real providers may still return timeout, invalid_json, empty content, or `finish_reason=length`. This is a known limitation for this stage: Event Stream must show a clear terminal status and safe diagnostics, main chat remains unaffected, Shadow does not pollute game state / memory / proactive, and this should not block the next Persona Pack work.
- Confidence is designed to stay explainable: high-confidence rules apply directly; passive-death, near-clear, unclear-reference, and Chinese game-failure slang expressions lower scheduling confidence so LLM Shadow Mode can run when available. Provider unavailable, auth_failed, timeout, invalid JSON, provider error, or no meaningful update still records a safe trace instead of a silent no-op; when JSON is safely recovered, Debug only shows a short `JSON 已安全恢复`-style summary, not the raw provider response.
- Low-confidence slang / unknown Boss references are only trace / Shadow Mode triggers, not hardcoded final Boss, death-count, or boss-cleared updates. Even when the LLM shadow produces a candidate, v2 only displays the candidate and rule diff; it does not automatically apply state updates.
- Proactive Companion now separates scenes before choosing a low-interruption question: explicit frustration or frustration count uses frustration wording such as `你还好吗？`; death-count growth without explicit frustration uses repeated-death wording such as `没关系吧？`; idle without stronger state signals uses silence wording such as `还在吗？`; active late-night sessions use late-night wording. Non-silence triggers wait for user activity and avoid consecutive same-type triggers; idle silence may repeat after cooldown but still respects idle threshold and cooldown.
- System actions such as memory reset, pending-memory clear, game-session reset, Settings / Local ASR save or refresh, and Debug reset briefly suppress proactive checks and sync observed death / frustration counts so old state does not immediately trigger a proactive message.
- Explicit memory requests now cover the playstyle preference `记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打`, while negated requests such as `不用 / 不要 / 别记住` remain non-memory.
- After a boss is cleared, pure strategy / location / build questions do not reopen the cleared Boss as the current Boss. Rei may lightly acknowledge that context when the user asks for more strategy, but should still answer the actual question instead of stopping at a blocking rhetorical question.
- The timeline keeps a bounded recent list and redacts/truncates summaries. It must not show raw prompts, full user messages, full assistant replies, full ASR transcripts, full memory text, full knowledge snippets, API keys, `.env`, full local paths, raw stdout/stderr, or raw JSON.
- `清空时间线` clears only the current timeline and does not clear Event Stream, chat, memory, game session, or Local ASR settings.

### Current Persona Pack Status

- Rei Persona Pack v1.1.2 now lives in `personas/rei/` with persona, voice, boundaries, game companion policy, memory policy, proactive policy, style calibration, response patterns, examples, anti examples, references, and version metadata.
- v1.1.2 runtime-facing persona markdown is Chinese-first and calibrates Rei toward calm, terse, low-emotion, slightly distant, lightly caring game companionship.
- v1.1.2 calibration now further narrows Rei toward an original narrow-expression cold persona: not emotionless or blank, but low-output, fact-first, and reluctant to explain feelings. It also adds non-hardcoded repetition control: similar meaning may use natural variation, while mechanical repeats, overused transition words, and relationship meta-language templates are forbidden. v1.1.2 also extends `docs/qa/persona_regression_cases.json` to keep relationship hand-test failure modes as sustainable regression cases.
- The pack is an original ReiLink character organization layer. It does not use Evangelion, Rei Ayanami, NERV, existing VTuber, public-figure, or official IP material.
- The backend Persona Pack loader reads only repo `personas/rei/` or packaged read-only resources. It does not accept arbitrary user persona paths or read user files.
- Missing packs, missing non-critical markdown, and invalid `version.json` fail soft. Main chat keeps built-in Rei guardrails, while Debug / Prompt Preview shows only safe status, missing sections, and error codes.
- Main chat prompt assembly now injects the structured Rei Persona Pack after the 基础系统安全 / 应用身份 block, then continues with game context, confirmed long-term memory, knowledge retrieval, and the current user input. The pack cannot override safety, privacy, pending memory confirmation, knowledge grounding, proactive gating, or the LLM Shadow candidate-only boundary.
- Persona Pack prompt injection has a fixed length budget: persona, style calibration, voice, response patterns, boundaries, and policy sections are primary, while examples / anti_examples inject only a small stable selection. Overlong content is safely truncated and Debug summary reports `persona_section_truncated` and truncated_sections.
- Debug / Prompt Preview keeps the redacted assembled prompt preview capability, while ordinary Debug / Event Stream must not show the full prompt or persona markdown. Prompt Preview shows only Persona Pack id, version, enabled state, status, loaded_sections, injected_sections, missing_sections, fallback / truncation summary, `raw_content_omitted=true`, and `path_omitted=true`; it does not show full persona markdown, API keys, `.env`, full local paths, stdout/stderr, raw JSON, or full ASR transcripts.
- Persona Pack v1.1.2 does not implement custom characters, persona self-learning, Voice Profile, TTS voice models, Live2D, or LLM-primary state writes. Memory, proactive, and Semantic Shadow write boundaries remain unchanged.

### Current UI Surface / IA Status

- UI/UX Information Architecture v0 lives in `docs/ui_ux_information_architecture.md`, with machine-readable scenarios in `docs/qa/ui_ux_information_architecture_scenarios.json`.
- UI Surface v0 is implemented in the desktop renderer. The left navigation is now a workspace launcher, Home / Chat is the default surface, and the right side no longer stacks all feature and Debug panels by default.
- Implemented workspaces: Memory, Game, Voice, Overlay, Settings, Developer / Debug, and Future Presentation / Avatar. Each opens as an in-app panel with tabs, a close button, and Escape close behavior while preserving chat history and unsent chat input.
- The recommended top-level modules are Home / Chat, Memory, Game, Voice, Overlay, Settings, Developer / Debug, and Future Presentation / Avatar. Normal users should default to Home / Chat, while Developer / Debug should not overwhelm the ordinary experience by default.
- The recommended surface model is an in-app Panel Launcher & Workspace Shell: prefer in-app workspaces, drawers, and modals before splitting ordinary modules into Electron child windows, which would raise packaged-app, focus, and test risk.
- Voice becomes a top-level product module. The current state remains Local ASR transcript-first plus Voice Output; direct spoken conversation requires a separate Voice Interaction v2 Spec covering `idle`, `listening`, `transcribing`, `ready_to_send`, `assistant_thinking`, `speaking`, `interrupted`, and `error`.
- Overlay becomes a top-level module but remains macOS safe mode. Auto-show stays fail-closed; the future direction is a game-safe companion surface for the latest 1-2 safe lines, voice state, and low-interruption hints.
- Memory should become an understandable normal-user module for pending / confirmed / ignored / search / source summary / session archive. Candidate Memory or Hermes-style memory should wait for the UI surface.
- Developer / Debug should contain Event Stream, Prompt Preview, Semantic Shadow trace, Knowledge trace, Persona Pack safe summary, and Runtime status while continuing to block raw prompts, API keys, `.env`, full paths, stdout/stderr, full persona markdown, and full assistant replies.
- Live2D / Avatar is only a future presentation layer placeholder and should follow Voice, Overlay, Memory, and Debug split work.

### Current Knowledge Retrieval Status

- The knowledge layer has moved from knowledge pack infrastructure to a local keyword retrieval loop.
- It supports top-k / snippet / context limits, grounding / gating, low-relevance prompt exclusion, and casual-chat isolation.
- Explicit game names from the user take priority over current game context, with cross-game query isolation.
- Current sample packs cover Elden Ring and Hollow Knight, including Chinese aliases.
- QA scenarios live in `docs/qa/retrieval_scenarios.json` and are validated by backend tests.
- There is no embedding, vector database, hybrid retrieval, or external guide-site crawling yet.

### Runtime / Packaging Notes

- Packaged `.app` has been smoke-tested repeatedly, but a healthy dev renderer does not prove packaged `.app` behavior.
- When backend binary, schema, runtime, knowledge loading, or user-visible packaged behavior changes, run `make package-backend`, `make package-desktop`, and a packaged smoke test.
- `.env`, API keys, memory, session, settings, logs, and local user data are not copied into the `.app`.
- The packaged app uses read-only bundled resources and the user data directory at `~/Library/Application Support/ReiLink/data`; `personas/rei` is bundled as a read-only resource, and missing pack resources must fallback instead of crashing.

### Upcoming Focus

- Debug Split v1.
- Core UI Visual Polish v1.
- Voice Interaction v2 Spec.
- Hermes-style Memory Architecture v0.
- Candidate Memory v1.
- v0.2 stable packaging polish.
- Installer / DMG spike.
- Code signing / notarization research.
- Windows packaging.
- Knowledge pack expansion.
- Embedding / hybrid retrieval research.
- Local ASR model setup helper.
- Local ASR accuracy tuning, timeout tuning, and optional larger-model guidance.
- Character TTS / natural voice output.
- Overlay v1.1 packaged release smoke.
- Overlay v1.2 Drag / Lock Mode.
- Overlay automatic avoidance and HUD-aware placement research.
- Persona / Memory Eval Runner v0.
- Live2D Presentation Policy.
- Live2D v1.
- Multi-companion system.

### Current Data Scope

- `elden_ring` and `hollow_knight` are the currently supported sample knowledge packs.
- `sekiro`, `baldurs_gate_3`, `cyberpunk_2077`, `monster_hunter`, and similar entries may appear as planned / detected_only catalog states, but they do not have full knowledge packs.
- The game registry lives at `data/games/game_registry.json`.
- The knowledge catalog lives at `data/knowledge/games/catalog.json`.
- Each supported knowledge pack should include `manifest.json` and `snippets.json`.
- Local knowledge packs can be validated with `make validate-knowledge`.
- New knowledge pack authoring guidance lives in `docs/KNOWLEDGE_PACK_AUTHORING.md`.

### Explicitly Out Of Scope For Now

- Steam login / Steam Web API.
- External guide-site crawling.
- RAG / vector database / embeddings.
- Cloud ASR / commercial ASR.
- Bundled whisper binaries, model files, or ffmpeg binaries.
- Live2D / Vision / advanced Overlay interactions.
- Multi-character system.

### Verification Baseline

The latest implementation baseline passed according to task records; the exact commit should be read from git history:

```text
backend tests: passed
desktop tests: passed
desktop build: passed
lint: passed
desktop e2e: passed
make validate-knowledge: passed
git diff --check: passed
```

Documentation-only updates usually only require `git diff --check`, unless backend or frontend files are changed.
