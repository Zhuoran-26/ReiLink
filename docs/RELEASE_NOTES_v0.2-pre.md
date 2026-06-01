# ReiLink v0.2-pre Release Notes

## 中文

### 概览

ReiLink v0.2-pre 是 MVP v0.1.1 之后的产品化补齐预发布版本。它主要面向 productization、public readiness、standalone runtime 和 multi-game knowledge maintenance，不是一个扩大产品范围的新功能版本。

v0.2-pre 的目标是让首次启动、开发启动、公开展示材料、独立应用运行时、本地数据目录、多游戏知识包维护和 release checklist 更清晰。当前预发布 tag 为 `reilink-v0.2-pre`；精确发布点以 git tag / history 为准。

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
- Standalone App Packaging v1：本地 macOS `.app` 可以作为未签名开发构建运行。
- Bundled backend binary：`make package-backend` 生成 PyInstaller backend binary，`make package-desktop` 会打入 `.app` resources。
- Bundled knowledge resources：sample knowledge resources 会随 packaged app 作为只读资源分发。
- Backend runtime priority：优先复用外部 backend，其次使用指定 binary、内置 binary，最后回退 repo-local backend。
- Backend auto-start and cleanup：没有外部 backend 时 app 可自动启动本地后端；退出时清理由 app 启动的后端进程。
- User data dir：packaged app 将 memory / session / settings / logs 写入 `~/Library/Application Support/ReiLink/data`。
- Local Data Controls：Settings 中新增“本地数据 / Local Data”，可查看路径、打开目录、查看 knowledge source，并复用 Demo Reset / reset controls。

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
- API key 仍通过本地环境或 `.env` 配置，不会内置进 App，也不提供云端账号或在线保存。
- backend binary 由 PyInstaller 生成，当前是 macOS 本地未签名开发构建。
- 当前没有 code signing / notarization / DMG installer / auto updater。
- 当前不是 App Store 或正式安装包。
- Windows / Linux 打包尚未完成。

### 升级 / 使用提示

建议在启动或准备 release 前运行：

```bash
make doctor
make validate-knowledge
make package-backend
make package-desktop
```

同时检查：

- `services/backend/.env` 是否存在且包含本地需要的 provider API key。
- `make dev-backend` 是否能启动开发 backend。
- `make dev-desktop` 是否能启动 desktop dev app。
- packaged app 是否能自动启动内置 backend，并显示 bundled knowledge。
- Settings 的“本地数据 / Local Data”是否显示 `~/Library/Application Support/ReiLink/data` 并能打开目录。
- Debug Panel / Prompt Preview 是否能展示当前游戏、知识包状态和 prompt context。

## English

### Overview

ReiLink v0.2-pre is a productization pre-release after MVP v0.1.1. It is focused on productization, public readiness, standalone runtime, and multi-game knowledge maintenance rather than broadening the product scope.

The goal is to make first run, developer startup, public showcase materials, standalone app runtime, local data directories, knowledge pack maintenance, and release checklist work clearer. The current pre-release tag is `reilink-v0.2-pre`; the exact release point should be read from git tags / history.

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
- Standalone App Packaging v1: the local macOS `.app` can run as an unsigned development build.
- Bundled backend binary: `make package-backend` creates the PyInstaller backend binary, and `make package-desktop` bundles it into `.app` resources.
- Bundled knowledge resources: sample knowledge resources are distributed as read-only packaged app resources.
- Backend runtime priority: reuse an external backend first, then use a configured binary, bundled binary, and repo-local fallback.
- Backend auto-start and cleanup: the app can auto-start the local backend when no external backend is present, and it cleans up app-started backend processes on quit.
- User data dir: the packaged app writes memory, session, settings, and logs to `~/Library/Application Support/ReiLink/data`.
- Local Data Controls: Settings now includes "本地数据 / Local Data" for showing paths, opening the directory, showing the knowledge source, and reusing Demo Reset / reset controls.

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
- API keys are still configured through the local environment or `.env`; they are not bundled into the app, and there is no cloud account or online key storage.
- The backend binary is generated by PyInstaller and currently targets unsigned local macOS development builds.
- There is no code signing, notarization, DMG installer, or auto updater yet.
- This is not an App Store app or a formal installer.
- Windows / Linux packaging is not complete yet.

### Upgrade / Usage Notes

Before local startup or release preparation, run:

```bash
make doctor
make validate-knowledge
make package-backend
make package-desktop
```

Also check:

- `services/backend/.env` exists and contains the local provider API key if needed.
- `make dev-backend` starts the development backend.
- `make dev-desktop` starts the desktop dev app.
- The packaged app auto-starts the bundled backend and reports bundled knowledge.
- Settings "本地数据 / Local Data" shows `~/Library/Application Support/ReiLink/data` and can open the directory.
- Debug Panel / Prompt Preview show the current game, knowledge pack state, and prompt context.
