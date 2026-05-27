# Self Test Report

Updated: 2026-05-25

## Completed Modules

- Backend FastAPI service and routes
- Elden Ring process detector
- Rei-like persona engine
- Local Elden Ring knowledge search
- Dialogue agent with mock and OpenAI-compatible provider abstraction
- JSONL conversation memory
- Mock voice endpoints
- Electron React desktop renderer
- Backend, desktop unit, and Playwright E2E test definitions
- GitHub Actions CI workflow

## Test Commands

```bash
make test-backend
make test-desktop
make test-e2e
make lint
make typecheck
```

## Test Results

- `services/backend/.venv/bin/python -m pytest services/backend/tests`: passed, 16 tests.
- `cd apps/desktop && npm test -- --reporter verbose --pool=forks`: passed, 5 tests.
- `cd apps/desktop && npm run lint`: passed.
- `cd apps/desktop && npm run build`: passed.
- `make test-backend`: passed.
- `make test-desktop`: passed.
- `make lint`: passed.
- `make typecheck`: passed.
- Backend startup check: `uvicorn app.main:app --host 127.0.0.1 --port 8000` started successfully with local bind permission.
- Backend smoke check: `GET /api/health` returned `{"status":"ok"}` and `POST /api/chat` returned a Rei-style mock Margit reply while saving a JSONL conversation.
- `cd apps/desktop && npm run test:e2e`: blocked after local Vite dev server started because Playwright Chromium was not installed.
- `cd apps/desktop && npx playwright install chromium`: attempted with approved network access, but the browser download stalled for several minutes and was stopped to avoid a hanging process.

## Failed Items

- E2E execution is not fully verified on this machine until Playwright Chromium is downloaded.
- Initial `npm install` failed when Electron's binary postinstall download returned `socket hang up`; dependencies were installed with `ELECTRON_SKIP_BINARY_DOWNLOAD=1` so lint, unit tests, and build could run.

## Known Limitations

- Non-Windows process detection returns idle by design.
- Local knowledge retrieval is keyword based.
- Voice is mocked and does not record microphone input.
- Desktop avatar is an original placeholder.

## Next Step

- Run `cd apps/desktop && npx playwright install chromium` on a stable network, then `make test-e2e`.
- Run Electron itself after allowing the Electron binary download, or use `ELECTRON_SKIP_BINARY_DOWNLOAD=0 npm install` to fetch it.

## 2026-05-26 中文化与对话质量修复

已完成：
- UI、Persona Prompt、mock 回复、知识库内容切换为中文。
- 新增 Lightweight Intent Router：区分 casual_chat、identity_question、elden_ring_boss_strategy、elden_ring_location、elden_ring_build、elden_ring_general_help、unclear。
- /api/chat 改为 User Message -> Intent Router -> Optional Knowledge Retrieval -> Prompt Builder -> LLM Provider -> Response Validator/Post-processor -> Final Reply。
- Knowledge 只作为内部 context，不再直接输出 markdown 原文。
- 新增 DeepSeek OpenAI-compatible provider，读取 DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL。
- Response Validator 会拦截非中文、markdown header、过长或疑似 raw knowledge 的回复。

验证：
- `services/backend/.venv/bin/python -m pytest services/backend/tests`：23 passed。
- `cd apps/desktop && npm test`：5 passed。
- `cd apps/desktop && npm run lint`：passed。
- `cd apps/desktop && npm run build`：passed。
- 本地 smoke：`你是谁` 无 knowledge sources；`Margit 怎么打` 返回中文打法；`Margit 在哪` 返回位置；`how` 要求补充。

已知限制：
- Intent Router 仍是轻量规则，Phase 1 足够演示；后续可替换为小模型分类或 provider-assisted routing。
- Mock provider 是本地可演示生成器；真实自然度由 DeepSeek/OpenAI provider 决定。
