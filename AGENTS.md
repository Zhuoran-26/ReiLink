# ReiLink Agent Instructions

## Source Of Truth

ReiLink is a desktop AI companion for single-player game players.

If `AGENTS.md` or any file under `docs/` conflicts with the current code or git history, treat the code and git history as authoritative. Report the conflict before continuing.

Use `docs/PROJECT_STATUS.md` for dynamic project status. Do not maintain a detailed completed-feature list in this file.

## Before Every Task

Before modifying code or docs, run and report:

```bash
git status
git branch --show-current
git log --oneline -5
git diff --stat
```

If the working tree is not clean, report it first. Do not continue automatically unless the user explicitly confirms.

## Branch And Git Rules

Work on:

```text
dev/codex-reilink
```

Do not work on `main` unless explicitly asked.

Do not push unless explicitly asked.

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
1. Run the required verification.
2. Commit if verification passes.
3. Report the commit hash and whether push was performed.

## Required Verification

Default backend verification:

```bash
cd services/backend
. .venv/bin/activate
python -m pytest
```

Default desktop verification:

```bash
cd apps/desktop
npm run lint
npm test
npm run build
```

For documentation-only changes, `git diff --check` is sufficient unless the user asks for more.

If any verification is skipped, explain why.

## Frontend Visual Smoke Test

When a task touches any of the following areas:

- Desktop UI
- Electron main process
- packaging / packaged app
- onboarding
- settings
- chat behavior
- message scrolling
- proactive UI
- debug panel
- user-visible error states

After automated tests pass, also run one frontend visual smoke test:

1. Start the backend or confirm backend status.
2. Open the desktop dev app or packaged app.
3. Confirm the interface is not a black screen.
4. Confirm the main chat area, input, settings area, and right-side panels render normally.
5. If the task changed a specific UI, click or inspect the relevant entry point.
6. In the completion report, state what the visual smoke test checked.
7. If the visual smoke test cannot be run, explain why.

This does not apply to pure backend, pure documentation, pure test-only, or pure knowledge validator tasks.

Do not use the visual smoke test as a replacement for automated tests; it is an extra check.

Do not commit screenshots unless the task explicitly asks for them.

## Product Principles

- Chinese-first AI companion for single-player game players.
- Keep generation LLM-first; do not hardcode Rei replies.
- Default persona is minimal; guarded is fallback.
- Rei should feel quiet, restrained, low-emotion, lightly caring, not sweet, not customer service, not a therapist, not a guide site, and not a generic AI assistant.
- Knowledge provides factual context only and must not directly generate Rei replies.
- UI language should be Simplified Chinese and avoid engineering labels in user-facing surfaces.
- Do not use Evangelion, Rei Ayanami, NERV, or any official IP elements.

## Stable Boundaries

Do not change persona prompts, memory write logic, game session core logic, knowledge core logic, proactive behavior, or model routing unless the task explicitly asks for it.

Do not add Live2D, Voice, Vision, Overlay, Steam login, Steam Web API, external crawling, vector database, or complex RAG unless explicitly requested.

Prefer targeted patches. Do not combine unrelated changes.

Always report:
- files changed
- verification run
- commit hash
- whether push was performed
