# Project Status

## 中文

Updated: 2026-06-05

### 当前阶段

当前阶段：`v0.2-pre productization / 产品化补齐预发布阶段`。

`reilink-mvp-v0.1.1` 已经作为公开展示版本发布，用于 GitHub / portfolio / interview 展示。`reilink-v0.2-pre` 已作为预发布版本公开，当前 `dev/codex-reilink` 已进一步补齐 standalone runtime / productization foundation，并继续推进 Voice Output、Voice Input fallback、Local ASR staged foundation 与 Knowledge Retrieval QA。

v0.2-pre 的重点不是新增核心玩法或扩大业务范围，而是让首次启动、开发启动、公开展示、standalone runtime、本地数据目录、多游戏知识维护和 release readiness 更清晰、更稳定。

产品方向：

- 中文优先的单机游戏 AI companion。
- LLM-first 回复生成。
- 游戏上下文、记忆和知识层提供辅助信息。
- 当前 sample companion 是 Rei-like 原创 minimal persona，不使用官方 IP。

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
- Semantic Extraction。
- Pending Memory confirmation。
- Proactive Companion，包含 cooldown 与阻断规则。
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
- Event Bus / Event Stream。
- Prompt Preview。
- Debug Dashboard。
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
- Bundled runtime resources：persona、persona style 和 game registry 等只读资源随 packaged app 分发。
- Backend runtime priority：external backend、configured binary、bundled binary、repo fallback。
- User data dir：packaged app 使用 `~/Library/Application Support/ReiLink/data`。
- Local Data Controls：Settings 中查看 / 打开本地数据目录，并复用 Demo Reset / reset controls。
- Audio Capture / Temp File probe。
- Local ASR staged foundation：feasibility plan、config detection、CLI probe、Backend ASR Transcription Bridge、Audio Format Conversion bridge、whisper-like output parsing hardening、manual setup guide。

### 当前 Voice / Local ASR 状态

- Voice Output 已完成并可用：支持 Test Voice、rate / volume、中文语音优先，`tts_started` 只在真实 `utterance.onstart` 后触发，`tts_completed` / `tts_error` 映射到安全中文摘要。
- Voice Input v1 已完成 push-to-talk fallback：Web Speech transcript 只填入输入框，不自动发送；未确认 transcript 不进入 memory、prompt、knowledge retrieval 或 game context。
- Electron packaged 环境中的 Web Speech Recognition 服务不可靠，当前不作为稳定主路径。
- Local ASR 是当前推进方向，已完成 staged foundation：feasibility plan、config detection、CLI probe、Audio Capture / Temp File probe、Backend ASR Transcription Bridge、Audio Format Conversion bridge 和 whisper-like parsing QA。
- Audio Format Conversion v1 已支持通过用户配置的 `REILINK_AUDIO_CONVERTER_BINARY` 把 WebM/Ogg 等录音格式转为 WAV；未配置或失败时安全短路，不调用 ASR。
- Local ASR 当前不提交 whisper binary，不提交 model，不提交 ffmpeg / converter binary，不接入云 ASR 或商业 ASR。
- Local ASR manual setup guide 已新增；真实 whisper.cpp / model / converter 仍由用户手动配置，不随 app 内置。
- 真实 whisper 手动 smoke 仍是 optional / manual，不是自动测试依赖。

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
- packaged app 使用内置只读 resources 与 `~/Library/Application Support/ReiLink/data` 用户数据目录。

### 后续重点

- v0.2 stable packaging polish。
- Installer / DMG spike。
- Code signing / notarization research。
- Windows packaging。
- Knowledge pack expansion。
- Optional RAG / vector retrieval。
- Local ASR real whisper.cpp manual QA。
- Local ASR converter setup and packaged manual QA。
- User-friendly Local ASR setup flow。
- Optional Overlay / Live2D。
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
- Live2D / Vision / Overlay。
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

Updated: 2026-06-05

### Current Stage

Current stage: `v0.2-pre productization / 产品化补齐预发布阶段`.

`reilink-mvp-v0.1.1` has been published as the public showcase version for GitHub, portfolio, and interview presentation. `reilink-v0.2-pre` has been published as a pre-release, and the current `dev/codex-reilink` branch has further filled in standalone runtime / productization foundation while continuing Voice Output, Voice Input fallback, Local ASR staged foundation, and Knowledge Retrieval QA work.

The v0.2-pre focus is not adding major core features or expanding product scope. It is making first run, developer startup, public presentation, standalone runtime, local data directories, multi-game knowledge maintenance, and release readiness clearer and more stable.

Product direction:

- Chinese-first AI companion for single-player game players.
- LLM-first response generation.
- Game context, memory, and knowledge provide supporting context.
- The current sample companion is an original Rei-like minimal persona and does not use official IP.

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
- Semantic Extraction.
- Pending Memory confirmation.
- Proactive Companion with cooldown and blocking safeguards.
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
- Event Bus / Event Stream.
- Prompt Preview.
- Debug Dashboard.
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
- Bundled runtime resources: read-only resources such as persona data, persona style, and the game registry are distributed with the packaged app.
- Backend runtime priority: external backend, configured binary, bundled binary, repo fallback.
- User data dir: the packaged app uses `~/Library/Application Support/ReiLink/data`.
- Local Data Controls: Settings can show / open the local data directory and reuse Demo Reset / reset controls.
- Audio Capture / Temp File probe.
- Local ASR staged foundation: feasibility plan, config detection, CLI probe, Backend ASR Transcription Bridge, Audio Format Conversion bridge, whisper-like output parsing hardening, and manual setup guide.

### Current Voice / Local ASR Status

- Voice Output is implemented and usable: Test Voice, rate / volume, Chinese voice preference, `tts_started` only after the real `utterance.onstart`, and safe Chinese Event Stream summaries.
- Voice Input v1 push-to-talk fallback is implemented: Web Speech transcripts only fill the input and are not auto-sent; unconfirmed transcripts do not enter memory, prompt, knowledge retrieval, or game context.
- Web Speech Recognition is not reliable in the packaged Electron runtime and is not the stable main path.
- Local ASR is the current direction, with staged foundation complete: feasibility plan, config detection, CLI probe, Audio Capture / Temp File probe, Backend ASR Transcription Bridge, Audio Format Conversion bridge, and whisper-like parsing QA.
- Audio Format Conversion v1 can use a user-configured `REILINK_AUDIO_CONVERTER_BINARY` to convert WebM/Ogg-style recordings to WAV; missing or failed converters short-circuit safely and do not call ASR.
- Local ASR does not commit a whisper binary, model file, ffmpeg / converter binary, cloud ASR, or commercial ASR integration.
- The Local ASR manual setup guide has been added; real whisper.cpp / model / converter remains user-configured and is not bundled with the app.
- Real whisper manual smoke remains optional / manual and is not an automated test dependency.

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
- The packaged app uses read-only bundled resources and the user data directory at `~/Library/Application Support/ReiLink/data`.

### Upcoming Focus

- v0.2 stable packaging polish.
- Installer / DMG spike.
- Code signing / notarization research.
- Windows packaging.
- Knowledge pack expansion.
- Optional RAG / vector retrieval.
- Local ASR real whisper.cpp manual QA.
- Local ASR converter setup and packaged manual QA.
- User-friendly Local ASR setup flow.
- Optional Overlay / Live2D.
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
- Live2D / Vision / Overlay.
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
