# Backend Bundle / Standalone Runtime Spike

## 中文

### 实验目标

本实验用于验证 ReiLink 的 FastAPI backend 是否可以打包成本地可执行文件，并由 Electron packaged app 启动。

这不是正式安装器方案，不包含代码签名、notarization、自动更新，也不把 backend binary 提交到仓库。

### 当前 backend 打包方式

当前原型使用 PyInstaller，从下面的入口打包：

```text
services/backend/packaging/backend_entry.py
```

打包入口会执行与开发模式等价的 uvicorn 启动：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动前会检查本地 `data` 目录和 knowledge catalog：

```text
data/knowledge/games/catalog.json
```

如果找不到必要数据，会输出明确错误并退出。

### 如何运行 package-backend

```bash
make package-backend
```

该命令会在 backend venv 中安装 PyInstaller 相关打包依赖，然后使用：

```text
services/backend/reilink_backend.spec
```

生成本地 backend binary。

### backend binary 产物路径

当前输出路径：

```text
services/backend/dist/reilink-backend
```

`services/backend/dist/` 和 `services/backend/build/` 已加入 `.gitignore`，不要提交 binary 或 build 产物。

### 如何测试 binary

在一个终端运行：

```bash
REILINK_PROJECT_ROOT=/Users/aragoto/Desktop/ReiLink \
services/backend/dist/reilink-backend
```

