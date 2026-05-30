# Safe Git Flow

Default branch for Codex work: `dev/codex-reilink`.

Do not push automatically. Push only after the user explicitly says `push`.

Before each commit:

1. Run backend tests:
   `services/backend/.venv/bin/python -m pytest services/backend/tests`
2. Run desktop tests:
   `npm test` in `apps/desktop`
3. Run desktop build:
   `npm run build` in `apps/desktop`
4. Check status:
   `git status --short --branch`
5. Show diff stat:
   `git diff --stat`
6. Check that no local secrets or memory files are staged:
   `.env`, `*.env`, `services/backend/.env`, `data/memory/user_profile.json`, `data/memory/episodes.jsonl`
7. Commit with a clear message such as:
   `fix: improve companion persona guardrails`

Never commit:

- API keys or provider secrets
- Local `.env` files
- `node_modules/`
- Python virtualenvs
- Build outputs
- Local memory data
