# ReiLink v0.2-pre Release Notes

## 中文

### 概览

ReiLink v0.2-pre 是 MVP v0.1.1 之后的产品化补齐预发布文档。它主要面向 productization、public readiness 和 multi-game knowledge maintenance，不是一个扩大产品范围的新功能版本。

v0.2-pre 的目标是让首次启动、开发启动、公开展示材料、多游戏知识包维护和 release checklist 更清晰，方便之后创建 `reilink-v0.2-pre` tag / pre-release。

### 新增内容

- First Run / Provider Setup：首次启动时更清楚地提示 provider 与 API key 配置状态。
- Dev Startup / Health Check：补齐 `make doctor` 与本地启动诊断。
- Public Readiness：整理公开展示前的安全、CI、素材和范围检查。
- Screenshot showcase assets：整理 README / release notes 使用的截图展示素材。
- Game Detector：本地进程 / 应用名检测当前游戏。
- Manual Game Context Control：允许手动设置当前游戏上下文。
- Unsupported Game fallback：未支持游戏不会错误复用已支持游戏知识。
- Knowledge Pack Manifest：每个 supported sample pack 有明确 manifest。
- Knowledge Pack Validator：通过 `make validate-knowledge` 校验 catalog、manifest 和 snippets。
- Knowledge Pack Authoring Guide：新增知识包编写规范，便于后续扩展更多游戏。

### 仍然不包含

- Voice。
- Live2D。
- Overlay。
- Vision。
- full RAG / vector database。
- Steam API。
- multi-companion system。

### 已知限制

- Local process detection 仍是轻量实现，不等同于完整游戏平台集成。
- Knowledge packs 仍是 sample-scale，不是完整攻略库。
- “这个 / 那个游戏”这类复杂指代仍有限制。
- API key 仍通过本地 `.env` 配置，不提供云端账号或在线保存。
- 打包安装器尚未完成。

### 升级 / 使用提示

建议在启动或准备 release 前运行：

```bash
make doctor
make validate-knowledge
```

同时检查：

- `services/backend/.env` 是否存在且包含本地需要的 provider API key。
- `make dev-backend` 是否能启动 backend。
- `make dev-desktop` 是否能启动 desktop app。
- Debug Panel / Prompt Preview 是否能展示当前游戏、知识包状态和 prompt context。

## English

### Overview

ReiLink v0.2-pre is a productization pre-release document after MVP v0.1.1. It is focused on productization, public readiness, and multi-game knowledge maintenance rather than broadening the product scope.

The goal is to make first run, developer startup, public showcase materials, knowledge pack maintenance, and release checklist work clearer before a later `reilink-v0.2-pre` tag / pre-release.

### What's New

- First Run / Provider Setup: clearer provider and API key setup state during first run.
- Dev Startup / Health Check: `make doctor` and local startup diagnostics.
- Public Readiness: safety, CI, showcase material, and scope checks before public presentation.
- Screenshot showcase assets: screenshots prepared for README and release notes.
- Game Detector: lightweight local process / app-name detection for the active game.
- Manual Game Context Control: manual current-game context override.
- Unsupported Game fallback: unsupported games do not accidentally reuse supported-game knowledge.
- Knowledge Pack Manifest: each supported sample pack has an explicit manifest.
- Knowledge Pack Validator: `make validate-knowledge` checks catalog, manifest, and snippets.
- Knowledge Pack Authoring Guide: documentation for adding future game knowledge packs.

### Still Not Included

- Voice.
- Live2D.
- Overlay.
- Vision.
- full RAG / vector database.
- Steam API.
- multi-companion system.

### Known Limitations

- Local process detection is still lightweight and is not a full game-platform integration.
- Knowledge packs are still sample-scale, not complete guide databases.
- Complex references such as "this game" or "that game" remain limited.
- API keys are still configured through a local `.env`; there is no cloud account or online key storage.
- Installer / packaging work is not finished yet.

### Upgrade / Usage Notes

Before local startup or release preparation, run:

```bash
make doctor
make validate-knowledge
```

Also check:

- `services/backend/.env` exists and contains the local provider API key if needed.
- `make dev-backend` starts the backend.
- `make dev-desktop` starts the desktop app.
- Debug Panel / Prompt Preview show the current game, knowledge pack state, and prompt context.
