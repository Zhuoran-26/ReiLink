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
- `docs/qa/persona_regression_cases.json`
- `docs/qa/ui_ux_information_architecture_scenarios.json`
- `docs/qa/ui_surface_scenarios.json`
- `docs/qa/voice_interaction_v2_scenarios.json`
- `docs/qa/voice_profile_scenarios.json`
- `docs/qa/llm_primary_guarded_extraction_scenarios.json`
- `docs/qa/extraction_eval_scenarios.json`
- `docs/qa/memory_architecture_scenarios.json`
- `docs/qa/candidate_memory_scenarios.json`

### 1. 基础启动检查

#### Dev App

- 启动 backend：`make dev-backend`。
- 启动 desktop：`make dev-desktop`。
- 主界面不是黑屏。
- 默认进入 Home / Chat；主聊天区、输入框、左侧 workspace launcher 正常显示。
- 右侧 workspace panel 默认关闭，不应默认堆满 Settings、Debug、Prompt Preview 或 Event Stream。
- `curl http://127.0.0.1:8000/api/health` 返回 `{"status":"ok"}`。
- 点击 Settings 后 Settings workspace 可见。
- 点击 Developer / Debug 后 Debug workspace 可见。
- 在 Developer / Debug 的 Event Stream tab 中，`事件流 / Event Stream` 标题可见，默认折叠，展开后能看到事件或“暂无事件”。
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
- 左侧 workspace launcher 可见；Settings、Voice、Overlay、Developer / Debug workspace 可打开。
- Developer / Debug 中 Event Stream 可见。
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
11. 默认 confirm-send 下 transcript 不自动发送。
12. Event Stream / Debug 不显示完整路径、stdout/stderr、transcript、API key 或 `.env`。

#### D. Voice / ASR Regression

1. Voice Output 默认关闭。
2. Test Voice 可用。
3. TTS 不朗读完整敏感内容到 Event Stream。
4. Web Speech fallback 不作为可靠主路径。
5. Local ASR ready 状态可显示。
6. Record & Transcribe 可用。
7. 默认 confirm-send 下识别结果填入输入框但不自动发送。
8. 用户确认后才进入 chat flow。
9. accepted memory 才进入 prompt。
10. proactive 内容不进入 memory。

### 1.6 Rei Persona Pack v1.1.2 回归检查

本节用于 Persona Pack v1.1.2。它不表示用户自定义角色、Live2D、TTS 音色或 persona 自动学习已开始。

1. `personas/rei/` 包含 persona、voice、boundaries、game companion policy、memory policy、proactive policy、style calibration、response patterns、examples、anti examples、references 和 `version.json`。
2. runtime-facing persona markdown 应中文优先；`version.json` key 继续保持英文兼容。
3. 主聊天 prompt 使用 structured Rei Persona Pack，但仍保留 base system safety / app identity。
4. Prompt Preview 继续保留脱敏后的 assembled prompt preview 能力；Event Stream / 普通 Debug 摘要不显示完整 prompt 或 persona markdown。
5. Debug Panel / Prompt Preview 只显示 persona pack id、version、enabled、status、loaded_sections、injected_sections、missing_sections、fallback 状态、`persona_section_truncated`、truncated_sections、`raw_content_omitted=true` 和 `path_omitted=true`。
6. Debug Panel / Prompt Preview 不显示完整 prompt、完整 persona markdown、完整用户输入、API key、`.env`、完整本地路径、raw stdout/stderr、raw JSON 或 ASR transcript 全文。
7. Persona Pack prompt 注入必须有长度预算：persona / voice / style calibration / response patterns / boundaries / policies 为主，examples / anti_examples 只取少量精选；内容过长时安全截断并在 Debug summary 显示 `persona_section_truncated`。
8. Rei 风格应更冷静、寡言、低情绪、有距离感；不是无情或空白，而是表达通道窄、反应压低、先观察事实。不客服、不鸡汤、不攻略百科、不热情欢迎、不撒娇、不卖萌。
9. Persona Pack 文件和 assembled persona prompt 不包含外部官方 IP / 既有角色标识，例如 Evangelion、Rei Ayanami、NERV、EVA、永雏塔菲、taffy-skill 的具体文本、口癖或设定。
10. 发送 `我在艾尔登法环打玛尔基特，已经死了3次，有点烦。`，Rei 应先承接挫败，再给一个轻量建议；不应变成客服腔、鸡汤或长篇攻略百科。
11. 发送 `玛尔基特二阶段怎么打？`，Rei 可以给简短策略，默认 3 到 6 句内，不要展开完整攻略站式打法。
12. 发送 `终于打过玛尔基特了。`，Rei 应简短确认，不过度庆祝，保留轻微陪伴感。
13. 发送 `记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。`，应经 Memory Candidate guard 后写入长期记忆，并在聊天页显示可撤销的轻量提示；隐式偏好仍应进入 pending memory confirmation。
14. 发送 `以后不用记住这个，只是我这次随便说一下。`，不应触发 pending memory。
15. 连续相似问题或关系追问时，Rei 不应机械复读上一轮回复；可以保留相近意思，但应换观察点、语序或轻微过渡。不要把“也”“还”“嗯”等变成新的固定口癖。
16. “看见 / 看着 / 坐在旁边 / 我在这里”类陪伴意象只能低频使用，不能成为关系追问或死亡循环的默认模板。
17. 关系类回复不应高频使用“不擅长接 / 不太会接 / 不知道怎么接”等把对话称为“接”的元语言；“这里不是空的 / 我会记得 / 你一直回来”等强落点不能近邻复用。
18. 示例和强意象只作为方向参考，不作为回复候选；真实回复应优先依据当前输入，在人设框架内自然生成。
19. Persona Pack 不应直接触发 proactive，也不应改变 Semantic Shadow candidate-only 边界。
20. 打包验证需运行 `make package-backend` 和 `make package-desktop`；packaged `.app` 中 `personas/rei` 应作为只读 resource 可用，缺失时必须 safe fallback，不应黑屏或 backend crash。

