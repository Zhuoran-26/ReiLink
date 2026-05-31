# Public Readiness Checklist

## 中文

### 仓库安全

- [ ] 没有 `.env`、`*.env` 或 `services/backend/.env` 被 tracked。
- [ ] 没有 `data/memory/*` 或 `data/session/*` 被 tracked。
- [ ] 没有 `node_modules/`、`.venv/`、`dist/` 或 `build/` 被 tracked。
- [ ] 没有真实 DeepSeek API key、`sk-` token 或其他 secrets 出现在 tracked 文件中。

### CI / 验证

- [ ] GitHub Actions backend tests 通过。
- [ ] GitHub Actions desktop lint / test / build 通过。
- [ ] E2E 已作为手动或 optional 检查准备好。
- [ ] 本地 `make doctor`、`make lint`、`make test`、`make typecheck` 通过。

### 公开材料

- [ ] MIT License 已添加。
- [ ] README 包含 status、quick start、health check、privacy、disclaimer、license。
- [x] Demo screenshots 已整理到 `docs/assets/`。
- [x] README screenshot section 已更新。
- [x] Release notes screenshot links 已添加。
- [ ] `docs/RELEASE_NOTES_v0.1.md` 已准备。
- [ ] `docs/TROUBLESHOOTING.md` 已覆盖常见启动问题。

### 范围与声明

- [ ] README 明确 Rei 是原创 companion persona。
- [ ] README 明确项目不隶属于 Evangelion、FromSoftware 或 Team Cherry。
- [ ] README 明确不使用官方 IP 元素。
- [ ] 已决定仓库公开 / 私有策略。
- [ ] 如公开仓库，确认 sample knowledge packs 不包含敏感或未授权材料。

## English

### Repository Safety

- [ ] No `.env`, `*.env`, or `services/backend/.env` files are tracked.
- [ ] No `data/memory/*` or `data/session/*` files are tracked.
- [ ] No `node_modules/`, `.venv/`, `dist/`, or `build/` directories are tracked.
- [ ] No real DeepSeek API key, `sk-` token, or other secret appears in tracked files.

### CI / Verification

- [ ] GitHub Actions backend tests pass.
- [ ] GitHub Actions desktop lint / test / build pass.
- [ ] E2E is prepared as a manual or optional check.
- [ ] Local `make doctor`, `make lint`, `make test`, and `make typecheck` pass.

### Public Materials

- [ ] MIT License is added.
- [ ] README includes status, quick start, health check, privacy, disclaimer, and license.
- [x] Demo screenshots are organized under `docs/assets/`.
- [x] README screenshot section is updated.
- [x] Release notes screenshot links are added.
- [ ] `docs/RELEASE_NOTES_v0.1.md` is ready.
- [ ] `docs/TROUBLESHOOTING.md` covers common startup issues.

### Scope And Disclaimers

- [ ] README clearly states Rei is an original companion persona.
- [ ] README clearly states the project is not affiliated with Evangelion, FromSoftware, or Team Cherry.
- [ ] README clearly states it does not use official IP elements.
- [ ] Public / private repository decision is made.
- [ ] If public, sample knowledge packs have been checked for sensitive or unauthorized material.
