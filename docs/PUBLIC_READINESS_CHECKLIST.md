# Public Readiness Checklist

## 中文

### 仓库安全

- [x] 没有 `.env`、`*.env` 或 `services/backend/.env` 被 tracked。
- [x] 没有 `data/memory/*` 或 `data/session/*` 被 tracked。
- [x] 没有 `node_modules/`、`.venv/`、`dist/` 或 `build/` 被 tracked。
- [x] 没有真实 DeepSeek API key、`sk-` token 或其他 secrets 出现在 tracked 文件中。

### CI / 验证

- [x] GitHub Actions workflow 已配置 backend tests，并使用 `LLM_PROVIDER=mock`，不依赖真实 DeepSeek API key。
- [x] GitHub Actions workflow 已配置 desktop lint / test / build。
- [x] E2E 已作为 `workflow_dispatch` 手动检查准备好。
- [ ] GitHub Actions 最新远端运行结果需在 GitHub 上确认。
- [x] 本地 stabilization pass 已重新确认 `make doctor`、`make validate-knowledge`、`make lint`、`make test-backend`、`make test-desktop`、`make typecheck`、`make package-backend`、`make package-desktop` 和 packaged app smoke test。

### v0.2-pre Release Sync

- [x] `reilink-v0.2-pre` tag / pre-release 已存在；精确发布点以 git tag / history 为准。
- [x] `make validate-knowledge` 已加入本地 release readiness 检查。
- [x] Standalone runtime stabilization check 已记录：`docs/V0.2_PRE_STABILIZATION_CHECK.md`。
- [x] Screenshot showcase assets 已存在于 `docs/assets/`。
- [x] Knowledge Pack Authoring Guide 已存在：`docs/KNOWLEDGE_PACK_AUTHORING.md`。
- [x] v0.2-pre release notes 已存在：`docs/RELEASE_NOTES_v0.2-pre.md`。
- [x] CI 不依赖真实 DeepSeek API key。
- [x] v0.1.1 public repository / showcase status 已确认；v0.2-pre 已公开为 pre-release。后续 runtime stabilization tag 仍需手动创建。

### 公开材料

- [x] MIT License 已添加。
- [x] README 包含 status、quick start、health check、privacy、disclaimer、license。
- [x] Demo screenshots 已整理到 `docs/assets/`。
- [x] README screenshot section 已更新。
- [x] Release notes screenshot links 已添加。
- [x] `docs/RELEASE_NOTES_v0.1.md` 已准备。
- [x] `docs/TROUBLESHOOTING.md` 已覆盖常见启动问题。

### 范围与声明

- [x] README 明确 Rei 是原创 companion persona。
- [x] README 明确项目不隶属于 Evangelion、FromSoftware 或 Team Cherry。
- [x] README 明确不使用官方 IP 元素。
- [x] 当前 public showcase 状态已确认；后续 pre-release / tag 仍需另行手动创建。
- [x] Sample knowledge packs 未发现 secrets、local paths 或 API key；商标与授权风险需发布者在公开前最终确认。

## English

### Repository Safety

- [x] No `.env`, `*.env`, or `services/backend/.env` files are tracked.
- [x] No `data/memory/*` or `data/session/*` files are tracked.
- [x] No `node_modules/`, `.venv/`, `dist/`, or `build/` directories are tracked.
- [x] No real DeepSeek API key, `sk-` token, or other secret appears in tracked files.

### CI / Verification

- [x] GitHub Actions workflow configures backend tests with `LLM_PROVIDER=mock` and does not require a real DeepSeek API key.
- [x] GitHub Actions workflow configures desktop lint / test / build.
- [x] E2E is prepared as a manual `workflow_dispatch` check.
- [ ] The latest remote GitHub Actions run still needs to be confirmed on GitHub.
- [x] The local stabilization pass re-confirmed `make doctor`, `make validate-knowledge`, `make lint`, `make test-backend`, `make test-desktop`, `make typecheck`, `make package-backend`, `make package-desktop`, and the packaged app smoke test.

### v0.2-pre Release Sync

- [x] The `reilink-v0.2-pre` tag / pre-release exists; the exact release point should be read from git tags / history.
- [x] `make validate-knowledge` is included in local release readiness checks.
- [x] Standalone runtime stabilization check is recorded in `docs/V0.2_PRE_STABILIZATION_CHECK.md`.
- [x] Screenshot showcase assets are present under `docs/assets/`.
- [x] Knowledge Pack Authoring Guide is present: `docs/KNOWLEDGE_PACK_AUTHORING.md`.
- [x] v0.2-pre release notes are present: `docs/RELEASE_NOTES_v0.2-pre.md`.
- [x] CI does not require a real DeepSeek API key.
- [x] v0.1.1 public repository / showcase status is confirmed; v0.2-pre is public as a pre-release. Any later runtime stabilization tag remains manual.

### Public Materials

- [x] MIT License is added.
- [x] README includes status, quick start, health check, privacy, disclaimer, and license.
- [x] Demo screenshots are organized under `docs/assets/`.
- [x] README screenshot section is updated.
- [x] Release notes screenshot links are added.
- [x] `docs/RELEASE_NOTES_v0.1.md` is ready.
- [x] `docs/TROUBLESHOOTING.md` covers common startup issues.

### Scope And Disclaimers

- [x] README clearly states Rei is an original companion persona.
- [x] README clearly states the project is not affiliated with Evangelion, FromSoftware, or Team Cherry.
- [x] README clearly states it does not use official IP elements.
- [x] Current public showcase status is confirmed; future pre-release / tag creation remains a separate manual step.
- [x] Sample knowledge packs show no secrets, local paths, or API keys; trademark and authorization risk should still be finally confirmed by the publisher before public release.
