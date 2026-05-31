# Roadmap

## 中文

### 当前阶段：v0.2-pre productization 基本完成

MVP v0.1 / v0.1.1 已完成，其中 `reilink-mvp-v0.1.1` 已作为公开展示版本发布。当前 `dev/codex-reilink` 上的 v0.2-pre productization 已基本完成，重点是首次配置、开发启动、公开展示、release readiness 和多游戏知识包维护。

MVP v0.1 / v0.1.1 已完成的核心能力：

- 中文 AI companion chat。
- Game Session State。
- Pending Memory confirmation。
- Proactive Companion。
- Local Game Detector。
- Manual Game Context Control。
- Unsupported Game fallback。
- Multi-game Knowledge Catalog。
- Knowledge Pack Manifest。
- Elden Ring 与 Hollow Knight sample knowledge packs。
- Debug Dashboard 与 Prompt Preview。

v0.2-pre 已完成的产品化补齐：

- First Run / Provider Setup。
- Dev Startup / Health Check。
- Public Readiness。
- Public screenshots and showcase assets。
- Knowledge Pack Validation Tool。
- Knowledge Pack Authoring Guide。
- Release notes / roadmap / checklist sync。

### 下一阶段重点

- v0.2 stable polish：修整体验细节、文档边界和 release checklist。
- Installer / packaging：准备更易分发的桌面安装方式。
- Knowledge pack expansion：扩展更多游戏 sample knowledge packs，同时保持轻量、可审查。
- Optional RAG / vector retrieval：评估是否进入更强检索层，但不把 sample pack 阶段误写成完整 RAG。
- Voice interaction：语音输入 / 输出。
- Overlay / Live2D：视觉陪伴层。
- Multi-companion system：多 companion 和多角色配置。

### 后续候选方向

- Better entity resolution：解决“这个 / 那个 / 刚才说的游戏”等指代问题。
- Richer game knowledge packs：扩展更多游戏与更完整知识包。
- Stronger local setup checks：让开发启动和运行诊断更明确。
- Public demo material：可选 demo video 或更完整展示素材。

### 当前不做

- 不做外部攻略站抓取。
- 不做 Steam Web API 或 Steam 登录。
- 不做 embeddings / vector database，除非后续明确进入 RAG 阶段。
- 不把 Rei 做成攻略站或通用 chatbot。
- 不把 Voice、Live2D、Overlay、Vision 或 multi-companion system 标记为已完成。

## English

### Current Stage: v0.2-pre Productization Mostly Complete

MVP v0.1 / v0.1.1 is complete, and `reilink-mvp-v0.1.1` has been published as the public showcase version. The current `dev/codex-reilink` branch has mostly completed v0.2-pre productization, focused on first-run setup, developer startup, public presentation, release readiness, and multi-game knowledge pack maintenance.

Core capabilities completed in MVP v0.1 / v0.1.1:

- Chinese AI companion chat.
- Game Session State.
- Pending Memory confirmation.
- Proactive Companion.
- Local Game Detector.
- Manual Game Context Control.
- Unsupported Game fallback.
- Multi-game Knowledge Catalog.
- Knowledge Pack Manifest.
- Elden Ring and Hollow Knight sample knowledge packs.
- Debug Dashboard and Prompt Preview.

Productization work completed in v0.2-pre:

- First Run / Provider Setup.
- Dev Startup / Health Check.
- Public Readiness.
- Public screenshots and showcase assets.
- Knowledge Pack Validation Tool.
- Knowledge Pack Authoring Guide.
- Release notes / roadmap / checklist sync.

### Next Focus

- v0.2 stable polish: refine experience details, documentation boundaries, and the release checklist.
- Installer / packaging: prepare an easier desktop distribution path.
- Knowledge pack expansion: add more sample knowledge packs while keeping them lightweight and reviewable.
- Optional RAG / vector retrieval: evaluate a stronger retrieval layer without mislabeling the current sample-pack stage as full RAG.
- Voice interaction: speech input and output.
- Overlay / Live2D: a visual companion layer.
- Multi-companion system: multiple companion and character configurations.

### Candidate Future Directions

- Better entity resolution: resolve referential phrases such as "this game", "that one", or "the game we just mentioned".
- Richer game knowledge packs: more games and deeper local knowledge packs.
- Stronger local setup checks: make development startup and diagnostics clearer.
- Public demo material: optional demo video or more complete showcase assets.

### Out Of Scope For Now

- No external guide-site crawling.
- No Steam Web API or Steam login.
- No embeddings / vector database unless a future task explicitly enters the RAG stage.
- Do not turn Rei into a guide site or generic chatbot.
- Do not mark Voice, Live2D, Overlay, Vision, or the multi-companion system as completed.