在另一个终端检查：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/setup/status
```

预期：

- `/api/health` 返回 `{"status":"ok"}`
- `/api/setup/status` 能返回 setup 状态
- 不输出 API key
- 能读取 `services/backend/.env`
- 能读取 `data/knowledge`
- memory/session 继续写入本地 `data/memory` 与 `data/session`

### Electron 如何使用 binary

Electron backend runtime 当前保留现有 fallback 顺序：

1. 如果外部 backend 已运行，直接使用。
2. 如果配置了 backend binary 且文件存在，优先启动 binary。
3. 如果 binary 不存在，fallback 到 repo-local `.venv` backend。
4. 如果都失败，显示中文错误。

可以通过环境变量指定 binary：

```bash
REILINK_BACKEND_BINARY=/Users/aragoto/Desktop/ReiLink/services/backend/dist/reilink-backend
```

如果显式指定的 binary 不存在，`auto` 模式会回退到 repo-local backend；`binary` 模式会显示错误并停止。

也可以显式选择 runtime 模式：

```bash
REILINK_BACKEND_RUNTIME=auto
REILINK_BACKEND_RUNTIME=binary
REILINK_BACKEND_RUNTIME=repo
```

默认是 `auto`。

### 路径与配置

`.env` 默认读取：

```text
services/backend/.env
```

也可以通过环境变量覆盖：

```bash
REILINK_BACKEND_ENV=/path/to/.env
```

项目根目录优先使用：

```bash
REILINK_PROJECT_ROOT=/Users/aragoto/Desktop/ReiLink
```

数据目录优先使用：

```bash
REILINK_DATA_DIR=/path/to/data
```

如果没有显式设置，backend 会从 binary 位置、当前工作目录和源码路径向上寻找包含 knowledge catalog 的 ReiLink 项目目录。

### Standalone App Packaging v1

当前 `make package-desktop` 会要求先生成 backend binary：

```bash
make package-backend
make package-desktop
```

如果 backend binary 不存在，desktop 打包会清晰失败，并提示先运行 `make package-backend`。

打包后 `.app` 内会包含：

```text
ReiLink.app/Contents/Resources/backend/reilink-backend
ReiLink.app/Contents/Resources/knowledge/games/catalog.json
ReiLink.app/Contents/Resources/knowledge/games/elden_ring/manifest.json
ReiLink.app/Contents/Resources/knowledge/games/elden_ring/snippets.json
ReiLink.app/Contents/Resources/knowledge/games/hollow_knight/manifest.json
ReiLink.app/Contents/Resources/knowledge/games/hollow_knight/snippets.json
```

`.env` 不会被复制进 `.app`。`data/memory`、`data/session` 和本地用户状态也不会被复制进 `.app`。API key 继续来自：

1. `REILINK_BACKEND_ENV` 指定的 env 文件
2. repo-local `services/backend/.env`
3. 当前环境变量中的 `DEEPSEEK_API_KEY`

如果都没有配置，前端 First Run / Provider Setup 会提示用户完成模型配置。

packaged app 启动 backend 的优先级为：

1. 外部 backend 已运行：直接使用。
2. `REILINK_BACKEND_BINARY` 指定的 binary：优先使用。
3. `.app` resources 内置 binary：使用 `Contents/Resources/backend/reilink-backend`。
4. repo-local `.venv` backend：作为开发 fallback。
5. 全部失败：显示中文错误。

standalone 模式下，Electron 会给 backend 传入：

```bash
REILINK_DATA_DIR="$HOME/Library/Application Support/ReiLink/data"
REILINK_KNOWLEDGE_DIR="ReiLink.app/Contents/Resources/knowledge/games"
```

其中 knowledge 是只读资源；memory、session、settings、logs 写入用户可写目录，不写入 `.app`。

### 如何测试 packaged app

```bash
make package-backend
make package-desktop
lsof -nP -iTCP:8000 -sTCP:LISTEN
open apps/desktop/release/ReiLink-darwin-arm64/ReiLink.app
curl http://127.0.0.1:8000/api/health
```

预期：

- UI 不是黑屏
- backend 来源显示“内置后端”
- 知识资源显示“内置知识资源”
- `/api/health` 返回 `{"status":"ok"}`
- 退出 app 后，本次 app 启动的 backend 会被关闭
- `.app` resources 中没有 `.env`、memory、session

### 当前限制

- 当前是本地未签名 macOS 开发构建，不是正式 installer。
- 尚未 code sign，也未 notarize。
- 当前不生成 DMG / pkg installer。
- 当前只验证 macOS 本地打包；backend binary 由当前 Python/PyInstaller 环境生成，实际架构跟随本机。
- DeepSeek API key 仍通过本地 `.env` 或环境变量提供，不会打包进 binary。
- 产物未签名，不能作为正式 release artifact。
- 仍未实现 installer、notarization、auto updater。

### 是否建议进入下一阶段 standalone packaging

建议继续进入下一阶段，但应拆成独立任务：

- 将 backend binary 复制到 Electron resources。
- 设计 production data dir，例如 `~/Library/Application Support/ReiLink/data`。
- 区分只读 bundled knowledge 和可写 memory/session。
- 增加迁移与首次运行初始化。
- 做 macOS 签名和 notarization 前的打包验证。

## English

### Goal

This spike verifies whether ReiLink's FastAPI backend can be packaged as a local executable and started by the Electron packaged app.

It is not a production installer flow. It does not include code signing, notarization, auto update, or committed backend binaries.

### Current Packaging Approach

The prototype uses PyInstaller with this entry point:

```text
services/backend/packaging/backend_entry.py
```

The executable starts uvicorn in the same shape as local development:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Before starting, it checks that the local data directory and knowledge catalog are available:

```text
data/knowledge/games/catalog.json
```

If required data is missing, the binary exits with a clear error.

### Running package-backend

```bash
make package-backend
```

This installs the PyInstaller packaging dependency into the backend venv and builds from:

```text
services/backend/reilink_backend.spec
```

### Output Path

The current binary output is:

```text
services/backend/dist/reilink-backend
```

`services/backend/dist/` and `services/backend/build/` are ignored by git. Do not commit generated binaries or build output.

### Testing the Binary

In one terminal:

```bash
REILINK_PROJECT_ROOT=/Users/aragoto/Desktop/ReiLink \
services/backend/dist/reilink-backend
```

In another terminal:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/setup/status
```

Expected behavior:

- `/api/health` returns `{"status":"ok"}`
- `/api/setup/status` returns setup status
- API keys are not printed
- `services/backend/.env` can be loaded
- `data/knowledge` can be read
- memory/session files continue to use local `data/memory` and `data/session`

### Electron Integration

The Electron backend runtime keeps the current safe fallback order:

1. Use an already-running external backend.
2. If a backend binary is configured and exists, start the binary.
3. If the binary is missing, fall back to the repo-local `.venv` backend.
4. If all options fail, show a clear Chinese error.

Use this environment variable to point Electron at a binary:

