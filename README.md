# ReiLink

> 本地优先的 AI 游戏陪伴 Agent 桌面应用。

简体中文 | [English](README.en.md)

[![Status](https://img.shields.io/badge/status-pre--release-6b5cff)](docs/PROJECT_STATUS.md)
[![Platform](https://img.shields.io/badge/platform-macOS-111827)](#快速开始)
[![Desktop](https://img.shields.io/badge/desktop-Electron-47848f)](https://www.electronjs.org/)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Language](https://img.shields.io/badge/language-TypeScript%20%2F%20Python-3178c6)](#架构概览)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

ReiLink 是面向单机游戏玩家的中文 AI 游戏陪伴运行时。它把当前游戏状态、玩家对话、已确认记忆、本地知识包、语音输入输出和调试事件放在同一个桌面应用里，让 companion 在游戏时提供低打扰、上下文相关、克制的回应。

ReiLink 不是通用 chatbot，也不是攻略站。最终回复仍由 persona + LLM 生成；game context、memory 和 knowledge layer 只提供辅助上下文。当前 companion persona 是原创 Rei-like minimal 风格，不使用 Evangelion、Rei Ayanami、NERV 或任何官方 IP 元素。

## 目录

- [ReiLink 是什么](#reilink-是什么)
- [当前状态](#当前状态)
- [核心亮点](#核心亮点)
- [功能矩阵](#功能矩阵)
- [架构概览](#架构概览)
- [Agent 回答链路](#agent-回答链路)
- [Voice Interaction v2.2](#voice-interaction-v22)
- [Knowledge Retrieval / 本地知识检索](#knowledge-retrieval--本地知识检索)
- [Local-first 与隐私边界](#local-first-与隐私边界)
- [快速开始](#快速开始)
- [Local ASR 配置](#local-asr-配置)
- [打包与运行时说明](#打包与运行时说明)
- [文档入口](#文档入口)
- [路线图](#路线图)
- [已知限制](#已知限制)
- [License](#license)

## ReiLink 是什么

很多游戏 companion 容易落到两个极端：要么只是普通聊天机器人，要么只是静态攻略查询。ReiLink 想探索中间地带：

- 玩家始终掌控输入、发送和记忆写入；
- companion 保持低情绪、低打扰、短句风格；
- 本地知识只在相关时提供事实上下文，不把回复变成 wiki dump；
- 记忆必须经过用户确认；
- 语音输入默认是 transcript-first 确认发送；用户显式开启 Direct Conversation 后，主动录音通过 guard 才会自动发送；
- 用户数据、设置、知识包和音频处理尽量保留在本机。

当前项目面向本地演示、作品集展示和 runtime / product iteration，不是正式商业安装包。

## 当前状态

- 当前开发里程碑：**Voice v2.2 release hardening**。
- `dev/codex-reilink` 分支包含最新 Voice / Local ASR / Knowledge Retrieval / Context & Memory 进展。
- 当前开发线已完成：Voice v2.2（confirm-send、Direct Conversation、Voice Profile、TTS Strategy / Provider Registry）、Local ASR、Knowledge Retrieval、Candidate Memory、Memory Retrieval、Session Archive Runtime、Archive Search 与 Archive-to-Memory Candidate Bridge。
- 公开 release tag 可能滞后于当前 dev 分支；GitHub 更新、release tag、push、merge 仍需要人工 review 后进行。
- macOS packaged app 已做多轮 smoke，但项目仍处于 pre-release。

详细状态见 [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)。

## 核心亮点

- 中文优先的 AI companion chat，原创 minimal persona。
- [DeepSeek](https://api-docs.deepseek.com/) compatible provider 与 `fast` / `pro` / `auto` 模型路由。
- Confirmable Memory：长期记忆只在用户接受后写入。
- Context & Memory System：Candidate Memory、已确认记忆检索、Persona-Memory Eval、Session Archive safe summaries、Archive Search 和显式 Archive-to-Memory Candidate Bridge。
- Game Context：当前游戏、Boss、进度、挫败状态和手动当前游戏覆盖。
- 本地知识包：包含 [Elden Ring sample knowledge](data/knowledge/games/elden_ring) 与 [Hollow Knight sample knowledge](data/knowledge/games/hollow_knight)。
- Knowledge Retrieval v1：本地 keyword retrieval、top-k snippets、grounding / gating、显式游戏名切换和闲聊隔离。
- Voice v2.2：默认 confirm-send、显式 Direct Conversation、九态状态机、Voice Profile full / brief / silent、可打断系统 TTS 与安全 Event Stream 生命周期摘要。
- Voice Input：用户配置 [whisper.cpp](https://github.com/ggerganov/whisper.cpp) compatible binary、model 和 [ffmpeg](https://ffmpeg.org/) compatible converter 后走 Local ASR；不接 cloud ASR。
- Event Stream / Debug Panel：展示安全摘要，不展示 raw prompt、API key、完整路径或完整 transcript。
- macOS packaged app runtime foundation：bundled backend binary、bundled knowledge resources、用户数据写到 app 外部。

## 功能矩阵

| 范围 | 能力 | 状态 | 说明 |
| --- | --- | --- | --- |
| Persona | 原创 minimal companion | MVP | 原创 Rei-like persona，不使用官方 IP。 |
| Dialogue | LLM-first 回复生成 | 已完成 | Game context / memory / knowledge 只提供上下文。 |
| Memory | Candidate / Retrieval / Archive | 已完成 | 只有 accepted / active 长期记忆会进入 prompt；archive 不直接进入 prompt。 |
| Game Context | Boss / deaths / frustration / session | MVP | Rule-first，必要时结合 LLM semantic fallback。 |
| Knowledge Retrieval | 本地 keyword retrieval | MVP | 暂无 embeddings / vector DB / hybrid retrieval。 |
| Session Archive | 最近会话 safe summary | MVP | 手动归档、搜索、删除、清空和显式候选扫描；不保存 raw prompt / transcript。 |
| Voice Interaction | confirm-send + Direct Conversation | v2.2 | Direct Conversation 需显式开启且每轮主动录音；不是 hands-free。 |
| Voice Output | System Speech Synthesis + Voice Profile | v2.2 | full / brief / silent；唯一 selectable provider 是系统语音，不是角色级配音。 |
| Voice Input | Local ASR | MVP | 需要用户手动配置 binary / model / converter；音频只交给本机 backend。 |
| Event Stream | 安全生命周期事件 | 已完成 | 不显示 raw prompt、API key、完整路径、完整 transcript。 |
| Packaging | macOS `.app` | MVP | 用户数据写在 `.app` 外部；当前为未签名本地构建。 |
| Overlay | macOS safe mode | MVP / 冻结 | Foundation 已有；auto-show 故意 fail-closed。 |
| Live2D | Avatar layer | 计划中 | 尚未实现。 |
| Embedding / Hybrid RAG | Vector / hybrid retrieval | 计划中 | 当前 retrieval 是 keyword-based。 |

## 架构概览

ReiLink 使用 [Electron](https://www.electronjs.org/) desktop shell、[React](https://react.dev/) / [TypeScript](https://www.typescriptlang.org/) / [Vite](https://vite.dev/) renderer，以及本地 [FastAPI](https://fastapi.tiangolo.com/) backend。packaged app 通过 [PyInstaller](https://pyinstaller.org/) 打包 backend binary。下方图表使用 [Mermaid](https://mermaid.js.org/)，可在 GitHub README 直接渲染。

```mermaid
flowchart LR
  Player["玩家"] --> UI["React Renderer<br/>聊天 / 设置 / 调试"]
  UI --> Events["Event Bus<br/>安全事件摘要"]
  UI --> VoiceOut["Voice Output<br/>系统 TTS"]
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
    ASR --> TempAudio["Temporary Audio Files<br/>默认处理后清理"]
    ASR --> Converter["Audio Converter<br/>ffmpeg-compatible"]
    ASR --> Whisper["Local ASR Binary<br/>whisper.cpp-compatible"]
  end

  Retrieval --> Packs["Bundled Knowledge Packs"]
  Memory --> UserData["Local User Data"]
  UserData --> ASRSettings
  Router --> DeepSeek["DeepSeek-compatible API"]

  Packs -. "只读资源" .-> Runtime
  UserData -. "本地保存" .-> Runtime
```

Renderer 负责用户交互、语音录制、Voice 状态、系统 TTS 和安全事件展示。Backend 负责 Agent runtime、knowledge retrieval、memory、game context、model routing、Local ASR subprocess 边界和用户数据目录。Local ASR settings 保存在 Local User Data 中；每轮录音只交给本机 backend，temporary audio 默认在处理后清理。默认模式下 transcript 只回填输入框；显式 Direct Conversation 仅在用户主动录音、主动停止且 guard 通过后进入同一 chat flow。未确认或被 guard 阻断的 transcript 不进入 memory、prompt、knowledge retrieval、game context、Semantic Extraction 或 proactive。Local-first 指本地用户数据、本地记忆、本地设置、本地知识包、音频处理和 Local ASR 优先保存在本机；LLM 推理目前仍可通过用户配置的 DeepSeek-compatible provider 完成。

## Agent 回答链路

ReiLink 的一次回复不是“用户消息直接丢给 chatbot”。它会先整理游戏上下文、记忆候选、本地知识和模型路由，再组装 prompt。

```mermaid
flowchart TD
  U["用户消息"] --> GC["游戏上下文提取"]
  U --> MC["记忆候选检测"]
  U --> KR["本地知识检索"]

  GC --> CTX["当前回合上下文"]
  MC --> PM["待确认记忆<br/>用户 accept 后才写入"]
  KR --> KG["Top-k 本地知识片段"]

  Persona["Persona"] --> Prompt["Prompt 组装"]
  LongMemory["Confirmed Memory<br/>长期记忆"] --> Prompt
  CTX --> Prompt["Prompt 组装"]
  KG --> Prompt
  Prompt --> Router["模型路由<br/>fast / pro / auto"]
  Router --> LLM["DeepSeek-compatible Provider"]
  LLM --> Reply["Rei 回复"]

  Reply --> UI2["聊天界面"]
  Reply --> TTS["可选语音输出"]
  Reply --> ES["Event Stream<br/>安全摘要"]

  PM -. "用户确认后" .-> LongMemory
```

Prompt 会同时使用 persona、confirmed memory、当前回合上下文和相关 knowledge snippets。Memory 不会自动写入；knowledge 只有相关时注入；闲聊不会强行触发 retrieval；Event Stream 只展示安全摘要。

## Voice Interaction v2.2

Voice v2.2 是用户主动触发的语音对话基础层，不是完整实时语音 Agent。默认仍是 `confirm_send`；Direct Conversation 必须显式开启，而且每一轮都需要用户主动录音，不会常驻监听，也没有 wake word。

### Voice Input / Local ASR

- Local ASR 是当前稳定主路径，Web Speech 只作环境允许时的 fallback。
- 用户在 Settings 配置 ASR binary、model 和 converter；ReiLink 不内置这些第三方文件。
- 主聊天使用浏览器 `MediaRecorder`，没有 Web Audio VAD 或 silence detection，也不再在旧的 3 秒 / 5 秒边界自动结束。用户主动停止是主路径，30 秒只是安全上限；独立 Audio Capture Probe 仍保留 3 秒探测。
- Stop 后先进入 capture `stopping`，等待最终 `dataavailable` / `onstop`，再构造完整 Blob、交给本机 backend 转写并清理临时文件；结束原因是 `user_stop`、`max_duration`、`cancelled` 或 `error`。
- `confirm_send`：transcript 进入可编辑输入框，用户可以修改、清空或重新录音；发送前不代表 LLM 已理解，也不运行 Semantic Extraction 或更新 Game Context、Memory、Boss。
- `direct_conversation`：每轮仍由用户主动录音。Local ASR 只有 `user_stop` 且 quality 为 `acceptable` 才可自动发送；Web Speech final transcript 没有 MediaRecorder stop reason，但仍通过其余文本 guard。空文本、少于 4 个 lexical 字符、短于 800 ms 的 Local ASR 录音、30 秒上限、纯 caption / speaker label / stage direction、常见疑似半句和明显可疑输出都会阻止自动发送。关闭 Direct Conversation 后，本轮完成时会退回 confirm-send。
- 未确认或被 guard 阻断的 transcript 不写 memory、不触发 proactive，也不进入 prompt、retrieval、game context 或 Semantic Extraction。
- 当前 Local ASR 不向 renderer 提供 no-speech probability、segment confidence 或 average log probability；ReiLink 不虚构这类 confidence。

### State / Direct Conversation

当前状态统一为 `idle`、`listening`、`transcribing`、`auto_sending`、`ready_to_send`、`assistant_thinking`、`speaking`、`interrupted` 和 `error`。录音与播报互斥；开始新录音或点击 Stop Voice 会尽量打断当前播报。

### Voice Output / Profile

- 当前唯一 enabled / selectable provider 是 `system_speech_synthesis`，由平台 `speechSynthesis` 提供能力。
- Local TTS 是 `not_implemented` placeholder；External TTS 是 disabled / `not_configured` placeholder，均不可选择。
- Voice Profile `rei_calm` 默认普通聊天 `full`、Direct Conversation `brief`，也支持 `silent`；brief 是 deterministic 截取，不额外调用 LLM。
- `silent` 只关闭自动播报，完整文字回复仍保留。Test Voice 是独立的显式操作，不等同于自动回复播报。
- ReiLink 不接外部 TTS API、不配置 TTS API key；平台 `speechSynthesis` 的内部实现由操作系统 / runtime 决定。

```mermaid
sequenceDiagram
  participant User as 用户
  participant UI as Renderer
  participant Backend as 本机 Backend
  participant ASR as Local ASR
  participant Chat as 现有 Chat Flow

  User->>UI: 主动开始录音
  User->>UI: 主动停止，或达到 30 秒安全上限
  UI->>UI: stopping，等待最终 dataavailable / onstop
  UI->>Backend: 本机传递完整音频 Blob
  Backend->>ASR: 本地转写
  ASR-->>UI: transcript
  alt confirm_send
    UI->>UI: 填入输入框，等待确认
    User->>Chat: 确认发送
  else direct_conversation 且 guard 通过
    UI->>Chat: 自动发送
  else guard 阻断
    UI->>UI: 等待确认或提示重试
  end
  Chat-->>UI: 文字回复
  opt Voice Output 开启且 profile 非 silent
    UI->>UI: 系统语音播报，可停止
  end
```

Voice / TTS Event Stream 只保留类型、来源 / mode、provider / status / profile、capture duration、音频格式安全摘要、stop reason、quality、send decision、guard reason 和长度等安全元数据，不保留完整 transcript、raw ASR output、raw audio、assistant reply、spoken text、raw prompt、provider raw config、凭据、完整本地路径或 raw stderr。详细规格见 [`docs/voice_interaction_v2_spec.md`](docs/voice_interaction_v2_spec.md)，发布门禁见 [`docs/release_voice_v2_2_hardening_checklist.md`](docs/release_voice_v2_2_hardening_checklist.md)。

## Knowledge Retrieval / 本地知识检索

当前 retrieval 是本地 keyword retrieval，不是 embedding / vector search。

- 支持 sample packs：Elden Ring / 艾尔登法环、Hollow Knight / 空洞骑士。
- 状态包括 `used`、`not_found`、`below_threshold`、`no_pack`、`not_game_related`。
- grounding / gating 会阻止低相关知识注入 prompt。
- 闲聊不会强行注入 knowledge。
- 无 Game Context 时，通用 `探索` 等 topic alias 不再独立启动 canonical game；只有更可靠的 Boss / location 实体 alias 可作为 bounded bootstrap 证据。噪声转写不会因此误切到空洞骑士，正确 `史东薇尔` 仍可识别艾尔登法环，明确的“我现在换去玩空洞骑士”仍可切换。
- 用户显式游戏名优先于 current game context。

知识包位于 [`data/knowledge/games`](data/knowledge/games)，新增知识包规范见 [`docs/KNOWLEDGE_PACK_AUTHORING.md`](docs/KNOWLEDGE_PACK_AUTHORING.md)。

## Local-first 与隐私边界

- 本地 memory、session、settings、logs 写入用户数据目录，不写入 packaged app resources。
- packaged app 用户数据目录：`~/Library/Application Support/ReiLink/data`。
- Local ASR settings 示例路径：`~/Library/Application Support/ReiLink/data/local_asr_settings.json`。
- API keys 和本地环境文件不会打包进 `.app`。
- Pending memory 必须由用户确认。
- Session Archive 只保存 safe summaries；Archive Search 不进 prompt，Archive-to-Memory Bridge 只创建待确认候选。
- Local ASR 音频是短时临时文件，处理后清理。
- Voice / TTS Event Stream 不保存完整 transcript、assistant reply 或 spoken text；Debug / Raw JSON 也不展示 raw prompt、raw subprocess output、API key、Authorization、完整本地路径、audio content 或 base64 audio。
- Local-first 指本地数据、本地设置、本地知识包和本地 ASR 优先留在本机；不代表当前所有 LLM 推理都离线。

## 快速开始

### 1. 环境要求

- macOS：当前 packaged app 路径以 macOS 为主。
- Python backend 环境。
- Node.js / npm desktop 环境。
- 可选：真实 LLM provider 凭据。
- 可选：Local ASR 所需 whisper.cpp-compatible binary、model file、converter。

### 2. Backend / Desktop 开发模式

```bash
make install-backend
make install-desktop
make doctor
make dev-backend
make dev-desktop
```

`make dev` 不管理长进程；请分别启动 backend 和 desktop。

### 3. Provider 配置

在本地 backend 环境配置 LLM provider。不要提交真实 key 或本地环境文件。无 key 本地演示可使用 `LLM_PROVIDER=mock`。

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/setup/status
```

### 4. 可选 Local ASR 配置

真实 Local ASR 需要用户自行准备本地工具，并放在 repo 和 packaged app 外部：

- whisper.cpp-compatible CLI binary
- compatible local model file
- 用于 browser WebM / Ogg 录音的 ffmpeg-like converter

然后在 Settings -> Voice Input -> `本地 ASR 配置 / Local ASR Setup` 中填入路径。详细步骤见 [`docs/local-asr-manual-setup.md`](docs/local-asr-manual-setup.md)。

### 5. 打包

```bash
make package-backend
make package-desktop
```

本地未签名 macOS app 会生成在 `apps/desktop/release/ReiLink-darwin-<arch>/ReiLink.app`。

## Local ASR 配置

配置优先级：

1. Settings 用户配置。
2. Local ASR 环境变量 fallback。
3. 未配置安全 fallback。

Settings API 只返回 configured booleans、source 和 basename；完整路径只保存在本地配置文件中，或出现在用户主动编辑的输入框中。ReiLink 不内置、不自动获取，也不会随项目提供 whisper binary、model、ffmpeg 或第三方可执行文件。

## 打包与运行时说明

packaged app backend 优先级：

1. `127.0.0.1:8000` 上健康的外部 backend。
2. 用户配置的 backend binary。
3. `.app` 内 bundled backend binary。
4. dev 模式下 repo-local fallback。

packaged resources 是只读资源。memory、session、settings、logs 和 Local ASR settings 都保存在 `.app` 外部。当前 macOS app 是本地未签名构建，不包含 installer、notarization、auto updater 或 Windows / Linux 打包。

## 文档入口

| 文档 | 用途 |
| --- | --- |
| [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) | 当前项目状态与范围。 |
| [`docs/QA.md`](docs/QA.md) | 手动 QA 与 release regression checklist。 |
| [`docs/release_voice_v2_2_hardening_checklist.md`](docs/release_voice_v2_2_hardening_checklist.md) | 当前 Voice v2.2 自动化、手动与 packaged release gate。 |
| [`docs/releases/reilink-voice-v2.2.md`](docs/releases/reilink-voice-v2.2.md) | Voice v2.2 release note 草稿。 |
| [`docs/voice_interaction_v2_spec.md`](docs/voice_interaction_v2_spec.md) | 当前 Voice v2.2 状态机与 Direct Conversation 规格。 |
| [`docs/voice_profile_v1.md`](docs/voice_profile_v1.md) | 当前 full / brief / silent 播报策略。 |
| [`docs/tts_provider_registry.md`](docs/tts_provider_registry.md) | 当前 TTS provider 能力与 placeholder 边界。 |
| [`docs/qa/voice_v2_2_release_matrix.json`](docs/qa/voice_v2_2_release_matrix.json) | Voice v2.2 release gate 到 component QA / 自动化测试的机器可读映射。 |
| [`docs/release_context_memory_hardening_checklist.md`](docs/release_context_memory_hardening_checklist.md) | Context & Memory release hardening checklist。 |
| [`docs/releases/reilink-v0.2-pre.4-context-memory.md`](docs/releases/reilink-v0.2-pre.4-context-memory.md) | Context & Memory v0.2-pre.4 release notes 草稿。 |
| [`docs/memory_architecture_v0.md`](docs/memory_architecture_v0.md) | Memory 分层、Candidate Memory、Retrieval 和 archive bridge 边界。 |
| [`docs/session_archive_v1_architecture.md`](docs/session_archive_v1_architecture.md) | Session Archive / Search / Archive-to-Memory Bridge 架构。 |
| [`docs/local-asr-manual-setup.md`](docs/local-asr-manual-setup.md) | 真实 Local ASR 配置与 smoke flow。 |
| [`docs/voice-input-local-asr-spike.md`](docs/voice-input-local-asr-spike.md) | Historical Local ASR spike；当前状态以 Voice v2.2 spec 为准。 |
| [`docs/release-notes/reilink-voice-mvp.md`](docs/release-notes/reilink-voice-mvp.md) | Historical Voice MVP release note；已被 v2.2 草稿取代。 |
| [`docs/qa/retrieval_scenarios.json`](docs/qa/retrieval_scenarios.json) | Knowledge Retrieval 机器可读回归场景。 |
| [`docs/qa/voice_input_scenarios.json`](docs/qa/voice_input_scenarios.json) | Voice Input fallback 机器可读回归场景。 |
| [`docs/qa/voice_input_local_asr_scenarios.json`](docs/qa/voice_input_local_asr_scenarios.json) | Local ASR release regression 场景。 |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | 常见启动和运行问题。 |

## 路线图

### v0.2 Runtime Foundation

当前开发线已基本完成该阶段的 MVP 能力。

- Voice Output MVP。
- Local ASR Voice Input MVP。
- Knowledge Retrieval v1。
- Candidate Memory v1 / Memory Retrieval v1。
- Session Archive Runtime / Search / Archive-to-Memory Candidate Bridge。
- Event Stream / Debug privacy guardrails。
- Packaged app runtime foundation。

### v0.2.x Stabilization

- Context & Memory release hardening。
- Voice v2.2 release hardening 与 QA consolidation。
- Packaged app smoke coverage for user-visible runtime changes。
- Local ASR setup helper and accuracy / timeout tuning。
- More robust QA regression flows。

### v0.3 Gameplay Presence

- Overlay v1。
- 更好的游戏会话感知。
- 低打扰 proactive companion display。

### v0.4 Character Presence

- Live2D avatar layer。
- Character state machine。
- 更自然的本地角色 TTS 探索。

### Later

- Embedding / hybrid retrieval。
- More games and richer knowledge packs。
- Installer / updater。

## 已知限制

- Pre-release / portfolio-oriented project。
- macOS-first。
- 还没有 installer、code signing、notarization 或 auto updater。
- 没有 cloud account / sync。
- 不内置 whisper binary、model、ffmpeg 或第三方可执行文件。
- 系统 TTS 可能不够自然，也不是角色级配音。
- Local ASR 准确率取决于模型大小、麦克风、环境噪音和硬件性能。
- Local ASR 可能丢失标点、改变措辞或误识别游戏专有名词、中文长句、口音和噪声；当前也没有可供 renderer 使用的 no-speech probability、segment confidence 或 average log probability。
- Direct Conversation 的半句判断是有限启发式、只能 best-effort；少量表面完整的未完成口语仍可能通过。纯括号包裹的真实自然语言也可能被 caption guard 保守阻止，但可以编辑后手动发送。需要严格控制时应使用默认 `confirm_send`。
- Voice v2.2 不是 hands-free / always-listening Agent；不做 wake word、speaker diarization 或自动下一轮录音。
- 尚未实现 local neural TTS、external / streaming TTS provider、custom character voice、voice cloning 或 cloud audio upload。
- Overlay auto-show 仍处于 macOS fail-closed safe mode。
- 还没有 Live2D。
- 还没有 embedding / vector DB / hybrid retrieval、semantic archive search、prompt archive retrieval 或外部 memory provider。
- 知识包仍是 samples，不是完整攻略库。
- 当前 packaged app 是本地未签名开发构建。

## License

MIT License. See [LICENSE](LICENSE).
