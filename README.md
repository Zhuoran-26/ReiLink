# ReiLink

## 中文

### 项目简介

ReiLink 是一个面向单机游戏玩家的中文 AI Companion 桌面应用。它会结合当前游戏、玩家对话、临时游戏状态、已确认记忆偏好和本地知识包，让一个 Rei-like 的原创低情绪陪伴角色用克制、简短的中文与玩家互动。

ReiLink 不是通用 chatbot，也不是纯攻略站。它更接近一个带有游戏上下文的陪伴层：由 AI companion、game context（游戏上下文）、memory（记忆）和 knowledge layer（知识层）共同组成，但最终回复仍保持 LLM-first，由 persona 与模型生成。

声明：本项目不使用 Evangelion、Rei Ayanami、NERV 或任何官方 IP 元素。

### 状态

Status: MVP / Pre-release。

当前公开预发布版本：v0.2-pre（`reilink-v0.2-pre`）。MVP v0.1.1（`reilink-mvp-v0.1.1`）仍是早期公开展示基线；当前开发继续在 `dev/codex-reilink` 上做 runtime / product foundation 补齐。

当前版本适合本地演示、作品集展示和代码审阅。它不是完整商业发布版本，也不包含安装器、云端账号、支付系统或复杂部署流程。

Rei 是原创 companion persona。项目不隶属于 Evangelion、FromSoftware、Team Cherry 或相关权利方。Elden Ring / Hollow Knight 仅作为本地 sample knowledge context 展示多游戏知识接口；相关名称与商标归各自权利方所有。

### 截图展示 / Screenshots

#### 主聊天界面 / Main Companion Chat

![Main Chat](docs/assets/reilink-main-chat.jpeg)

![Companion Chat](docs/assets/reilink-companion-chat.jpeg)

#### 可确认记忆 / Confirmable Memory

![Pending Memory](docs/assets/reilink-pending-memory.jpeg)

#### 游戏状态 / Game Session State

![Game Session](docs/assets/reilink-game-session.jpeg)

#### 多游戏知识库 / Multi-game Knowledge

![Elden Ring Knowledge](docs/assets/reilink-knowledge-elden-ring.jpeg)

![Hollow Knight Knowledge](docs/assets/reilink-knowledge-hollow-knight.jpeg)

#### 未支持游戏兜底 / Unsupported Game Fallback

![Knowledge Fallback](docs/assets/reilink-knowledge-fallback.jpeg)

#### 主动陪伴 / Proactive Companion

![Proactive Companion](docs/assets/reilink-proactive.jpeg)

#### 回复上下文与调试 / Context Preview and Debug

![Context Preview](docs/assets/reilink-context-preview.jpeg)

![Debug Panel](docs/assets/reilink-debug-panel.jpeg)

### 功能介绍

- 中文 AI companion chat（中文陪伴聊天）
- Rei-like original minimal persona（原创 minimal 人格）
- DeepSeek provider（DeepSeek 模型提供方）
- Model routing（模型路由）：`fast` / `pro` / `auto`
- Multi-part replies（分段回复）
- Pending memory confirmation（待确认记忆）
- Game session state（游戏会话状态）
- Semantic extraction（语义识别）
- Proactive companion trigger（低频主动陪伴触发）
- Local game detection（本地游戏检测）
- Manual game context override（手动当前游戏覆盖）
- Multi-game knowledge catalog（多游戏知识目录）
- Knowledge pack manifest（知识包清单）
- Knowledge Retrieval（本地关键词检索、grounding / gating 与显式游戏名切换）
- Elden Ring 与 Hollow Knight sample knowledge packs（样例知识包）
- Voice Output（语音输出、Test Voice、语速与音量）
- Voice Input v1 fallback（push-to-talk Web Speech fallback，不自动发送）
- Local ASR v1（Settings 手动配置、本地录音转写、主聊天语音按钮接入、transcript 不自动发送）
- Event Stream（安全事件流摘要）
- Debug dashboard（调试面板）
- Prompt / context preview（回复上下文预览）
- Settings panel（设置面板）
- Local-first memory and session state（本地优先的记忆与会话状态）
- Standalone App Packaging v1（独立应用本地打包 v1）
- Bundled backend binary 与 bundled knowledge resources（内置后端 binary 与知识资源）
- Local Data Controls（本地数据查看、打开目录与安全重置入口）

