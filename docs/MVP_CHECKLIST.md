# MVP v0.1 Checklist

## 中文

### 发布前验证

- [ ] Backend tests pass：运行 `make test-backend`。
- [ ] Desktop tests pass：运行 `make test-desktop`。
- [ ] Lint pass：运行 `make lint`。
- [ ] Build pass：运行 `make typecheck`。
- [ ] E2E pass：运行 `make test-e2e`。
- [ ] `git diff --check` pass：确认没有空白或补丁格式问题。
- [ ] 当前分支为 `dev/codex-reilink`。
- [ ] 工作区干净：`git status` 没有未提交修改。

### 仓库安全

- [ ] 没有 `.env`、`*.env` 或 `services/backend/.env` 被 tracked。
- [ ] 没有 `data/memory/*` 被 tracked。
- [ ] 没有 `data/session/*` 被 tracked。
- [ ] 没有 `node_modules/`、`.venv/`、`dist/`、`build/` 被 tracked。
- [ ] 没有真实 API key 出现在 README、docs、测试或日志中。

### 产品展示材料

- [ ] README 已更新，并包含中英双语项目简介、功能、运行方法、隐私说明和 Roadmap。
- [ ] `docs/DEMO_SCRIPT.md` 已准备，可按 6 个 demo 场景演示。
- [ ] `docs/MANUAL_EVAL_CASES.md` 已准备，可用于人工质量评估。
- [ ] `docs/TROUBLESHOOTING.md` 已准备，可快速处理常见启动和开发问题。
- [ ] Debug Panel 与 Prompt Preview 可以说明关键状态：`active_source`（当前来源）、`knowledge_available`（知识库是否可用）、`fallback_reason`（兜底原因）。

### MVP 范围确认

- [ ] 不新增 Live2D / Voice / Vision / Overlay。
- [ ] 不新增 Steam API、外部抓取、RAG 或 vector database。
- [ ] 不修改 persona prompt、memory 写入逻辑、game session 核心逻辑、semantic extraction 核心逻辑、proactive 核心逻辑或 model routing。
- [ ] Elden Ring 与 Hollow Knight sample knowledge packs 可正常切换。
- [ ] Unsupported game fallback 不会误用 Elden Ring 知识。

### 发布动作

- [ ] 文档和验证结果已提交到 `dev/codex-reilink`。
- [ ] `dev` 已 push：将 `dev pushed` 理解为开发分支已推送到远端。
- [ ] 如需要版本标记，创建 tag：`tag created` 表示已创建发布标签。
- [ ] 最终演示前重新拉起 backend 和 desktop，确认首页可用。

## English

### Pre-release Verification

- [ ] Backend tests pass: run `make test-backend`.
- [ ] Desktop tests pass: run `make test-desktop`.
- [ ] Lint pass: run `make lint`.
- [ ] Build pass: run `make typecheck`.
- [ ] E2E pass: run `make test-e2e`.
- [ ] `git diff --check` passes with no whitespace or patch-format issues.
- [ ] Current branch is `dev/codex-reilink`.
- [ ] Working tree is clean: `git status` shows no uncommitted changes.

### Repository Safety

- [ ] No `.env`, `*.env`, or `services/backend/.env` files are tracked.
- [ ] No `data/memory/*` files are tracked.
- [ ] No `data/session/*` files are tracked.
- [ ] No `node_modules/`, `.venv/`, `dist/`, or `build/` directories are tracked.
- [ ] No real API keys appear in README, docs, tests, or logs.

### Presentation Materials

- [ ] README is updated with bilingual overview, features, setup, privacy notes, and roadmap.
- [ ] `docs/DEMO_SCRIPT.md` is ready for the six demo scenes.
- [ ] `docs/MANUAL_EVAL_CASES.md` is ready for manual quality evaluation.
- [ ] `docs/TROUBLESHOOTING.md` is ready for common startup and development issues.
- [ ] Debug Panel and Prompt Preview can explain key states: `active_source` means active source, `knowledge_available` means whether local knowledge is available, and `fallback_reason` means why the app fell back.

### MVP Scope Check

- [ ] No Live2D / Voice / Vision / Overlay added.
- [ ] No Steam API, external crawling, RAG, or vector database added.
- [ ] No changes to persona prompts, memory write logic, game session core logic, semantic extraction core logic, proactive core logic, or model routing.
- [ ] Elden Ring and Hollow Knight sample knowledge packs switch correctly.
- [ ] Unsupported game fallback does not reuse Elden Ring knowledge.

### Release Actions

- [ ] Documentation and verification results are committed to `dev/codex-reilink`.
- [ ] `dev pushed`: the development branch has been pushed to the remote.
- [ ] If a release marker is needed, create a tag: `tag created` means the release tag exists.
- [ ] Before the final demo, restart backend and desktop and confirm the app opens correctly.
