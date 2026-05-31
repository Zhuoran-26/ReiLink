# ReiLink Agent Instructions

## Project

ReiLink is a desktop AI companion for single-player game players.

Current stack:
- Backend: FastAPI / Python
- Desktop: Electron / React / TypeScript
- LLM: DeepSeek provider
- Current default persona: minimal
- Current dev branch: `dev/codex-reilink`

Current product direction:
- Chinese-first AI companion
- Multi-game / multi-character future
- Current sample game: Elden Ring
- Current sample companion: Rei-like original character

Do not use Evangelion, Rei Ayanami, NERV, or any official IP elements.

## Before Every Task

Before modifying code, run and report:

```bash
git status
git branch --show-current
git log --oneline -5
git diff --stat
```

If the working tree is not clean, report it first. Do not continue automatically.

## Git Rules

Work on:

```text
dev/codex-reilink
```

Do not work on `main` unless explicitly asked.

Never commit:

```text
.env
*.env
services/backend/.env
data/memory/*
data/session/*
node_modules/
.venv/
dist/
build/
__pycache__/
.DS_Store
```

After finishing a task:
1. Run tests.
2. Commit if tests pass.
3. Do not push unless explicitly asked.

## Required Tests

Backend:

```bash
cd services/backend
. .venv/bin/activate
python -m pytest
```

Desktop:

```bash
cd apps/desktop
npm run lint
npm test
npm run build
```

If tests are skipped, explain why.

## Core Modules

Main backend modules:
- persona_engine
- dialogue_agent
- game_session
- memory
- semantic_extraction
- game_knowledge
- proactive
- app_settings

Main frontend areas:
- Chat UI
- Settings
- Pending Memory
- Game Session Debug
- Semantic Extraction Debug
- Prompt Preview
- Proactive Debug
- Knowledge Debug

## Persona Rules

Keep generation LLM-first.

Do not hardcode Rei replies.

Default persona is minimal; guarded is fallback.

Rei should feel:
- quiet
- restrained
- low-emotion
- lightly caring
- not sweet
- not 客服
- not 心理咨询师
- not 攻略站
- not generic AI assistant

Avoid:
- "作为 AI"
- "作为陪伴者"
- "我会尽力理解你"
- "喜欢的定义因人而异"
- repeated "我在这里 / 我听见了 / 别想太多"
- bracketed stage actions
- fake poetic prose
- long guide-style replies unless user asks for detail

## Memory Rules

Long-term memory must be conservative.

Pending memory must be accepted before entering long-term memory.

Pending memory must not be injected into prompts.

Accepted memory can be injected as summary.

Temporary game state should not become long-term memory unless confirmed.

## Game State Rules

Priority:

```text
current user message > session focus > fresh game state > long-term memory
```

Do not let stale boss memory override fresh current state.

Negation matters:

```text
没打过 / 没过 / 差点过 / 还没过 != cleared
终于过了 / 打过了 / 赢了 = cleared
```

## Knowledge Rules

Knowledge layer provides factual context only.

It must not directly generate Rei replies.

Do not turn Rei into an 攻略站.

No RAG/vector database unless explicitly requested.

## Proactive Rules

Proactive messages must be quiet and low-frequency.

They must:
- obey cooldown
- require user activity after one proactive message
- not enter pending memory
- not change game session state
- be marked as proactive

## UI Rules

UI language should be Simplified Chinese.

Avoid engineering labels in user-facing UI.

Prefer:
- 当前游戏
- 当前 Boss
- 游戏状态
- 待确认记忆
- 主动陪伴
- 模型路由
- 语义识别
- Prompt 预览

Raw JSON can remain English but should be collapsed by default.

## Task Discipline

Prefer targeted patches.

Do not combine unrelated changes.

Do not change persona for backend-state tasks.

Do not change backend logic for UI-only tasks.

Do not add Live2D / Voice / Vision / Overlay unless explicitly requested.

Always report:
- files changed
- tests run
- commit hash
- whether push was performed
