# Context & Memory Release Hardening Checklist v0

Updated: 2026-06-20

This checklist is the release-readiness gate for the current Context & Memory system. It covers LLM-primary extraction, Candidate Memory, Memory UX auto-save / undo / pending hints, Memory Retrieval, Persona-Memory Eval, Session Archive Runtime, Archive Search, and Archive-to-Memory Candidate Bridge.

It does not introduce new runtime behavior.

## Git Safety

Before release hardening or packaging:

```bash
git status
git branch --show-current
git log --oneline -5
git diff --stat
```

Required branch:

```text
dev/codex-reilink
```

Do not push, merge `main`, rebase `main`, tag, reset, restore, or clean unless explicitly requested by the project owner.

## Automated Tests

Backend release-hardening baseline:

```bash
cd services/backend
. .venv/bin/activate
python -m pytest tests/test_qa_scenarios.py
python -m pytest
```

Desktop baseline when renderer UI, shared API contracts, Electron main, packaged runtime behavior, local storage, or bundled backend behavior changes:

```bash
cd apps/desktop
npm run lint
npm test -- --run
npm run build
```

Docs-only changes should at least run:

```bash
git diff --check
```

If QA parser tests or machine-readable QA JSON change, run the backend QA scenario test even when runtime code is unchanged.

## Packaged Build Order

When backend API, API schema, backend binary behavior, knowledge loading, bundled resources, local storage layout, Electron main, renderer UI, or packaged app behavior changes:

```bash
make package-backend
make package-desktop
```

Always package backend before desktop when backend code, backend resources, API schemas, or bundled backend behavior changed. This avoids testing a desktop build against a stale bundled backend.

Docs-only, QA JSON-only, and pure parser-test changes can skip packaged build and packaged smoke if no runtime, frontend, Electron, API, storage, or bundled-resource behavior changed.

## Packaged Smoke

Minimum packaged `.app` smoke when required:

1. Open `apps/desktop/release/ReiLink-darwin-<arch>/ReiLink.app` directly.
2. Confirm the app is not a black screen.
3. Confirm backend connected or `GET /api/health` returns ok.
4. Confirm Home / Chat input is visible and not obstructed.
5. Open Settings and Voice workspaces.
6. Open Memory workspace.
7. Confirm tabs include `待确认`, `已保存`, `本地数据`, `候选记忆`, and `最近会话` or `会话归档`.
8. Open `最近会话` / `会话归档`.
9. Confirm archive empty state or safe archive list is visible.
10. Confirm `归档当前会话` and `刷新` controls are visible.
11. Confirm delete / clear controls are visible when archive data exists.
12. Confirm archive search / scan controls do not expose raw transcript, raw prompt, raw JSON, secrets, or full local paths.
13. Quit the app.
14. Confirm the app-started backend has no residual process.

## Memory Manual Smoke

1. Send an explicit stable preference, such as `记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。`
2. Confirm the memory is saved or appears as a pending candidate according to the current guard path.
3. Confirm undo or ignore controls work where applicable.
4. Confirm accepted memory appears in Memory workspace saved memory.
5. Confirm pending / ignored / rejected / undone memory does not enter PromptMemoryBlock.
6. Confirm Prompt Preview / Debug shows safe summary only.
7. Confirm Rei's reply does not explain internal guard / candidate mechanics.

## Session Archive Manual Smoke

1. Open Memory workspace.
2. Open `最近会话` / `会话归档`.
3. Click `刷新`; empty archive should show a safe empty state.
4. Click `归档当前会话`; an empty timeline should skip safely and not error.
5. If session timeline has safe events, click `归档当前会话` and confirm a safe archive summary appears.
6. Search by keyword / game / boss where archive data exists.
7. Confirm search results are safe summaries only.
8. Click explicit archive-to-memory scan, such as `检查可保存偏好`.
9. Confirm only stable user preferences can become pending candidates.
10. Confirm search results do not automatically create memory candidates.
11. Confirm archive data never enters PromptMemoryBlock directly.

## Privacy And Safety

The following must stay true across docs, tests, runtime, Debug, Prompt Preview, Event Stream, Session Archive, and packaged app smoke:

- Raw prompt is not displayed, archived, searched, or injected from archive.
- Raw provider JSON is not displayed, archived, searched, or injected.
- API keys, `.env`, bearer tokens, Authorization headers, and secrets are not saved or displayed.
- Full local paths are not shown in Debug / Event Stream / Prompt Preview / archive surfaces.
- Full voice transcript is not archived by default.
- Voice audio is not saved by default.
- Assistant and proactive text are not treated as user facts.
- Pending, rejected, ignored, expired, or undone memory does not enter prompt.
- Session Archive does not enter PromptMemoryBlock.
- Archive Search does not enter PromptMemoryBlock.
- Archive-to-Memory Bridge only creates pending candidates through explicit user scan.
- Only accepted / active Long-term Memory can enter PromptMemoryBlock.
- Persona Core has priority over memory and archive-derived candidates.

## Known Limitations

- No vector search.
- No semantic archive search.
- No archive search auto-candidate generation.
- No prompt archive retrieval.
- No external memory provider.
- No automatic archive-to-memory conversion.
- No archive export.
- No advanced retention UI.
- No archive scan audit counts beyond current safe summaries.
- No TTS Strategy v2.
- No Overlay auto-show restore.
- No Live2D / Vision runtime.

## Before Push / Merge / Tag

1. Confirm branch is `dev/codex-reilink` or an approved feature branch cut from it.
2. Confirm automated tests passed.
3. Confirm required packaged build and smoke were completed or explicitly skipped with reason.
4. Confirm `git status` contains only intended files.
5. Confirm no `.env`, `*.env`, user data, memory data, session data, `node_modules`, `.venv`, `dist`, `build`, `__pycache__`, or `.DS_Store` is staged.
6. Confirm release notes are draft-only unless the owner explicitly asks to publish.
7. Do not push, merge, rebase, or tag without explicit owner instruction.
