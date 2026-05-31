# Troubleshooting

## 中文

### Backend disconnected（后端未连接）

现象：

- Desktop 显示“未连接”。
- Chat 请求失败。
- Debug 数据为空或停留在旧状态。

处理：

```bash
make dev-backend
```

确认 backend 地址为 `http://127.0.0.1:8000`。再启动或刷新 desktop：

```bash
make dev-desktop
```

### DeepSeek API key missing（DeepSeek key 缺失）

现象：

- `LLM_PROVIDER=deepseek` 时回复失败。
- 后端日志提示 API key missing 或 provider configuration error。

处理：

- 在 `services/backend/.env` 中配置 `DEEPSEEK_API_KEY`。
- 不要把真实 key 提交到 git。
- 无 key 演示时使用 `LLM_PROVIDER=mock`。

示例：

```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### SSL certificate issue on macOS（macOS 证书问题）

现象：

- Python / provider 请求出现 certificate verify failed。
- 依赖安装或 HTTPS 请求失败。

处理：

- 确认系统时间正确。
- 更新 Python / certifi 证书。
- 如果使用 python.org 安装包，可运行其自带的 Install Certificates 脚本。
- 不要在代码里关闭 SSL 校验作为长期方案。

### Electron binary download issue（Electron 下载失败）

现象：

- `npm install` 时 Electron binary 下载失败。
- 只需要跑 renderer lint / unit tests / build。

处理：

```bash
cd apps/desktop
ELECTRON_SKIP_BINARY_DOWNLOAD=1 npm install
```

说明：这足够运行 renderer lint、unit tests 和 build。若要运行 Electron shell，仍需要 Electron binary。

### GitHub push HTTP/1.1 workaround（GitHub push HTTP/1.1 兼容处理）

现象：

- `git push` 失败，出现 HTTP/2 stream、RPC failed 或 early EOF。

处理：

```bash
git config --global http.version HTTP/1.1
git push
```

如果问题消失，后续可继续使用 HTTP/1.1。不要在未确认远端状态时重复 force push。

### Git gc warning（Git 垃圾回收警告）

现象：

- Git 提示 `gc`、`loose objects` 或需要 prune。

处理：

```bash
git gc
```

如果仓库正在被其他任务使用，先确认没有并发 git 操作。

### GitHub Actions lint failure（CI lint 失败）

现象：

- 本地能运行，但 GitHub Actions 的 lint job 失败。

处理：

```bash
cd apps/desktop
npm run lint
```

常见原因：

- TypeScript 类型没有同步更新。
- 测试 fixture 缺少新字段。
- UI 文案改动后测试断言没更新。

### .env not loaded（环境变量未加载）

现象：

- 明明写了 `.env`，后端仍提示 provider 未配置。
- DeepSeek key 未被读取。

处理：

- 确认文件路径是 `services/backend/.env`。
- 确认变量格式为 `KEY=value`，不要写多余空格。
- 重启 backend。
- 检查 Debug Provider 中 `env_file_loaded`（环境文件是否加载）。

### Codex compact / stream disconnected（Codex 上下文压缩或流断开）

现象：

- Codex 会话提示 compact、resume 或 stream disconnected。
- 长任务中断后需要继续。

处理：

- 先运行 `git status` 确认当前工作区。
- 查看最近 diff：`git diff --stat`。
- 如果已有部分改动，继续在当前分支上收尾，不要重置用户改动。
- 如果任务目标不清晰，先查看 `AGENTS.md` 和相关 docs。

## English

### Backend Disconnected

Symptoms:

- Desktop shows disconnected.
- Chat requests fail.
- Debug data is empty or stale.

Fix:

```bash
make dev-backend
```

Confirm the backend is available at `http://127.0.0.1:8000`. Then start or refresh the desktop renderer:

```bash
make dev-desktop
```

### DeepSeek API Key Missing

Symptoms:

- Replies fail when `LLM_PROVIDER=deepseek`.
- Backend logs mention a missing API key or provider configuration error.

Fix:

- Configure `DEEPSEEK_API_KEY` in `services/backend/.env`.
- Never commit real keys.
- Use `LLM_PROVIDER=mock` for demos without a key.

Example:

```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### SSL Certificate Issue on macOS

Symptoms:

- Python or provider requests fail with certificate verify failed.
- Dependency install or HTTPS requests fail.

Fix:

- Confirm system time is correct.
- Update Python / certifi certificates.
- If using the python.org installer, run its Install Certificates script.
- Do not disable SSL verification in application code as a long-term fix.

### Electron Binary Download Issue

Symptoms:

- `npm install` fails while downloading the Electron binary.
- You only need renderer lint, unit tests, or build checks.

Fix:

```bash
cd apps/desktop
ELECTRON_SKIP_BINARY_DOWNLOAD=1 npm install
```

This is enough for renderer lint, unit tests, and build. Running the Electron shell still requires the Electron binary.

### GitHub Push HTTP/1.1 Workaround

Symptoms:

- `git push` fails with HTTP/2 stream, RPC failed, or early EOF errors.

Fix:

```bash
git config --global http.version HTTP/1.1
git push
```

If the issue disappears, keep using HTTP/1.1. Do not repeat force pushes without confirming the remote state.

### Git GC Warning

Symptoms:

- Git reports `gc`, `loose objects`, or prune warnings.

Fix:

```bash
git gc
```

If another task may be using the repository, confirm there is no concurrent git operation first.

### GitHub Actions Lint Failure

Symptoms:

- The app works locally, but the GitHub Actions lint job fails.

Fix:

```bash
cd apps/desktop
npm run lint
```

Common causes:

- TypeScript API types were not updated.
- Test fixtures are missing new fields.
- UI copy changed but test assertions were not updated.

### .env Not Loaded

Symptoms:

- `.env` exists, but the backend still reports missing provider configuration.
- DeepSeek key is not read.

Fix:

- Confirm the file path is `services/backend/.env`.
- Use `KEY=value` lines without extra formatting.
- Restart the backend.
- Check `env_file_loaded` in Debug Provider.

### Codex Compact / Stream Disconnected

Symptoms:

- Codex reports compact, resume, or stream disconnected.
- A long-running task needs to continue after interruption.

Fix:

- Run `git status` first to inspect the working tree.
- Inspect recent changes with `git diff --stat`.
- If partial changes exist, continue from the current branch and do not reset user work.
- If the task goal is unclear, read `AGENTS.md` and relevant docs before editing.
