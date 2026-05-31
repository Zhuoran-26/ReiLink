# ReiLink v0.1 Release Notes

## 中文

### 状态

ReiLink v0.1 是 MVP / pre-release。它用于公开展示、作品集说明和本地演示，不是完整商业发布版本。

当前公开展示材料已补齐：LICENSE、README 截图区、release notes 与 public readiness checklist。仓库 visibility 仍需发布前手动决定。

### MVP 功能

- FastAPI backend 与 Electron / React desktop shell。
- 中文优先的原创 AI companion chat。
- DeepSeek-compatible provider，支持 `fast` / `pro` / `auto` model preference。
- Minimal persona 为默认模式，guarded 保留为 fallback。
- Game session state，记录当前游戏、Boss、死亡和挫败等临时状态。
- Semantic extraction，用于识别游戏状态和待确认记忆候选。
- Pending memory confirmation，用户接受后才写入长期记忆。
- Proactive companion，包含 cooldown、阻断规则和低频触发。
- Local game detector 与 manual game context control。
- Multi-game catalog 与 knowledge pack manifest。
- Elden Ring / Hollow Knight sample knowledge packs。
- Debug dashboard、prompt/context preview、first run provider setup 和 dev health check。

### 截图 / Screenshots

核心截图已整理到 `docs/assets/`，用于 GitHub / portfolio / interview 展示。

![Main Chat](assets/reilink-main-chat.jpeg)

![Pending Memory](assets/reilink-pending-memory.jpeg)

![Elden Ring Knowledge](assets/reilink-knowledge-elden-ring.jpeg)

![Hollow Knight Knowledge](assets/reilink-knowledge-hollow-knight.jpeg)

![Context Preview](assets/reilink-context-preview.jpeg)

![Debug Panel](assets/reilink-debug-panel.jpeg)

### 已知限制

- 当前知识包是 sample packs，不是完整攻略库。
- Game detector 是轻量本地进程 / 应用名检测。
- 指代表达如“这个 / 那个 / 刚才说的游戏”仍有已知限制。
- 没有 Steam login / Steam Web API。
- 没有外部攻略站抓取、RAG、embedding 或 vector database。
- 没有 Live2D / Voice / Vision / Overlay。
- 当前不提供云端账号、在线保存 API key 或支付系统。

### 安装 / 启动

```bash
make install-backend
make install-desktop
make doctor
make dev-backend
make dev-desktop
```

后端健康检查：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/setup/status
```

### 隐私说明

- 不要提交 `.env`、`*.env` 或 `services/backend/.env`。
- 不要提交 `data/memory/*` 或 `data/session/*`。
- API key 只在本地 `.env` 中读取，setup status 只显示 loaded / missing。
- Pending memory 必须由用户确认后才进入长期记忆。
- ReiLink 不会自动上传用户记忆或会话状态。

### 后续计划

- 准备可选 public demo short video 或更多展示素材。
- 扩展更多游戏 sample knowledge packs。
- 改进游戏实体指代解析。
- 继续完善 first run、developer startup 和 release checklist。
- 评估更强的知识检索层，但不在 v0.1 范围内引入复杂 RAG。

## English

### Status

ReiLink v0.1 is an MVP / pre-release. It is intended for public presentation, portfolio review, and local demos, not as a full commercial release.

The public showcase materials are now prepared: LICENSE, README screenshots, release notes, and the public readiness checklist. Repository visibility still needs to be decided manually before release.

### MVP Features

- FastAPI backend and Electron / React desktop shell.
- Chinese-first original AI companion chat.
- DeepSeek-compatible provider with `fast` / `pro` / `auto` model preference.
- Minimal persona as the default mode, with guarded kept as a fallback.
- Game session state for active game, boss, death count, and frustration signals.
- Semantic extraction for game-state and pending-memory candidates.
- Pending memory confirmation before anything enters long-term memory.
- Proactive companion with cooldown, blocking rules, and low-frequency triggers.
- Local game detector and manual game context control.
- Multi-game catalog and knowledge pack manifest.
- Elden Ring / Hollow Knight sample knowledge packs.
- Debug dashboard, prompt/context preview, first run provider setup, and dev health check.

### Screenshots

Core screenshots are organized under `docs/assets/` for GitHub, portfolio, and interview presentation.

See the screenshot references in the Chinese section above for main chat, pending memory, multi-game knowledge, context preview, and debug.

### Known Limitations

- Current knowledge packs are sample packs, not complete guide databases.
- Game detection is lightweight local process / app-name detection.
- Referential phrases such as "this game", "that one", or "the game we just mentioned" remain limited.
- No Steam login / Steam Web API.
- No external guide-site crawling, RAG, embeddings, or vector database.
- No Live2D / Voice / Vision / Overlay.
- No cloud account, online API key storage, or payment system.

### Install / Start

```bash
make install-backend
make install-desktop
make doctor
make dev-backend
make dev-desktop
```

Backend health checks:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/setup/status
```

### Privacy

- Do not commit `.env`, `*.env`, or `services/backend/.env`.
- Do not commit `data/memory/*` or `data/session/*`.
- API keys are read only from the local `.env`; setup status only reports loaded / missing.
- Pending memory must be accepted by the user before it enters long-term memory.
- ReiLink does not automatically upload user memory or session state.

### Next Steps

- Prepare an optional public demo short video or additional showcase assets.
- Expand more game sample knowledge packs.
- Improve game entity reference resolution.
- Continue improving first run, developer startup, and release checklist flows.
- Evaluate a stronger retrieval layer later, without adding complex RAG in v0.1.