### 1.7 UI/UX Information Architecture v0 人工验收

本节用于 `docs/ui_ux_information_architecture.md`。IA 已落到 UI Surface v0；本节同时确认当前 Voice 已接入 Voice v2.1 + Voice Profile v1：默认确认发送、显式 opt-in 直接对话和规则化 full / brief / silent 播报策略。不表示 hands-free、角色 TTS / 角色音色、Overlay voice state、Overlay auto-show、Hermes-style memory 或 Live2D 已实现。

机器可读场景见 `docs/qa/ui_ux_information_architecture_scenarios.json`。

1. 普通用户默认应进入 Home / Chat，而不是 Debug、Prompt Preview、Event Stream 或 Raw JSON。
2. 左侧定位应是 workspace launcher，不只是页面 anchor。
3. Memory 应有独立普通用户入口，承接 pending、confirmed、ignored、search、sources 和后续 session archive。
4. Game 应有独立普通用户入口，承接 current game、boss、session state、knowledge availability 和 manual control。
5. Voice 应有独立一级入口；当前是 Local ASR transcript-first 默认 + Voice Output + Voice v2.1 直接对话显式 opt-in + Voice Profile v1 行为策略，hands-free、角色 TTS / 角色音色和 Overlay voice state 仍只做未来规划。
6. Voice 未来状态至少覆盖 idle、listening、transcribing、ready_to_send、assistant_thinking、speaking、interrupted 和 error。
7. Overlay 应有独立入口，但 macOS auto-show 仍是 fail-closed safe mode；不要把它描述为完整可用的游戏 HUD。
8. Developer / Debug 应与普通体验分离，承接 Event Stream、Prompt Preview、LLM Primary / Semantic Shadow trace、Knowledge trace、Persona Pack safe summary 和 Runtime status。
9. Prompt Preview / Debug 不得显示 raw prompt、API key、`.env`、完整路径、stdout/stderr、完整 persona markdown、完整 assistant reply、完整 user input 或完整 ASR transcript。
10. Memory 和 Game Session state 必须区分：长期记忆 / candidate memory 不等于当前 boss、death count、frustration 或 session timeline。
11. Future Presentation / Avatar / Live2D 只预留，不应成为当前主体验，也不应排在 Voice、Overlay、Memory 和 Debug split 之前。
12. Panel Shell 切换 workspace 时不应丢失未发送的聊天输入。

### 1.8 UI Surface v0 人工验收

机器可读场景见 `docs/qa/ui_surface_scenarios.json`。

