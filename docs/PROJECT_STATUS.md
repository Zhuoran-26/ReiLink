# Project Status

## 中文

Updated: 2026-06-02

### 当前阶段

当前阶段：`v0.2-pre productization / 产品化补齐预发布阶段`。

`reilink-mvp-v0.1.1` 已经作为公开展示版本发布，用于 GitHub / portfolio / interview 展示。`reilink-v0.2-pre` 已作为预发布版本公开，当前 `dev/codex-reilink` 已进一步补齐 standalone runtime / productization foundation。

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
- Elden Ring sample knowledge pack。
- Hollow Knight sample knowledge pack。
- Prompt Preview。
- Debug Dashboard。
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
- Backend runtime priority：external backend、configured binary、bundled binary、repo fallback。
- User data dir：packaged app 使用 `~/Library/Application Support/ReiLink/data`。
- Local Data Controls：Settings 中查看 / 打开本地数据目录，并复用 Demo Reset / reset controls。

### 后续重点

- v0.2 stable packaging polish。
- Installer / DMG spike。
- Code signing / notarization research。
- Windows packaging。
- Knowledge pack expansion。
- Optional RAG / vector retrieval。
- Optional Voice interaction。
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
- Live2D / Voice / Vision / Overlay。
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

Updated: 2026-06-02

### Current Stage

Current stage: `v0.2-pre productization / 产品化补齐预发布阶段`.

`reilink-mvp-v0.1.1` has been published as the public showcase version for GitHub, portfolio, and interview presentation. `reilink-v0.2-pre` has been published as a pre-release, and the current `dev/codex-reilink` branch has further filled in standalone runtime / productization foundation.

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
- Elden Ring sample knowledge pack.
- Hollow Knight sample knowledge pack.
- Prompt Preview.
- Debug Dashboard.
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
- Backend runtime priority: external backend, configured binary, bundled binary, repo fallback.
- User data dir: the packaged app uses `~/Library/Application Support/ReiLink/data`.
- Local Data Controls: Settings can show / open the local data directory and reuse Demo Reset / reset controls.

### Upcoming Focus

- v0.2 stable packaging polish.
- Installer / DMG spike.
- Code signing / notarization research.
- Windows packaging.
- Knowledge pack expansion.
- Optional RAG / vector retrieval.
- Optional Voice interaction.
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
- Live2D / Voice / Vision / Overlay.
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
