# Project Status

Updated: 2026-05-31

## Current Stage

ReiLink is in an incremental local MVP stage focused on a Chinese-first desktop AI companion for single-player game players.

The current sample game is Elden Ring, with the knowledge and detector layers structured so future games can be added through registries and catalogs rather than hardcoded paths.

## Current Branch

```text
dev/codex-reilink
```

## Latest Stable Implementation Commit

```text
2f2d629 feat: add local game detector
```

This is the latest verified implementation baseline before the documentation cleanup commit.

## Completed Major Capabilities

- FastAPI backend and Electron/React desktop shell.
- DeepSeek-compatible LLM provider path with model routing.
- Minimal default persona with guarded fallback.
- Game Session state for current game, boss, location, and progress.
- Semantic Extraction for game state and memory candidates.
- Pending Memory review before long-term memory insertion.
- Prompt Preview and Debug Dashboard surfaces.
- Settings Panel with persisted app settings.
- Proactive Companion behavior with cooldown safeguards.
- Game Knowledge Layer v1 based on local curated snippets.
- Game Catalog / Multi-game Knowledge Interface v1.
- Game Detector v2 with local mockable process/app detection and registry mapping.

## Current Data Scope

- `elden_ring` is the only populated sample game.
- Future game IDs are expected to be added through `data/games/game_registry.json` and `data/knowledge/games/catalog.json`.
- No Steam API, Steam login, external crawling, vector database, Live2D, Voice, Vision, or Overlay is currently part of the implemented scope.

## Verification Baseline

For the latest implementation baseline:

```text
backend tests: passed
desktop tests: passed
desktop build: passed
lint: passed
desktop e2e: passed
```

For documentation-only updates, `git diff --check` is sufficient unless a task asks for more.
