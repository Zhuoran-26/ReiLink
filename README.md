# ReiLink

ReiLink is a Phase 1 MVP for a local AI game companion desktop app. This phase supports one game, Elden Ring, and one original Rei-like companion persona.

The implemented loop is:

Detect Elden Ring process -> build persona prompt -> search local Elden Ring knowledge -> generate a mock or OpenAI-compatible reply -> show it in the desktop UI -> save JSONL conversation history.

## Stack

- Backend: Python, FastAPI, psutil, pytest
- Desktop: Electron, React, TypeScript, Vite
- Tests: pytest, Vitest, React Testing Library, Playwright
- Storage: local JSONL files under `data/conversations`

## Quick Start

```bash
cp .env.example .env
make install-backend
make install-desktop
```

Run backend:

```bash
make dev-backend
```

Run desktop renderer:

```bash
make dev-desktop
```

Open `http://127.0.0.1:5173` during development, or run Electron from `apps/desktop` with `npm run dev:electron`.

## Test

```bash
make test
make test-backend
make test-desktop
make test-e2e
make lint
make typecheck
```

If Electron's binary download is unstable during install, run:

```bash
cd apps/desktop
ELECTRON_SKIP_BINARY_DOWNLOAD=1 npm install
```

That is enough for renderer lint, unit tests, and build checks. Running the packaged Electron shell still requires the Electron binary.

## Provider Configuration

Mock mode is the default and needs no API key.

To use an OpenAI-compatible provider, set:

```bash
LLM_PROVIDER=openai-compatible
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=...
```

STT and TTS are mocked in Phase 1. Voice endpoints exist but no continuous microphone listening is implemented.

## Current Limitations

- Elden Ring process detection is Windows-first and returns idle on non-Windows systems.
- Knowledge search is keyword based local file retrieval, not full RAG.
- The avatar is an original placeholder, not official or copyrighted game or anime artwork.
- Voice is API placeholder plus mock fallback.


## DeepSeek 配置

ReiLink 支持 DeepSeek 的 OpenAI-compatible API。

```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

如果 `LLM_PROVIDER=deepseek` 但没有配置 `DEEPSEEK_API_KEY`，后端会返回清晰错误，不会崩溃。Phase 1 默认仍是 `LLM_PROVIDER=mock`，无 key 也可以中文演示。
