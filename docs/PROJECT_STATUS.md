# Project Status

## 中文

Updated: 2026-06-01

### 当前阶段

ReiLink 处于 MVP v0.1 收口阶段。当前重点不再是新增大功能，而是保证本地演示稳定、项目能力讲得清楚、文档和调试面板能支撑 GitHub / portfolio / interview 展示。

产品方向：

- 中文优先的单机游戏 AI companion。
- LLM-first 回复生成。
- 游戏上下文、记忆和知识层提供辅助信息。
- 当前 sample companion 是 Rei-like 原创 minimal persona，不使用官方 IP。

### 当前分支

```text
dev/codex-reilink
```

### 最新稳定实现提交

```text
ee7e791 feat: add knowledge pack manifests
```

这是 MVP 文档收口前的最新已验证实现基线。

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
- Game Catalog / Multi-game Knowledge Interface。
- Knowledge Pack Manifest v1。
- Elden Ring sample knowledge pack。
- Hollow Knight sample knowledge pack。
- Prompt Preview。
- Debug Dashboard。
- UI polish。

### 当前数据范围

- `elden_ring` 和 `hollow_knight` 是当前已接入的 sample knowledge packs。
- `sekiro`、`baldurs_gate_3`、`cyberpunk_2077`、`monster_hunter` 等条目可作为 planned / detected_only 状态展示，但没有完整知识包。
- 游戏注册表位于 `data/games/game_registry.json`。
- 知识目录位于 `data/knowledge/games/catalog.json`。
- 每个已支持知识包应包含 `manifest.json` 和 `snippets.json`。

### 明确不在当前范围

- Steam login / Steam Web API。
- 外部抓取攻略站。
- RAG / vector database / embeddings。
- Live2D / Voice / Vision / Overlay。
- Multi-character system。

### 验证基线

最近实现提交已通过：

```text
backend tests: passed
desktop tests: passed
desktop build: passed
lint: passed
desktop e2e: passed
git diff --check: passed
```

文档-only 更新通常只需要运行 `git diff --check`，除非任务修改了 backend 或 frontend 文件。

## English

Updated: 2026-06-01

### Current Stage

ReiLink is in the MVP v0.1 wrap-up stage. The current focus is no longer adding major product features, but making the local demo stable, the project easy to explain, and the documentation / debug surfaces strong enough for GitHub, portfolio, and interview presentation.

Product direction:

- Chinese-first AI companion for single-player game players.
- LLM-first response generation.
- Game context, memory, and knowledge provide supporting context.
- The current sample companion is an original Rei-like minimal persona and does not use official IP.

### Current Branch

```text
dev/codex-reilink
```

### Latest Stable Implementation Commit

```text
ee7e791 feat: add knowledge pack manifests
```

This is the latest verified implementation baseline before the MVP documentation wrap-up.

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
- Game Catalog / Multi-game Knowledge Interface.
- Knowledge Pack Manifest v1.
- Elden Ring sample knowledge pack.
- Hollow Knight sample knowledge pack.
- Prompt Preview.
- Debug Dashboard.
- UI polish.

### Current Data Scope

- `elden_ring` and `hollow_knight` are the currently supported sample knowledge packs.
- `sekiro`, `baldurs_gate_3`, `cyberpunk_2077`, `monster_hunter`, and similar entries may appear as planned / detected_only catalog states, but they do not have full knowledge packs.
- The game registry lives at `data/games/game_registry.json`.
- The knowledge catalog lives at `data/knowledge/games/catalog.json`.
- Each supported knowledge pack should include `manifest.json` and `snippets.json`.

### Explicitly Out Of Scope For Now

- Steam login / Steam Web API.
- External guide-site crawling.
- RAG / vector database / embeddings.
- Live2D / Voice / Vision / Overlay.
- Multi-character system.

### Verification Baseline

The latest implementation commit passed:

```text
backend tests: passed
desktop tests: passed
desktop build: passed
lint: passed
desktop e2e: passed
git diff --check: passed
```

Documentation-only updates usually only require `git diff --check`, unless backend or frontend files are changed.