1. 默认打开 Home / Chat，右侧 workspace panel 关闭。
2. 左侧 launcher 可见，并包含 Home / Chat、Memory、Game、Voice、Overlay、Settings、Developer / Debug 和 Future / Avatar 入口。
3. 点击 Memory 打开 Memory workspace；Pending tab 可见，Confirmed / Local Data / Future placeholder 可切换。
4. 点击 Game 打开 Game workspace；Current Context、Session Timeline、Knowledge、Manual Control 可切换。
5. 点击 Voice 打开 Voice workspace；Conversation 状态面板、Input / Local ASR、Output、Voice Profile 策略面板可切换。Local ASR 和 Voice Output 现有控件仍可找到。
6. 点击 Overlay 打开 Overlay workspace；Safe Mode、Placement、Content、Future Game Mode 可切换。强制关闭悬浮层按钮仍可找到，auto-show 仍未恢复。
7. 点击 Settings 打开 Settings workspace；app-level 设置、模型状态、本地数据和旧配置入口仍可找到。
8. 点击 Developer / Debug 打开 Debug workspace；Event Stream、Prompt Preview、Runtime、LLM Primary / Semantic Shadow trace 可找到，且 Debug 不默认打开。
9. 每个 workspace 可以点击关闭按钮关闭；按 Escape 也能关闭。
10. 切换 workspace 后聊天输入草稿不丢，聊天历史不丢，后端连接状态不被重置。
11. Prompt Preview 仍只显示安全摘要，不显示完整 prompt、完整 persona markdown、完整路径、`.env`、API key 或 raw provider response。
12. Future / Avatar 只是 placeholder，不加载 Live2D runtime、不引入资源文件。
13. Workspace header、title、关闭按钮和 tabs 应始终在内容卡片上方完整可见。
14. Developer / Debug 的 Event Stream、Prompt Preview、Runtime、Trace tabs 均可点击切换。
15. Settings 的 应用、模型、隐私 / 数据、高级 tabs 均可点击切换，设置内容不能覆盖 tab hit area。
16. Voice、Overlay、Game、Memory 和 Future / Avatar tabs 均可点击，且内容卡片不遮挡 tab row。
17. Workspace 内部长内容只在 body 内滚动；header、tabs 和关闭按钮不随 body 滚动，也不被 body 覆盖。
18. 小窗口下 workspace 不应出现明显横向溢出；tabs 与关闭按钮仍可见且可点击。

### 1.9 UI Surface v0.2 tab 内容切换回归验收

1. Settings workspace 中 应用、模型、隐私 / 数据、高级 tabs 的 active 样式与实际内容一致；模型 tab 显示模型状态，隐私 / 数据 tab 显示本地数据，高级 tab 显示 Overlay、Voice Output、Voice Input / Local ASR 旧配置入口。
2. Developer / Debug workspace 中 Event Stream、Prompt Preview、Runtime、Trace tabs 均显示对应安全面板；Prompt Preview 仍不显示完整 prompt、完整 persona markdown、API key、`.env`、完整路径或 raw provider response。
3. Voice workspace 中 Conversation、Input / Local ASR、Output、Voice Profile tabs 均显示不同内容；Conversation 显示 Voice v2 状态、确认发送 / 直接对话模式、输出状态和安全边界，Input 仍能找到 Local ASR，Output 仍能找到 Test Voice / Voice Output。
4. Overlay workspace 中 Safe Mode、Placement、Content、Future Game Mode tabs 均显示不同内容；Safe Mode 继续说明 macOS auto-show fail-closed，Future Game Mode 不恢复 auto-show。
5. Future / Avatar workspace 中 Avatar 与 Presentation Policy tabs 显示不同 placeholder，且不加载 Live2D runtime、Avatar 资源或 presentation layer 行为。
6. 切换任意 workspace tab 不应清空聊天历史或未发送输入；切换到其他 workspace 后，该 workspace 的上次 active tab 可独立保留，不污染其他 workspace。
7. Close button 与 Escape 关闭 workspace 仍有效；v0.1 的 tabs 不遮挡、body 内部滚动隔离、小窗口 hit-testing 要继续通过。
8. 本轮接入 Voice v2.1 直接对话显式 opt-in 和 Voice Profile v1 行为策略；仍不实现 hands-free、角色 TTS / 角色音色、Overlay voice state、Overlay auto-show、Hermes-style memory 或 Live2D。

### 1.10 Voice Interaction v2.1 Direct Conversation Mode 人工验收

设计文档见 `docs/voice_interaction_v2_spec.md`，机器可读场景见 `docs/qa/voice_interaction_v2_scenarios.json`。本节验收 Voice v2 state machine、默认确认发送、显式 opt-in 直接对话和 Voice Profile v1 brief 默认；不表示 hands-free、角色 TTS / 角色音色或 Overlay voice state 已实现。