### Voice Interaction MVP / 语音交互 MVP

ReiLink 当前的 Voice Interaction MVP 是“可选语音输出 + 用户确认式本地语音输入”，不是完全自然语音助手。

- Voice Output：使用本机系统 `speechSynthesis`，默认关闭；支持 Test Voice、语速、音量、Stop Voice 和安全 Event Stream 生命周期摘要。
- Voice Input：Web Speech 只作为 fallback；稳定主路径是用户在 Settings 手动配置本地 whisper.cpp-compatible binary、model 和 converter 后，由 Local ASR 录音转写。
- Transcript-first UX：识别文本只填入聊天输入框，用户可编辑或删除；只有用户手动点击发送后才进入 chat flow、memory、prompt、knowledge retrieval 或 game context。
- Privacy：不使用云 ASR，不默认保存音频，不内置或下载 whisper binary、model、ffmpeg，也不把完整路径、完整 transcript、raw subprocess output、API key 或 `.env` 放进 Debug / Event Stream / Raw JSON。

### 技术栈

Backend:

- Python
- FastAPI
- JSON / JSONL local state
- DeepSeek-compatible provider

Desktop:

- Electron
- React
- TypeScript
- Vite

Tests:

- pytest
- Vitest
- React Testing Library
- Playwright

### 架构概览

主要 backend 模块：

- `persona_engine`：加载 persona 配置并构建系统提示。
- `dialogue_agent`：编排设置、游戏状态、知识、模型路由、provider 调用和 debug 数据。
- `game_session`：维护当前游戏、Boss、进度和临时状态。
- `memory`：维护待确认记忆和已接受长期记忆。
- `semantic_extraction`：从用户消息中识别游戏状态和记忆候选。
- `game_knowledge` / `knowledge`：基于 catalog 与 snippets 提供事实上下文。
- `game_detector`：本地进程 / 应用名检测当前游戏。
- `proactive`：低频主动陪伴触发与冷却控制。
- `app_settings`：持久化用户设置。

主要 desktop 区域：

- Chat UI（聊天）
- Settings（设置）
- Pending Memory（待确认记忆）
- Game Session / Game Context Debug（游戏状态与上下文）
- Prompt Preview（回复上下文预览）
- Knowledge Debug（知识层调试）
- Event Stream（事件流）
- Voice Output / Voice Input settings（语音输出 / 输入设置）

### 快速启动 / Quick Start

Makefile 已提供常用命令。

1. 创建 backend 虚拟环境并安装依赖：

```bash
make install-backend
```

2. 安装 desktop 依赖：

```bash
make install-desktop
```

3. 配置 backend 环境变量，手动创建 `services/backend/.env`，不要提交真实 key。可先参考下方“环境变量”。

4. 运行本地环境检查：

```bash
make doctor
```

5. 启动 backend：

```bash
make dev-backend
```

6. 启动 desktop / Electron dev：

```bash
make dev-desktop
```

首次打开会在聊天区看到 Quick Start / 新手引导。它只写入本地 settings 中的完成状态，不会写入长期记忆，也不会进入待确认记忆；之后可在 Settings 里点“新手引导：重新查看”再次打开。

如果只想启动 Vite renderer：

```bash
cd apps/desktop
npm run dev
```

`make dev` 不做复杂进程管理，只会提示分别运行 `make dev-backend` 和 `make dev-desktop`。

### 本地打包 / Local Packaging

生成本地未签名的 macOS Electron app：

```bash
make package-backend
make package-desktop
```

`make package-backend` 会用 PyInstaller 生成 backend binary。`make package-desktop` 会构建 Electron app，并把 backend binary、`data/knowledge/games` 知识资源，以及 persona / game registry 等只读 runtime resources 复制进 `.app` 的只读 resources。

packaged app 会按以下优先级连接或启动后端：

1. 外部已经运行且健康的 backend。
2. `REILINK_BACKEND_BINARY` 指定的 backend binary。
3. `.app/Contents/Resources/backend/reilink-backend` 内置 backend binary。
4. repo-local backend fallback。

当前打包是 macOS 本地未签名开发构建，用于展示、截图、录屏或 release artifact 预演；它不是正式 installer，没有 code signing、notarization、DMG installer 或 auto updater。产物默认生成在 `apps/desktop/release/ReiLink-darwin-<arch>/ReiLink.app`。macOS 可能提示应用未签名，需要在本机允许打开。

