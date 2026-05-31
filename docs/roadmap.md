# Roadmap

## 中文

### 当前阶段：v0.2 产品化补齐

MVP v0.1 已完成并发布 pre-release tag。当前 `dev/codex-reilink` 正在进行 v0.2 productization，重点是让本地启动、首次配置、公开展示和 release readiness 更清晰。

MVP v0.1 已完成的核心能力：

- 中文 AI companion chat。
- Game Session State。
- Pending Memory confirmation。
- Local Game Detector。
- Manual Game Context Control。
- Multi-game Knowledge Catalog。
- Knowledge Pack Manifest。
- Elden Ring 与 Hollow Knight sample knowledge packs。
- Debug Dashboard 与 Prompt Preview。

v0.2 已完成的产品化补齐：

- First Run / Provider Setup。
- Dev Startup / Health Check。
- Public Readiness / Release Polish。

### 下一阶段重点

- Public readiness final check。
- Screenshots / demo assets。
- Optional public release。

### 后续候选方向

- RAG / vector search：让知识检索从样例 snippets 扩展为更强的检索层。
- Steam library integration：识别用户本地游戏库，但不涉及 Steam 登录前应先明确隐私边界。
- Voice interaction：语音输入 / 输出。
- Live2D / overlay：视觉陪伴层。
- Multi-companion system：多 companion 和多角色配置。
- Richer game knowledge packs：扩展更多游戏与更完整知识包。
- Better entity resolution：解决“这个 / 那个 / 刚才说的游戏”等指代问题。

### 当前不做

- 不做外部攻略站抓取。
- 不做 Steam Web API 或 Steam 登录。
- 不做 embeddings / vector database，除非后续明确进入 RAG 阶段。
- 不把 Rei 做成攻略站或通用 chatbot。

## English

### Current Stage: v0.2 Productization

MVP v0.1 has been completed and released with a pre-release tag. The current `dev/codex-reilink` branch is in v0.2 productization, focused on making local startup, first-run setup, public presentation, and release readiness clearer.

Core capabilities completed in MVP v0.1:

- Chinese AI companion chat.
- Game Session State.
- Pending Memory confirmation.
- Local Game Detector.
- Manual Game Context Control.
- Multi-game Knowledge Catalog.
- Knowledge Pack Manifest.
- Elden Ring and Hollow Knight sample knowledge packs.
- Debug Dashboard and Prompt Preview.

Productization work completed in v0.2:

- First Run / Provider Setup.
- Dev Startup / Health Check.
- Public Readiness / Release Polish.

### Next Focus

- Public readiness final check.
- Screenshots / demo assets.
- Optional public release.

### Candidate Future Directions

- RAG / vector search: evolve beyond sample snippets into a stronger retrieval layer.
- Steam library integration: detect the user's local game library, with clear privacy boundaries before any Steam login work.
- Voice interaction: speech input and output.
- Live2D / overlay: a visual companion layer.
- Multi-companion system: multiple companion and character configurations.
- Richer game knowledge packs: more games and deeper local knowledge packs.
- Better entity resolution: resolve referential phrases such as "this game", "that one", or "the game we just mentioned".

### Out Of Scope For Now

- No external guide-site crawling.
- No Steam Web API or Steam login.
- No embeddings / vector database unless a future task explicitly enters the RAG stage.
- Do not turn Rei into a guide site or generic chatbot.