1. Voice v2 默认仍是 confirm-send：ASR transcript 进入 ready-to-send 状态，用户确认后才进入 chat flow。
2. 直接对话模式必须默认关闭，只能由用户在 Voice workspace Conversation 中显式切换到 `直接对话`；不得因开启 Local ASR、Voice Output 或打开 Voice workspace 自动启用。
3. 直接对话模式开启后，ASR transcript 转写成功会自动进入现有 chat flow；不得绕过 Memory Candidate guard、knowledge gating、game context safety、persona guardrails 或 provider error handling。显式记忆可显示非阻塞撤销提示，隐式候选仍待确认。
4. 直接对话模式下，录音过短、transcript 太短或疑似半句时不得自动发送；应进入 `ready_to_send`，提示“这句太短了。可以再说一次。”或等价安全文案。
5. 被 partial guard 拦下的 transcript 不写 memory、不触发 proactive、不进入 game context / Semantic Extraction，Event Stream 只能显示 provider、字符数、时长和阻断原因。
6. 直接对话不是 hands-free：每一轮仍需要用户主动点击或按住语音输入；当前不做 wake word、不做后台常驻监听、不做自动下一轮录音。
7. Voice Output 开启时，直接对话的 assistant 最终回复默认短版播报，完整回复仍显示在聊天里；Voice Output 关闭时只显示文字回复。
8. Stop Voice 能打断直接对话后的 TTS；用户开始新一轮录音时应先停止正在播放的 TTS。
9. 状态机至少覆盖 `idle`、`listening`、`transcribing`、`ready_to_send`、`assistant_thinking`、`speaking`、`interrupted` 和 `error`。
10. `listening` 和 `speaking` 必须互斥。
11. 未确认 transcript 不写 memory、不创建 pending memory、不进入 prompt / retrieval / game context / Semantic Extraction，也不触发 proactive。
12. 直接对话的 Event Stream / Debug / Raw JSON / Prompt Preview / Overlay 只能显示 mode、provider、字符数、句数、长度上限、跳过原因和生命周期摘要；不得显示完整 transcript、raw prompt、完整 assistant reply、spoken text、路径、API key、`.env`、stdout 或 stderr。
13. Voice Output 只能朗读安全 assistant reply、Test Voice 或未来安全短摘要；不得朗读 Debug、Prompt Preview、Event Stream、LLM Primary / Semantic Shadow trace、raw prompt、raw provider response、完整 transcript、memory 内部信息、API key、`.env`、完整路径、stdout 或 stderr。
14. 游戏中语音输出应短、低打扰；长攻略内容可以保留在 chat text，不应整段朗读 Debug 或知识原文。
15. Voice workspace 的 Conversation tab 应承接状态、确认发送 / 直接对话切换、确认、打断和错误；Input / Local ASR 与 Output 继续承接现有配置，Output tab 应说明直接对话 + Voice Output 的默认短版自动播报关系。
16. Home / Chat 输入区应显示紧凑 voice state 和当前模式，但不得清空未发送草稿或隐藏普通文本输入。
17. 未来 Overlay 只可显示低风险 voice state，不显示完整 transcript、完整 assistant reply、Debug、Prompt Preview、memory 内容或敏感信息；macOS auto-show 仍不在本 spec 范围内。
18. 错误文案应中文优先、短且安全：覆盖 ASR 未配置、binary / model 缺失、converter 缺失、ASR timeout、无 transcript、mic permission denied、TTS unavailable 和 provider timeout。

### 1.11 Voice Profile v1 人工验收

设计文档见 `docs/voice_profile_v1.md`，机器可读场景见 `docs/qa/voice_profile_scenarios.json`。

1. Voice workspace 的 Voice Profile tab 应显示当前 profile `rei_calm` / `Rei Calm / Rei 冷静陪伴`。
2. UI 应明确这是行为策略，不是角色音色或新 TTS 引擎；当前仍使用系统 `speechSynthesis`。
3. 默认普通聊天播报模式为 `full`，默认直接对话播报模式为 `brief`。
4. 直接对话 + Voice Output 开启时，完整 assistant reply 仍在聊天中可见，TTS 只读短版。
5. 将直接对话播报模式改为 `full` 后，应朗读清理后的完整 assistant reply。
6. 将直接对话播报模式改为 `silent` 后，应只显示文字，不启动 TTS，并记录安全跳过原因。
7. 最长播报字数和句数可配置；brief 模式应遵守配置上限。
8. 主动陪伴和记忆确认播报默认关闭，开启也只能播报安全文本。
9. Voice Profile 决策不得朗读 Debug、Prompt Preview、Event Stream、Trace、Knowledge trace、Persona summary、Memory internal、raw prompt、API key、`.env`、完整路径、stdout 或 stderr。
10. 代码块、inline code、JSON 和 trace-like structured content 不应被整段读出；清理后为空则跳过。
11. Voice Profile 相关事件只允许包含 profile id、source、mode、字符数、句数、长度上限和 skip reason；不得包含完整 assistant reply、spoken text、ASR transcript、raw prompt 或敏感信息。
12. Test Voice 仍可播放固定测试文本，不写入聊天，也不代表角色音色。
13. 直接对话自动发送时，已有未发送手打草稿不得被 Voice Profile 或播报策略清空。

### 1.12 LLM-primary Guarded Extraction v1.0.3 Pilot 人工验收