`.env`、API key、memory、session 和用户数据不会被复制进 `.app`。

Local ASR 可以通过 Settings -> Voice Input 手动配置本地 ASR binary、model 和 audio converter 路径。ReiLink 不内置、不下载、不提交 whisper binary、model 或 ffmpeg；transcript 只填入输入框，用户手动发送前不会进入 chat flow、memory、prompt、knowledge retrieval 或 game context。发布回归清单见 [docs/QA.md](docs/QA.md)，真实配置步骤见 [docs/local-asr-manual-setup.md](docs/local-asr-manual-setup.md)。

### 后端运行时 / Backend Runtime

Desktop app 会访问 `http://127.0.0.1:8000`。如果该地址已有健康的外部 ReiLink backend，app 会复用它，不会重复启动，也不会在退出时杀掉外部 backend。

如果没有外部 backend，app 会自动启动可用的 backend runtime。packaged app 优先启动内置 backend binary；开发模式可回退到 repo-local backend。app 退出时会清理由自己启动的 backend 进程，并释放 8000 端口。

后端健康检查：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/setup/status
```

### 常用命令 / Common Commands

```bash
make doctor
make dev-backend
make dev-desktop
make package-backend
make test-backend
make test-desktop
make test
make lint
make typecheck
make package-desktop
```

说明：

- `make doctor`：检查本地环境，不启动长进程。
- `make dev-backend`：启动 FastAPI backend。
- `make dev-desktop`：启动 Electron dev shell。
- `make package-backend`：用 PyInstaller 生成本地 backend binary。
- `make test`：运行 backend + desktop tests。
- `make lint`：运行 desktop lint 和 `git diff --check`。
- `make typecheck`：当前等同于 desktop build。
- `make package-desktop`：生成本地未签名的 macOS Electron app，并打入 backend binary 与 bundled knowledge resources。

常见启动问题见 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)。

项目状态见 [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。QA / 回归入口见 [docs/QA.md](docs/QA.md)，机器可读场景见 [docs/qa/retrieval_scenarios.json](docs/qa/retrieval_scenarios.json)、[docs/qa/voice_input_scenarios.json](docs/qa/voice_input_scenarios.json) 和 [docs/qa/voice_input_local_asr_scenarios.json](docs/qa/voice_input_local_asr_scenarios.json)。Voice Input v2 本地 ASR 可行性设计见 [docs/voice-input-local-asr-spike.md](docs/voice-input-local-asr-spike.md)，真实 Local ASR 手动配置和可选 smoke 见 [docs/local-asr-manual-setup.md](docs/local-asr-manual-setup.md)。Voice Interaction MVP release notes 草稿见 [docs/release-notes/reilink-voice-mvp.md](docs/release-notes/reilink-voice-mvp.md)。

### 环境变量

示例配置，放在 `services/backend/.env`：

```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL_FAST=
DEEPSEEK_MODEL_PRO=
MODEL_PREFERENCE=auto
PERSONA_MODE=minimal
PROACTIVE_COMPANION=off
PROACTIVE_SENSITIVITY=low
AUTO_GAME_DETECTION=on
```

不要在仓库中提交真实 API key。`LLM_PROVIDER=mock` 可用于无 key 的本地演示。

### 首次启动 / 模型配置

第一次启动时，desktop 会读取 backend setup status。如果 DeepSeek API Key 未加载，聊天区会显示“需要完成模型配置”，设置中只显示 API Key 状态，不显示真实 key。

确认 setup status：

```bash
curl http://127.0.0.1:8000/api/setup/status
```

正常配置后应看到：

```json
{
  "provider": "deepseek",
  "provider_configured": true,
  "api_key_loaded": true,
  "needs_setup": false,
  "missing_items": []
}
```

如果 `DEEPSEEK_API_KEY` 缺失，`needs_setup` 会是 `true`，`missing_items` 会包含 `DEEPSEEK_API_KEY`。响应不会返回真实 API key。

### 隐私与本地数据

- `.env`、`*.env` 和 `services/backend/.env` 不应提交。
- API key 通过本地环境变量或 `services/backend/.env` 配置，不会内置进 `.app`。
- packaged app 的用户数据目录是 `~/Library/Application Support/ReiLink/data`。
- memory / session / settings / logs 写入用户数据目录，不写入 `.app/Contents/Resources`。
- `.app` resources 只保存只读资源，例如 bundled knowledge、persona runtime resources 和 backend binary。
- Settings 中的“本地数据 / Local Data”可以查看并打开本地数据目录，也可以执行安全的演示状态重置操作。
- repo dev 模式下，未显式设置 `REILINK_DATA_DIR` 时会使用 repo-local `data` 目录。
- `data/memory/*` 保存本地长期记忆数据，不应提交。
- `data/session/*` 保存本地临时会话状态，不应提交。
- Pending memory（待确认记忆）必须由用户接受后才会进入长期记忆。
- Pending memory 不会直接注入 prompt。
- ReiLink 不会自动上传用户记忆或会话状态。
- 本地 knowledge packs 只提供事实上下文，不直接生成 Rei 的最终回复。

### License

ReiLink 使用 MIT License，见 [LICENSE](LICENSE)。

### 知识包结构

知识层使用本地 JSON 文件，不使用外部抓取、Steam API、RAG 或 vector database。

关键路径：

- `data/knowledge/games/catalog.json`：游戏目录。`game_id` 表示游戏 ID，`display_name` 表示显示名称，`support_status` 表示支持状态。
- `data/knowledge/games/{game_id}/manifest.json`：知识包清单。`version` 表示版本，`language` 表示语言，`coverage` 表示覆盖范围。
- `data/knowledge/games/{game_id}/snippets.json`：简短事实片段。

新增游戏知识包见 [`docs/KNOWLEDGE_PACK_AUTHORING.md`](docs/KNOWLEDGE_PACK_AUTHORING.md)。

知识包校验工具：

```bash
make validate-knowledge
```

该命令会检查 catalog、supported 游戏的 manifest 与 snippets 结构。`planned` / `detected_only` 游戏暂未接入知识包时只会输出 warning，不会让校验失败。

当前 sample packs：

- Elden Ring / 艾尔登法环
- Hollow Knight / 空洞骑士

知识层只提供 factual context（事实上下文）。Rei 的最终表达仍由 persona + LLM 生成，避免变成攻略站。

### 当前限制

- 目前只有 Elden Ring 与 Hollow Knight 的样例知识包，不是完整攻略库。
- Game detector 仍是轻量本地进程 / 应用名检测。
- backend binary 由 PyInstaller 生成，当前是 macOS 本地未签名开发构建。
- 当前没有 code signing / notarization / DMG installer / auto updater。
- 当前不是 App Store 应用或正式安装包。
- Windows / Linux 打包尚未完成。
- API key 仍通过本地环境或 `.env` 配置，不会内置进 App。
- 没有 Live2D / Vision / Overlay。
- Voice Output 当前使用系统 TTS，不是角色级配音；名字和语气的发音可能不自然。
- Voice Output 与 Voice Input v1 fallback 已接入；真实 Web Speech 在 packaged Electron 中不可靠，Local ASR ready 时主聊天语音按钮优先走本地 ASR。
- Local ASR 不内置 whisper binary、model 或 ffmpeg；用户可在 Settings 手动配置路径，audio format conversion 通过用户配置的本地 converter bridge 提供。
- 没有完整 RAG、embedding 或 vector database。
- 多游戏知识库仍处于样例阶段。
- “这个 / 那个 / 刚才说的游戏”这类指代表达仍有已知限制，未来需要 Recent Entity Tracker 或 LLM semantic resolver。

### Roadmap（路线图）

- RAG / vector search
- Steam library integration
- Local ASR native file picker / model setup helper
- Local ASR accuracy tuning / larger model guidance
- Character TTS / more natural voice output
- Live2D / overlay
- Multi-companion system
- Richer game knowledge packs
- Better entity resolution

## English

### Project Overview

ReiLink is a Chinese-first desktop AI companion for single-player game players. It combines the active game, user conversation, temporary game state, accepted memory preferences, and local knowledge packs so an original Rei-like minimal companion can respond in restrained, concise Chinese.

It is not a generic chatbot and not a pure guide site. ReiLink is designed as an AI companion with game context, memory, and a factual knowledge layer. Final replies remain LLM-first and are generated through the persona and model.

This project does not use Evangelion, Rei Ayanami, NERV, or any official IP elements.

### Status

Status: MVP / Pre-release.

Current public pre-release: v0.2-pre (`reilink-v0.2-pre`). MVP v0.1.1 (`reilink-mvp-v0.1.1`) remains the earlier public showcase baseline; active development continues on `dev/codex-reilink` for runtime / product foundation work.

The current version is suitable for local demos, portfolio presentation, and code review. It is not a full commercial release and does not include an installer, cloud accounts, payments, or complex deployment flows.

Rei is an original companion persona. This project is not affiliated with Evangelion, FromSoftware, Team Cherry, or their rights holders. Elden Ring / Hollow Knight are used only as local sample knowledge contexts to demonstrate the multi-game knowledge interface; related names and trademarks belong to their respective owners.

### Screenshots

The bilingual screenshot showcase above uses repository assets under `docs/assets/` for GitHub, portfolio, and interview presentation.

### Key Features

- Chinese AI companion chat
- Original Rei-like minimal persona
- DeepSeek model provider
- Model routing: `fast` / `pro` / `auto`
- Multi-part replies
- Pending memory confirmation
- Game session state
- Semantic extraction
- Proactive companion trigger
- Local game detection
- Manual game context override
- Multi-game knowledge catalog
- Knowledge pack manifest
- Knowledge Retrieval with local keyword retrieval, grounding / gating, and explicit game-name switching
- Elden Ring and Hollow Knight sample knowledge packs
- Voice Output with Test Voice, rate, and volume
- Voice Input v1 push-to-talk Web Speech fallback with no auto-send
- Local ASR v1 with Settings configuration, local record/transcribe, main-chat voice-button integration, and no auto-send
- Event Stream with safe lifecycle summaries
- Debug dashboard
- Prompt / context preview
- Settings panel
- Local-first memory and session state
- Standalone App Packaging v1
- Bundled backend binary and bundled knowledge resources
- Local Data Controls for inspecting, opening, and safely resetting local data

### Voice Interaction MVP

ReiLink's current Voice Interaction MVP is optional voice output plus user-confirmed local voice input. It is not a fully natural voice assistant.

- Voice Output: local system `speechSynthesis`, off by default, with Test Voice, rate, volume, Stop Voice, and safe Event Stream lifecycle summaries.
- Voice Input: Web Speech remains a fallback; the stable path is Local ASR after the user manually configures a whisper.cpp-compatible binary, model, and converter in Settings.
- Transcript-first UX: recognized text fills the chat input only. The user can edit or delete it, and it enters chat flow, memory, prompt, knowledge retrieval, or game context only after manual send.
- Privacy: no cloud ASR, no default audio retention, no bundled or downloaded whisper binary/model/ffmpeg, and no full path, full transcript, raw subprocess output, API key, or `.env` in Debug / Event Stream / Raw JSON.

### Tech Stack

Backend:

- Python
- FastAPI
- JSON / JSONL local state
- DeepSeek-compatible provider

Desktop:

- Electron
- React
- TypeScript
- Vite

Tests:

- pytest
- Vitest
- React Testing Library
- Playwright

### Architecture

Main backend modules:

- `persona_engine`: loads persona configuration and builds system prompt context.
- `dialogue_agent`: orchestrates settings, game state, knowledge, model routing, provider calls, and debug data.
- `game_session`: tracks active game, boss, progress, and temporary session state.
- `memory`: separates pending memory from accepted long-term memory.
- `semantic_extraction`: extracts game-state and memory-candidate signals from user messages.
- `game_knowledge` / `knowledge`: provides factual context through catalog and snippets.
- `game_detector`: detects the active game from local process or app names.
- `proactive`: handles low-frequency proactive companion triggers and cooldowns.
- `app_settings`: persists user-facing settings.

Main desktop areas:

- Chat UI
- Settings
- Pending Memory
- Game Session / Game Context Debug
- Prompt Preview
- Knowledge Debug
- Event Stream
- Voice Output / Voice Input settings

### Quick Start

The Makefile includes the common development commands.

1. Create the backend virtual environment and install dependencies:

```bash
make install-backend
```

2. Install desktop dependencies:

```bash
make install-desktop
```

3. Configure backend environment variables by creating `services/backend/.env` manually. Do not commit real keys. See "Environment Variables" below.

4. Run the local environment check:

```bash
make doctor
```

5. Start the backend:

```bash
make dev-backend
```

6. Start the desktop / Electron dev shell:

```bash
make dev-desktop
```

On first open, the chat area shows a Quick Start onboarding card. It only stores completion state in local settings, does not write long-term memory, and does not create pending memory; it can be reopened from Settings.

To start the Vite renderer only:

```bash
cd apps/desktop
npm run dev
```

`make dev` does not manage long-running processes. It prints the two commands to run in separate terminals: `make dev-backend` and `make dev-desktop`.

### Local Packaging

Build an unsigned local macOS Electron app:

```bash
make package-backend
make package-desktop
```

`make package-backend` builds the backend binary with PyInstaller. `make package-desktop` builds the Electron app and copies the backend binary, `data/knowledge/games` knowledge resources, and read-only runtime resources such as persona data and the game registry into the app's read-only resources.

The packaged app connects to or starts the backend in this order:

1. An already-running healthy external backend.
2. The backend binary specified by `REILINK_BACKEND_BINARY`.
3. The bundled backend binary at `.app/Contents/Resources/backend/reilink-backend`.
4. A repo-local backend fallback.

This is an unsigned local macOS development build for demos, screenshots, recordings, or release artifact dry runs. It is not a formal installer and does not include code signing, notarization, a DMG installer, or an auto updater. The default output is `apps/desktop/release/ReiLink-darwin-<arch>/ReiLink.app`. macOS may warn that the app is unsigned, so you may need to allow it locally.

`.env` files, API keys, memory, session state, and user data are not copied into the `.app`.

Local ASR can be configured manually from Settings -> Voice Input with user-provided ASR binary, model, and audio converter paths. ReiLink does not bundle, download, or commit a whisper binary, model, or ffmpeg; transcripts only fill the input and do not enter chat flow, memory, prompt, knowledge retrieval, or game context until the user manually sends. The release regression checklist is in [docs/QA.md](docs/QA.md), and real setup steps are in [docs/local-asr-manual-setup.md](docs/local-asr-manual-setup.md).

### Backend Runtime

The desktop app talks to `http://127.0.0.1:8000`. If that address already has a healthy external ReiLink backend, the app reuses it, does not start a duplicate backend, and does not kill the external backend when quitting.

If no external backend is available, the app automatically starts an available backend runtime. The packaged app prefers the bundled backend binary; development mode can fall back to the repo-local backend. When the app quits, it cleans up backend processes it started itself and releases port 8000.

Backend health checks:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/setup/status
```

### Common Commands

```bash
make doctor
make dev-backend
make dev-desktop
make package-backend
make test-backend
make test-desktop
make test
make lint
make typecheck
make package-desktop
```

Notes:

- `make doctor`: checks the local environment without starting long-running processes.
- `make dev-backend`: starts the FastAPI backend.
- `make dev-desktop`: starts the Electron dev shell.
- `make package-backend`: builds the local backend binary with PyInstaller.
- `make test`: runs backend + desktop tests.
- `make lint`: runs desktop lint and `git diff --check`.
- `make typecheck`: currently runs the desktop build.
- `make package-desktop`: builds an unsigned local macOS Electron app with the backend binary and bundled knowledge resources.

For common startup issues, see [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

Current project status is in [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md). For manual QA and regression coverage, see [docs/QA.md](docs/QA.md). Machine-readable scenarios live in [docs/qa/retrieval_scenarios.json](docs/qa/retrieval_scenarios.json), [docs/qa/voice_input_scenarios.json](docs/qa/voice_input_scenarios.json), and [docs/qa/voice_input_local_asr_scenarios.json](docs/qa/voice_input_local_asr_scenarios.json). The Voice Input v2 local ASR feasibility plan is in [docs/voice-input-local-asr-spike.md](docs/voice-input-local-asr-spike.md), the real Local ASR manual setup / optional smoke guide is in [docs/local-asr-manual-setup.md](docs/local-asr-manual-setup.md), and the Voice Interaction MVP release notes draft is in [docs/release-notes/reilink-voice-mvp.md](docs/release-notes/reilink-voice-mvp.md).

### Environment Variables

Example `services/backend/.env`:

```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL_FAST=
DEEPSEEK_MODEL_PRO=
MODEL_PREFERENCE=auto
PERSONA_MODE=minimal
PROACTIVE_COMPANION=off
PROACTIVE_SENSITIVITY=low
AUTO_GAME_DETECTION=on
```

Never commit real API keys. `LLM_PROVIDER=mock` can be used for local demos without a key.

### First Run / Provider Setup

On first launch, the desktop app reads the backend setup status. If the DeepSeek API key is not loaded, the chat area shows a lightweight setup prompt, and Settings only shows the API key status without revealing the key value.

Check setup status:

```bash
curl http://127.0.0.1:8000/api/setup/status
```

After a valid local configuration, the response should include:

```json
{
  "provider": "deepseek",
  "provider_configured": true,
  "api_key_loaded": true,
  "needs_setup": false,
  "missing_items": []
}
```

If `DEEPSEEK_API_KEY` is missing, `needs_setup` is `true` and `missing_items` includes `DEEPSEEK_API_KEY`. The response never returns the real API key.

### Privacy / Local Data

- `.env`, `*.env`, and `services/backend/.env` should never be committed.
- API keys are configured through local environment variables or `services/backend/.env`; they are not bundled into the `.app`.
- The packaged app user data directory is `~/Library/Application Support/ReiLink/data`.
- Memory, session, settings, and logs are written to the user data directory, not to `.app/Contents/Resources`.
- `.app` resources only hold read-only resources such as bundled knowledge, persona runtime resources, and the backend binary.
- Settings includes "本地数据 / Local Data" for viewing and opening the local data directory and for safe demo reset controls.
- In repo dev mode, ReiLink uses the repo-local `data` directory unless `REILINK_DATA_DIR` is set.
- `data/memory/*` stores local long-term memory data and should not be committed.
- `data/session/*` stores local temporary session state and should not be committed.
- Pending memory must be accepted by the user before it enters long-term memory.
- Pending memory is not injected directly into prompts.
- ReiLink does not automatically upload user memory or session state.
- Local knowledge packs provide factual context only; they do not generate Rei's final reply directly.

### License

ReiLink is licensed under the MIT License. See [LICENSE](LICENSE).

### Knowledge Packs

The knowledge layer uses local JSON files. It does not use external crawling, Steam API, RAG, or a vector database.

Key paths:

- `data/knowledge/games/catalog.json`: game catalog. `game_id` means game identifier, `display_name` means display name, and `support_status` means support state.
- `data/knowledge/games/{game_id}/manifest.json`: knowledge pack manifest. `version` means pack version, `language` means pack language, and `coverage` means covered topics.
- `data/knowledge/games/{game_id}/snippets.json`: short factual snippets.

See [`docs/KNOWLEDGE_PACK_AUTHORING.md`](docs/KNOWLEDGE_PACK_AUTHORING.md) for adding new game knowledge packs.

Knowledge pack validator:

```bash
make validate-knowledge
```

This command checks the catalog plus manifest and snippets structure for supported games. `planned` / `detected_only` games without knowledge packs only produce warnings and do not fail validation.

Current sample packs:

- Elden Ring
- Hollow Knight

The knowledge layer only provides factual context. Rei's final wording is still generated by persona + LLM, so the product does not become a guide site.

### Current Limitations

- Only Elden Ring and Hollow Knight have sample knowledge packs today.
- Game detection is still lightweight local process / app-name detection.
- The backend binary is generated by PyInstaller and currently targets unsigned local macOS development builds.
- There is no code signing, notarization, DMG installer, or auto updater yet.
- This is not an App Store app or a formal installer.
- Windows / Linux packaging is not complete yet.
- API keys are still configured through the local environment or `.env`; they are not bundled into the app.
- No Live2D / Vision / Overlay.
- Voice Output currently uses system TTS, not character-grade voice acting; names and tone may sound unnatural.
- Voice Output and Voice Input v1 fallback are implemented; real Web Speech is unreliable in packaged Electron, and the main chat voice button prefers Local ASR when it is ready.
- Local ASR does not bundle a whisper binary, model, or ffmpeg; users can configure paths in Settings, and audio format conversion is available through a user-configured local converter bridge.
- No full RAG, embeddings, or vector database.
- Multi-game knowledge is still at sample-pack stage.
- Referential phrases such as "this game", "that one", or "the game we just mentioned" have known limitations and will need a Recent Entity Tracker or LLM semantic resolver.

### Roadmap

- RAG / vector search
- Steam library integration
- Local ASR native file picker / model setup helper
- Local ASR accuracy tuning / larger-model guidance
- Character TTS / more natural voice output
- Live2D / overlay
- Multi-companion system
- Richer game knowledge packs
- Better entity resolution
