# Architecture

ReiLink is split into a FastAPI backend and an Electron/React desktop app. Local JSON files hold development-time game, knowledge, memory, and session data.

## Backend

Backend code lives under `services/backend/app`.

- `api/`: FastAPI routes for chat, settings, game status, detection, memory, debug, and health endpoints.
- `schemas/`: shared API request and response models.
- `core/`: configuration and app-level constants.
- `modules/`: product logic used by the routes and dialogue pipeline.

Important backend modules:

- `dialogue_agent`: orchestrates settings, session state, detector output, knowledge context, model routing, provider calls, and prompt preview data.
- `persona_engine`: loads persona configuration and builds system prompt context.
- `game_session`: tracks temporary current game, boss, location, and progress state.
- `game_detector`: performs local, mockable game detection from process or app names.
- `knowledge`: matches games through the catalog and retrieves small factual snippets.
- `memory`: stores accepted long-term memory and pending memory separately.
- `semantic_extraction`: extracts candidate game state and memory signals from user messages.
- `proactive`: creates low-frequency proactive companion messages.
- `app_settings`: persists user-facing settings such as debug mode and auto game detection.

## Desktop

Desktop code lives under `apps/desktop`.

- `src/main/`: Electron main process.
- `src/renderer/`: React UI, including chat, settings, prompt preview, pending memory, and debug panels.
- `src/shared/`: TypeScript API types and client helpers shared by renderer code.
- `tests/e2e/`: Playwright desktop smoke tests.

The UI should stay Chinese-first and should present debug information with user-friendly labels. Raw JSON may remain available for diagnosis, but should stay collapsed by default.

## Data Files

- `data/games/game_registry.json`: local game registry and process-name mapping.
- `data/knowledge/games/catalog.json`: enabled knowledge games and snippet paths.
- `data/knowledge/games/*/snippets.json`: small curated factual snippets.
- `data/memory/*`: local memory data; never commit.
- `data/session/*`: local session state; never commit.

## Runtime Flow

```text
Desktop UI
-> FastAPI route
-> app settings + game detector + game session + semantic extraction
-> knowledge catalog/retriever when relevant
-> prompt preview + model routing + LLM provider
-> final Rei response
```

Detector and knowledge outputs provide context only. They should not turn Rei into a guide site or replace LLM-first generation.