设计文档见 `docs/llm_primary_guarded_extraction_architecture.md`，机器可读验收场景见 `docs/qa/llm_primary_guarded_extraction_scenarios.json`，固定 eval 场景见 `docs/qa/extraction_eval_scenarios.json`。本节验收当前 v1.0.3 pilot runtime 与 Extraction Eval Runner v0：foreground LLM semantic reader、tolerant-but-safe candidate schema、live JSON / schema reliability、switch / negation role fields、formal game state 与 candidate understanding 分层、confirmation intent trace、deterministic guard、rule grounding / fallback、source metadata、safe parse diagnostics、safe trace 和 mock-first regression runner。

1. 文档应明确 rule-first 的早期优势：可预测、易测、少量游戏稳定、不依赖 provider。
2. 文档应明确 rule-first 的扩展瓶颈：多游戏 alias 爆炸、ASR 近音错字、规则 no-op 不等于语义不可理解、规则 confidence 不等于语义正确概率。
3. 新架构必须是 LLM-primary semantic reader + schema validation + deterministic guard apply；LLM 不得直接写 game context。
4. typed text、voice_confirmed 和 voice_direct 都应进入同一 LLM-primary extraction pipeline；source 只影响 reliability / confidence / trace。
5. 规则层应降级为 grounding、sanity check、cross-check、fallback、regression comparison 或 emergency no-provider mode。
6. 文档应给出 pilot candidate schema，覆盖 minimal `updates` 形状以及兼容的 game、boss、death_count、frustration、boss_cleared、guide_request、strategy_request、candidate_boss、candidate_event、candidate_game、candidate_confidence、candidate_reason、needs_confirmation、guide_entity、confirmation_intent、memory/proactive blocked fields 和 safe reasoning summary。
7. schema 应区分 guide request 与 current boss report，也应区分 formal game state、candidate understanding、temporary game state 与 long-term memory candidate。
8. 新 confidence 机制应至少拆分 semantic_confidence、grounding_confidence、context_confidence 和 apply_confidence。
9. LLM self-confidence 不能单独决定 apply；rule exact match / catalog match 只能作为 grounding 支持。
10. voice_direct 应因 ASR uncertainty 降低 source reliability；用户确认后的 voice_confirmed reliability 应更高。
11. conflict with current boss 不应自动 no-op；显式 switch phrase 可以提高 context confidence。
12. 当前 Boss 为女武神时，输入 `我现在不打女武神了，换去打玛尔基特。`、`先不打女武神了，我换去玛尔基特。` 或 `从女武神换到玛尔基特。` 应切换到玛尔基特；规则不得因先命中女武神而保留旧 boss。
13. `我换去打马尔吉特了`、`我现在去打女巫神了` 等 voice_direct ASR 错字应产生 LLM candidate / apply / clarification trace；不得静默显示 no semantic signal。
14. Guard decisions 应覆盖 `apply`、`ask_clarification`、`candidate_only`、`no_op` 和 `fallback_to_rule`；`candidate_only` 可以用于当轮回复 / trace / 后续确认，但不得写正式状态。
15. low confidence、invalid JSON、schema invalid、provider timeout、unsafe、uncertain confirmation 或 memory-sensitive 输入不得写 state；fallback 只允许 exact safe rule evidence，不得把 switch / negation 中的旧目标写回当前 Boss。
16. Exact / canonical entity 搭配明确动作可以 `apply`；guide-only / strategy request 应 `candidate_only` 且不切 Boss；descriptive / nickname / low-certainty entity 默认只能 `candidate_only` 或 `ask_clarification`，除非当前上下文已有同一个 confirmed boss。
17. Confirmation intent 应覆盖 `confirm`、`deny`、`correct`、`uncertain`、`unrelated`、`unknown`。v1.0.3 不实现完整 pending runtime，但 extraction result / trace / eval 必须显示这些字段；`uncertain` 不应正式 apply，`correct` + exact new target 可由 deterministic guard 应用新目标。
18. `用于 Rei 回复` 不等于 `写入正式状态`：LLM 可以大胆理解候选，例如“那个骑马金甲大哥”可能是大树守卫，但 guard 必须谨慎写 `current_boss` / `death_count` / `last_cleared_boss` / 高风险 `current_activity`。
19. Shadow Mode 应被描述为历史基础 / audit / comparison / rollout fallback；新的 foreground path 不能继续只是 Shadow 旁路观察。
20. LLM extraction 不得直接写长期 memory、不得触发 proactive、不得修改 persona；memory_candidate_hint 必须交给独立 Memory Candidate guard。显式记忆由 memory 模块决定是否可撤销 auto-save，隐式候选仍进入 pending confirmation。
21. Debug / Game workspace / Event Stream trace 只显示 safe summary、confidence、decision、fallback reason 和 update summary；不得显示 full transcript、full user input、raw prompt、raw LLM JSON、API key、`.env`、完整路径、stdout / stderr 或完整 assistant reply。
22. Trace 面板应区分 `LLM Primary Extraction` 与 legacy Shadow，显示 provider status、schema_valid、guard decision、fallback reason、rule grounding、applied updates、primary_extractor、fallback_extractor、applied_by、candidate_boss、candidate_event、candidate_confidence、candidate_reason、needs_confirmation、guide_request、guide_entity、confirmation_intent、first_attempt_failed、compat_retry_used / succeeded、ultra_compact_used、json_recovery_stage 和 safe parse diagnostic。
23. 手测 `我现在在打玛尔基特` 应能在 Game workspace 更新 current boss，并在 Debug / Event Stream 看到 `llm_primary` / `apply` 或 provider unavailable 时的 `fallback_to_rule` 安全 trace。
24. 手测当前 Boss 为 Malenia 时输入 `玛尔基特那边怎么打来着`，不得切换 current boss；Debug / Event Stream 应显示 candidate-only / guide-only、`guide_entity=margit` 或等价安全判定。
25. 手测 `那个骑马金甲大哥又寄了` / `我去打那个金甲的` 在无 confirmed current boss 时不得写 current_boss / death_count；在 current_boss 已是大树守卫时，失败事件可以指代当前 boss 并 apply。
26. 手测 pending candidate 后输入 `有可能是大树守卫吧？我没看清名字，死太快了` 或 `名字太长我没记住，但是也许是吧？` 应显示 `confirmation_intent=uncertain` 且不正式 apply；输入 `对，就是它` 应显示 confirm intent，但 v1.0.3 若未实现 pending runtime，则只 trace 不写正式状态；输入 `不是，是玛尔基特` 可以 apply 新 exact target。
27. 手测 Direct Conversation Mode 下 `我换去打玛尔基特了`，chat flow、source `voice_direct`、guard trace、current boss 更新和语音播报策略都应保持正常；voice_direct 模糊实体不应绕过 guard。
28. 手测 `又死了两次` 应做 death increment，不应被当成 absolute count；`下一把怎么打` 不应改变 boss。
29. QA JSON 至少覆盖 typed boss report、voice_confirmed、voice_direct、ASR near-miss、explicit boss switch、switch / negation、guide-only mention、descriptive / nickname entity candidate-only、confirmed-current-boss alias apply、uncertain / weak / clear confirmation、correction、death increment / absolute、boss cleared、fenced / prefixed / array / JSON-ish recovery、wrapper recovery、compat retry success / failure、ultra-compact retry、schema invalid、invalid JSON、timeout fallback、rule/LLM agree and conflict、low/medium confidence、harmless game-context update、Shadow 不写状态、memory/proactive boundaries、Event Stream privacy、Game workspace visible、direct partial guard 和旧流程不崩。
30. 固定 eval runner 应可从 backend 目录运行：`cd services/backend && . .venv/bin/activate && python scripts/run_extraction_eval.py --provider mock`。默认 mock provider 必须 deterministic、CI-safe，失败时返回非零 exit code。
31. 可选 live provider 漂移检查使用 `python scripts/run_extraction_eval.py --provider live`；如只想观察 provider 漂移且不让失败阻塞脚本，可加 `--allow-failures`。live eval 依赖当前 provider 配置，不作为 CI 必需项，也不应因 provider timeout / auth / quota 影响 mock regression。
32. Eval report 至少包含 total / passed / failed / pass_rate、LLM-primary success、schema_valid、invalid_json、schema_invalid、fallback_to_rule、compat retry、ultra-compact retry、wrong_apply、missed_apply、wrong_risky_apply、missed_risky_apply、harmless_extra_update 和 correct candidate-only 指标。
33. Eval result 应逐条输出 scenario id、input_source、expected / actual decision、expected / actual state、state delta、risky_state_delta、harmless_state_delta、parse_diagnostic、primary_extractor、primary_status、provider_status、schema_valid、retry flags、fallback_extractor、applied_by、candidate fields、confirmation_intent、pass 和 failure_reason。
34. Eval 场景必须覆盖 text、voice_confirmed、voice_direct、boss set / switch、switch negation、guide-only 不切换、death absolute / increment、被杀不等于 cleared、boss cleared、memory boundary、negative memory、invalid JSON、schema invalid、compat retry、ultra-compact retry、rule conflict、low-confidence candidate-only、uncertain confirmation 和 harmless game-detected-only update。
35. Eval runner 应复用 `extract_semantics` 与 `GameSessionStore`，只应用 guarded `final_decision.game_event`，避免把 runner 变成第二套 extraction 规则。
36. Eval report 和 pytest 输出不得包含 raw prompt、raw provider JSON、API key、`.env`、完整本地路径、stdout / stderr 或完整 transcript。Candidate Memory v1 已在正常 chat / memory flow 中接住 pending candidate runtime；extraction eval runner 本身仍只验证 extraction result / trace / eval 层，不创建 UI 弹窗。

