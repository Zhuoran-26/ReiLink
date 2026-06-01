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

### 当前限制

- 当前 binary 仍依赖本地 `data` 目录，不是完整自包含 app。
- 当前 binary 仍建议通过 `REILINK_PROJECT_ROOT` 指向 repo 根目录。
- DeepSeek API key 仍通过本地 `.env` 或环境变量提供，不会打包进 binary。
- 产物未签名，不能作为正式 release artifact。
- 尚未把 binary 自动复制进 Electron `.app` resources。
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

### Current Limitations

- The binary still depends on a local `data` directory.
- `REILINK_PROJECT_ROOT` is still recommended for reliable local testing.
- API keys remain local `.env` / environment configuration and are not bundled.
- The binary is unsigned and not suitable as a formal release artifact.
- The binary is not yet copied into Electron `.app` resources.
- Installer, notarization, and auto update are not part of this spike.

### Recommendation

Continue toward standalone app packaging in a dedicated follow-up:

- Copy the backend binary into Electron resources.
- Define a production data directory such as `~/Library/Application Support/ReiLink/data`.
- Split bundled read-only knowledge from writable memory/session data.
- Add first-run initialization and migration.
- Validate packaging before macOS signing and notarization.