```bash
REILINK_BACKEND_BINARY=/Users/aragoto/Desktop/ReiLink/services/backend/dist/reilink-backend
```

If the explicitly configured binary does not exist, `auto` mode falls back to the repo-local backend; `binary` mode reports an error and stops.

Runtime mode can be forced with:

```bash
REILINK_BACKEND_RUNTIME=auto
REILINK_BACKEND_RUNTIME=binary
REILINK_BACKEND_RUNTIME=repo
```

The default mode is `auto`.

### Paths And Config

`.env` is loaded from:

```text
services/backend/.env
```

It can be overridden with:

```bash
REILINK_BACKEND_ENV=/path/to/.env
```

The project root can be set explicitly:

```bash
REILINK_PROJECT_ROOT=/Users/aragoto/Desktop/ReiLink
```

The data directory can be overridden with:

```bash
REILINK_DATA_DIR=/path/to/data
```

Without explicit settings, the backend searches upward from the binary path, current working directory, and source paths for a ReiLink project root containing the knowledge catalog.

### Standalone App Packaging v1

`make package-desktop` now expects the backend binary to exist first:

```bash
make package-backend
make package-desktop
```

If the backend binary is missing, desktop packaging fails with a clear message telling the user to run `make package-backend`.

The packaged `.app` contains:

```text
ReiLink.app/Contents/Resources/backend/reilink-backend
ReiLink.app/Contents/Resources/knowledge/games/catalog.json
ReiLink.app/Contents/Resources/knowledge/games/elden_ring/manifest.json
ReiLink.app/Contents/Resources/knowledge/games/elden_ring/snippets.json
ReiLink.app/Contents/Resources/knowledge/games/hollow_knight/manifest.json
ReiLink.app/Contents/Resources/knowledge/games/hollow_knight/snippets.json
```

`.env` is not copied into the app bundle. `data/memory`, `data/session`, and local user state are not copied either. API keys continue to come from:

1. an env file passed with `REILINK_BACKEND_ENV`
2. repo-local `services/backend/.env`
3. `DEEPSEEK_API_KEY` in the current environment

If none are configured, the frontend First Run / Provider Setup flow asks the user to configure the model provider.

The packaged app starts the backend in this order:

1. Use an already-running external backend.
2. Use the binary specified by `REILINK_BACKEND_BINARY`.
3. Use the bundled binary at `Contents/Resources/backend/reilink-backend`.
4. Fall back to the repo-local `.venv` backend for development.
5. If all options fail, show a clear Chinese error.

In standalone mode, Electron passes:

```bash
REILINK_DATA_DIR="$HOME/Library/Application Support/ReiLink/data"
REILINK_KNOWLEDGE_DIR="ReiLink.app/Contents/Resources/knowledge/games"
```

Knowledge is treated as read-only bundled content. Memory, session, settings, and logs are written to the user-writable data directory, not into the `.app`.

### Testing the Packaged App

```bash
make package-backend
make package-desktop
lsof -nP -iTCP:8000 -sTCP:LISTEN
open apps/desktop/release/ReiLink-darwin-arm64/ReiLink.app
curl http://127.0.0.1:8000/api/health
```

Expected behavior:

- the UI is not a black screen
- backend source shows the bundled backend
- knowledge source shows bundled knowledge
- `/api/health` returns `{"status":"ok"}`
- quitting the app stops the backend started by that app run
- app resources do not contain `.env`, memory, or session data

### Current Limitations

- This is an unsigned local macOS development build, not a production installer.
- Code signing and notarization are not implemented.
- DMG / pkg installer generation is not implemented.
- Only macOS local packaging is covered. The backend binary architecture follows the local Python/PyInstaller build environment.
- API keys remain local `.env` / environment configuration and are not bundled.
- The binary is unsigned and not suitable as a formal release artifact.
- Installer, notarization, and auto update are not part of this spike.

### Recommendation

Continue toward standalone app packaging in a dedicated follow-up:

- Copy the backend binary into Electron resources.
- Define a production data directory such as `~/Library/Application Support/ReiLink/data`.
- Split bundled read-only knowledge from writable memory/session data.
- Add first-run initialization and migration.
- Validate packaging before macOS signing and notarization.