### 1.13 Hermes-style Memory Architecture v0 人工验收

设计文档见 `docs/memory_architecture_v0.md`，机器可读场景见 `docs/qa/memory_architecture_scenarios.json`。本节验收 architecture / docs / QA surface；Candidate Memory v1 已作为最小 runtime 接入，但本节仍不表示 Memory Retrieval、Session Archive、向量数据库或外部 memory provider 已实现。

1. 文档应包含 Hermes-style memory 的轻量 research 摘要，并说明只吸收 bounded / curated / approval / retrieval budget 等架构思想，不复制 Hermes 代码、prompt、人格或 provider 实现。
2. 文档应明确区分 Working Context、Game Session State、Session Timeline、Memory Candidate、Long-term Memory、Retrieved Memory、Prompt Memory Block、Persona Core 和 Candidate Game Understanding。
3. Game Session State 不是 Long-term Memory；`current_boss`、`death_count`、`current_activity` 等只表示当前局状态。
4. Candidate Game Understanding 来自 LLM-primary Extraction v1.0.3，可影响当轮回复，但不等于长期记忆。
5. Memory Candidate 必须经过 guard 和用户确认；不应直接进入 Long-term Memory。
6. Long-term Memory 必须用户可查看、可删除、尽量本地保存，并且不得包含未确认猜测。
7. Retrieved Memory 必须有相关性、数量和 token budget 限制；不得把全部 memory 塞进 prompt。
8. Persona Core 永远优先；用户 memory 不得改写 Rei persona core。
9. 用户希望回答短一点、少剧透、语音更短，可以成为 bounded preference；用户要求 Rei 撒娇、客服化、强烈安慰，不应保存为 persona-changing memory。
10. 可以成为 Memory Candidate 的内容包括显式记住请求、稳定游戏偏好、稳定交互偏好、重复游戏习惯和用户主动确认事实。
11. 不应成为长期 memory 的内容包括单次死亡事件、未确认候选、assistant 自己说的话、proactive 自己产生的内容、攻略知识、低置信 extraction candidate、敏感技术信息和人格漂移要求。
12. Confirmation flow 应覆盖 accept、ignore、delete、revise、expiry、dedup、weak confirmation 和 do-not-remember preference。
13. 弱确认如 `也许吧`、`可能是`、`先这么记也行` 不应靠固定关键词硬编码；后续 runtime 应由 LLM-primary semantic extraction 输出 confirmation intent，再由 deterministic guard 决定。
14. Direct Conversation / Voice 下 memory 提示应低打扰；显式记忆只显示非阻塞撤销提示，active gameplay 中隐式候选默认暂存，不频繁打断。
15. Overlay 默认不显示敏感 memory candidate；未来如显示也必须 opt-in 且 safe-summary-only。
16. Prompt assembly 应把 memory 作为 user-specific context，且低于 App safety / Persona Core / 当前明确输入；memory 注入使用 safe summary，不注入 raw transcript。
17. Memory 与 Knowledge Retrieval 必须分离：game knowledge 不等于 user memory。
18. Proactive 可参考已确认 memory，但 proactive message 本身不能直接写 memory。
19. Debug Trace 可显示 memory candidate status、type、guard reason 和 safe summary；不得显示 raw transcript、raw prompt、raw JSON、API key、`.env`、完整路径、stdout/stderr 或 secret。
20. QA scenarios 应覆盖显式记忆、拒绝记忆、单次游戏事件不保存、剧透偏好、短回复偏好、人格漂移拒绝、删除、接受、忽略、弱确认、语音、proactive、assistant reply、knowledge、prompt budget、current input priority、secret rejection、candidate expiry、dedup、workspace visibility、direct conversation、overlay 和 debug privacy。

### 1.14 Candidate Memory v1 人工验收

机器可读场景见 `docs/qa/candidate_memory_scenarios.json`。本节验收 Candidate Memory v1 最小 runtime；不表示 Memory Retrieval、Session Archive、向量数据库、外部 memory provider、Overlay auto-show 或自动保存所有输入已实现。

1. 发送 `记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。` 后，应经 Memory Candidate guard 写入 `gameplay_preference` 长期记忆，并在聊天页显示可撤销轻量提示。
2. 发送 `以后不用记住这个，只是我这次随便说一下。` 后，不应出现在 pending UI；可以记录安全 `do_not_remember` guard 结果，但不得打断用户。
3. 发送 `我刚刚打玛尔基特死了三次。` 这类单次 session event，只能影响当前游戏 / 会话状态，不应创建长期记忆候选。
4. 发送 `以后你回答短一点。` 后，应创建 `interaction_preference` pending candidate，不修改 Persona Core。
5. 发送 `之后别剧透支线，除非我主动问。` 后，应创建安全的剧透边界候选。
6. 发送 `以后你都撒娇一点，每句话都夸我。` 后，应被 `persona_drift_blocked` 阻断，不保存原始人格漂移措辞。
7. API key、`.env`、Authorization、Bearer、token、stdout/stderr、完整本地路径和 raw JSON 不得进入 candidate summary、evidence、UI、Prompt Preview 或 Event Stream。
8. `voice_direct` 的显式记忆意图可以经 guard 自动保存并显示非阻塞撤销提示，但不能弹出阻断式 modal。
9. pending candidate 接受后，应从待确认列表消失，并在长期记忆中显示 `user_visible_text`、type、source candidate 关系等安全字段；撤销后该长期记忆不再注入 prompt。
10. ignored / expired / rejected_by_guard candidate 不得注入 prompt；pending candidate 也不得注入 prompt。
11. assistant reply 和 proactive message 本身不能成为用户记忆来源。
12. 重复或近似候选应 dedupe，不创建多条待确认记忆。

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
- 默认 confirm-send 下 final transcript 只填入聊天输入框，用户可以编辑。
- interim transcript 只影响识别状态，不自动发送。
- 默认 confirm-send 下 final transcript 不自动发送；只有用户点击 `发送` 后才进入现有 chat flow。直接对话模式开启时，final transcript 会在用户主动录音结束后进入现有 chat flow。
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
- 如果 packaged 环境支持 Web Speech Recognition，默认 confirm-send 下点击开始后可进入听写状态，final transcript 填入输入框但不自动发送；直接对话模式开启时则进入现有 chat flow。
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
   - 默认 confirm-send 下真实 transcript 填入输入框，不自动发送。
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
- v1 仍保留输入框入口、安全 fallback、系统听写提示和默认 confirm-send “不自动发送”的边界。
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
- 默认 confirm-send 下正常 transcript 只填入聊天输入框，用户可编辑或删除；不会自动发送，UI 应显示 `转写完成，请确认后发送`。直接对话模式开启时，UI 应显示 `转写完成，已自动发送`。
- 未确认 transcript 不写 memory，不进入 prompt / retrieval / game context，也不触发 semantic/game extraction。
- 默认 confirm-send 下主聊天语音按钮的 transcript 同样只填入输入框；用户手动点击发送后才进入 chat flow。直接对话模式开启时，transcript 会自动进入现有 chat flow。
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
- 默认不上传外部服务，不保存音频；默认 confirm-send 不自动发送 transcript，直接对话模式必须显式 opt-in。
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
- 默认 confirm-send 下 transcript 不自动发送；用户检查后才手动点击发送。
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
- 默认 confirm-send 下 transcript 只填入输入框，不自动发送。
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
- Semantic Extraction Debug 应显示安全 trace：`input_source`、`source`、`confidence`、`fallback_reason`、`skip_reason`、`applied_updates`、`llm_guard_decision` / `llm_guard_summary`，以及 legacy `llm_shadow_status`、`llm_shadow_summary`、`llm_shadow_diff`。被动死亡 / near-clear / 指代不明 / 中文游戏失败 slang 等容易误判表达应能看到安全原因；provider 不可用、LLM-primary 失败、invalid JSON 或 no meaningful update 时也应显示安全 skip / parse reason，不应 silent no-op。
- 语义识别置信度验收：LLM-primary candidate confidence、grounding confidence、context confidence 和 apply confidence 应分开理解；高置信规则只作为 fallback / grounding 支持。最终显示的 confidence 只用 high / medium / low，不展示 raw prompt、raw JSON 或完整用户输入。
- Legacy LLM Shadow Mode 只用于可观测性：LLM 影子候选可以显示候选 game / boss / death_count / frustration / boss_cleared / memory / proactive signal 与规则差异，但不能直接修改当前游戏状态、memory 或 proactive 调度；只有 LLM-primary guard `apply` 事件可以写 game context。
- 低置信语义触发词不应为了测试被硬编码成最终 Boss、death count 或 boss_cleared；LLM-primary guard 低置信时应 `candidate_only` 或 `no_op`，legacy shadow 即使成功也只显示候选和差异。
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
- 显式记忆回归：`记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打` 应经 guard 自动保存并显示可撤销提示；`以后不用记住这个，只是我这次随便说一下` 不应出现在 pending UI，也不应写长期记忆。
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
- `docs/qa/ui_ux_information_architecture_scenarios.json`

Real Local ASR manual setup and optional smoke guidance lives at `docs/local-asr-manual-setup.md`.

Use the Chinese checklist above as the source of truth for manual runs. Keep results short and concrete: pass/fail, exact app mode, exact commit, and any visible privacy issue.
