# LLM-primary Guarded Extraction Architecture v1 Pilot

Updated: 2026-06-17

Status: implemented pilot. ReiLink now has a foreground LLM-primary semantic reader for chat input when an LLM provider is configured, followed by strict JSON/schema validation and deterministic guard. It preserves rule fallback when provider is unavailable or the guarded candidate is unsafe. This pilot does not add embeddings or vector databases and does not change memory, proactive, persona, voice core behavior, or Overlay runtime boundaries.

## Purpose

ReiLink needs semantic extraction that scales beyond a small rule and alias set. The next architecture should make the LLM the primary semantic reader while keeping state writes deterministic and guarded.

The key rule is:

```text
LLM understands and proposes.
Schema validates.
Guard decides.
Deterministic code applies or refuses.
```

The LLM must not directly write game context, memory, proactive state, persona state, or session state.

## Why Move Beyond Rule-first

Rule-first has been useful:

- It is stable for early single-game and low-entity-count cases.
- It is predictable and easy to reason about.
- It is easy to unit test.
- It works when no provider is configured.
- It provides deterministic exact matches that are still valuable for grounding.

But rule-first is now the wrong primary semantic reader:

- Multi-game expansion makes alias / regex / typo tables unbounded.
- Voice ASR can produce near-sound mistakes, partial entities, and bad segmentation that exact rules miss.
- Slang, boss nicknames, item variants, regions, and mechanics differ per game and per player.
- Rule confidence is not semantic correctness probability; an exact string match can still misunderstand intent.
- Rule no-op does not mean the user's input is semantically unclear.
- LLM reply generation can understand a user mention while game context remains stale, creating a split between what Rei says and what ReiLink state believes.
- Existing Shadow Mode observes LLM candidates but does not participate in the foreground path, so the system can look LLM-aware while still mutating state through rules only.

New direction:

- LLM is the primary semantic reader for typed and voice inputs.
- Rules move behind the LLM as guard, validation, cross-check, and fallback.
- Game catalog data is a grounding / validation source, not a giant rule table.
- Deterministic code still owns `apply`, `ask_clarification`, `candidate_only`, `no_op`, and `fallback_to_rule`.

## Pipeline

```text
Input
  - text input
  - voice confirm-send input
  - voice direct conversation input

-> Source marker
  - text
  - voice_confirmed
  - voice_direct

-> LLM primary semantic extraction
  - structured candidate
  - intent
  - entity
  - confidence
  - evidence summary
  - uncertainty

-> Schema validation
  - strict JSON
  - allowed fields
  - enums
  - value ranges

-> Guard decision
  - catalog grounding
  - context consistency
  - conflict detection
  - risk policy
  - confidence calibration

-> Decision
  - apply
  - ask_clarification
  - candidate_only
  - no_op
  - fallback_to_rule

-> State update
  - only deterministic apply path can update game context

-> Safe trace
  - Debug / Game workspace / Event Stream
```

Important invariants:

- Typed text uses the same LLM-primary extraction path as voice.
- `voice_confirmed` and `voice_direct` differ only in source reliability, trace, and guard thresholds.
- Direct Conversation auto-send still enters the normal chat flow and the same extraction pipeline.
- Confirm-send voice input has higher source reliability than direct voice because the user confirmed or edited the transcript.
- Rules do not overwrite LLM semantic confidence. They can raise or lower grounding / context confidence through explicit guard logic.
- Low confidence writes nothing.
- Conflicts are not silently overwritten.

## Runtime Pilot Scope

The v1 pilot applies only low-risk game-session fields:

- `game`
- `boss`
- `death_count_absolute`
- `death_count_increment`
- `frustration`
- `boss_cleared`
- `guide_request`
- `strategy_request`

All sources enter the same path:

- typed chat text: `input_source=text`
- confirmed voice transcript: `input_source=voice_confirmed`
- Direct Conversation auto-send transcript: `input_source=voice_direct`

The LLM never writes state directly. It returns a candidate. Pydantic schema validation rejects invalid JSON, unknown enum values, and out-of-range counts. The deterministic guard then emits exactly one of:

- `apply`
- `ask_clarification`
- `candidate_only`
- `no_op`
- `fallback_to_rule`

Only `apply` creates a `semantic_game_event` with `guard_source=llm_primary`; `GameSessionStore` applies that event deterministically. Legacy Shadow Mode remains observability-only.

## LLM Candidate Schema v1 Pilot

The foreground LLM returns one strict JSON object. It uses constrained IDs for the current pilot and must keep memory / proactive candidates disabled.

```json
{
  "is_game_related": true,
  "confidence": "high",
  "game": {"operation": "set", "value": "elden_ring", "confidence": "high"},
  "boss": {"operation": "set", "value": "margit", "surface_label": null, "confidence": "high"},
  "death_count": {"operation": "none", "value": null, "confidence": "low"},
  "frustration": {"operation": "none", "confidence": "low"},
  "boss_cleared": {"operation": "none", "confidence": "low"},
  "guide_request": {"value": false, "confidence": "low"},
  "strategy_request": {"value": false, "confidence": "low"},
  "memory_candidate": {"should_create": false, "kind": "none", "safe_summary": null, "confidence": "low"},
  "proactive_signal": {"type": "none", "confidence": "low", "reason": ""},
  "reasoning_summary": "safe short summary, no raw user text"
}
```

### Required Fields

Base fields:

- `is_game_related`: boolean.
- `confidence`: `high`, `medium`, or `low`.

Entity fields:

- `game.operation`: `set`, `keep`, `none`, `unknown`.
- `game.value`: `elden_ring`, `hollow_knight`, `unknown`, or `null`.
- `boss.operation`: `set`, `keep`, `clear`, `none`, `unknown`.
- `boss.value`: `margit`, `tree_sentinel`, `false_knight`, `unknown`, or `null`.
- `boss.surface_label`: nullable safe short label.

Event fields:

- `death_count.operation`: `set`, `increment`, `none`, `unknown`; value range `0..99`.
- `frustration.operation`: `raise`, `lower`, `clear`, `keep`, `none`, `unknown`.
- `boss_cleared.operation`: `set_true`, `set_false`, `none`, `unknown`.
- `guide_request.value`: boolean.
- `strategy_request.value`: boolean.

Safety fields:

- `memory_candidate.should_create`: must remain `false` in this pilot.
- `proactive_signal.type`: must remain `none` in this pilot.
- `reasoning_summary`: safe short summary only; no raw user text, transcript, prompt, JSON, path, or secret.

Schema requirements:

- The pilot currently uses a small constrained candidate ID set; broader multi-game catalog grounding remains future work.
- It must distinguish asking for a guide from reporting current boss.
- It must distinguish temporary game-session state from long-term memory candidate.
- It must distinguish explicit "remember this" from casual statements.
- It must allow unknown freeform entities so the guard can ask clarification instead of pretending no semantic signal exists.

## Composite Confidence

LLM confidence alone must never decide `apply`.

Use a composite model:

```text
semantic_confidence
  = LLM self-confidence
  + schema completeness
  + evidence strength
  - ambiguity penalties
  - provider / parsing instability

grounding_confidence
  = catalog match strength
  + rule exact-match support
  + known game-context compatibility
  - freeform / unknown entity penalty

context_confidence
  = consistency with current game context
  + explicit switch phrase support
  + recent session compatibility
  - unresolved conflict severity

apply_confidence
  = calibrated combination of semantic, grounding, context, source reliability, and risk policy
```

Dimensions:

- LLM self-reported confidence.
- Schema completeness.
- Evidence strength.
- Context consistency.
- Catalog grounding.
- Source reliability:
  - `text`: high.
  - `voice_confirmed`: high-medium because the transcript was user-confirmed or edited.
  - `voice_direct`: medium because ASR uncertainty remains.
- Conflict severity.
- Ambiguity count.
- Extraction stability, future optional.
- Provider status.

Rules:

- Rule exact match may raise `grounding_confidence`.
- Catalog match may raise `grounding_confidence`.
- Voice ASR source lowers source reliability unless the user confirmed it.
- Explicit switch phrases such as `我现在换到 X` raise `context_confidence`.
- Conflict with current boss does not automatically mean low confidence; the user may be switching boss.
- Vague reference such as `玛尔基特那边怎么打来着` may be guide intent, not boss switch.
- Low `apply_confidence` becomes `candidate_only`, `ask_clarification`, or `no_op`.
- Trace should show safe confidence summaries, not raw input or raw model output.

Suggested thresholds for the pilot:

| Decision | Suggested Condition |
| --- | --- |
| `apply` | schema valid, `semantic_confidence >= 0.75`, `grounding_confidence >= 0.7`, `apply_confidence >= 0.75`, no unsafe conflict |
| `ask_clarification` | game-related, medium confidence, ambiguous entity or unresolved conflict |
| `candidate_only` | useful candidate, but confidence / grounding is not enough for state write |
| `no_op` | non-game, invalid, unsafe, very low confidence, provider failure without safe fallback |
| `fallback_to_rule` | LLM unavailable / timeout / auth failed and exact deterministic rule evidence exists |

## Guard Decisions

`apply`

- LLM candidate schema is valid.
- Semantic confidence is high.
- Apply confidence is high.
- Proposed updates are allowed game-context fields.
- Catalog grounding or safe freeform handling is sufficient.
- There is no unsafe conflict.
- Deterministic guard applies the update.

`ask_clarification`

- Input is likely game-related.
- Entity is ambiguous or freeform.
- Conflict is possible but not obviously a switch.
- Confidence is medium.
- User likely expects context update.
- UI / reply can ask a short clarification without writing state.

`candidate_only`

- Candidate is useful for reply context or debug trace.
- Confidence is not enough to persist state.
- It may influence the immediate assistant reply only when safe.
- It must not mutate game context, memory, proactive state, or persona.

`no_op`

- Low confidence.
- Non-game input.
- Invalid JSON.
- Provider timeout without safe fallback.
- Unsafe or memory-sensitive input.
- Relationship / emotional attachment text that should not become memory or game state.

`fallback_to_rule`

- LLM unavailable.
- Provider auth failed.
- Timeout and rule exact match exists.
- Fallback reason must be traced.
- Rule fallback still passes deterministic guard and must not revive broad alias patching.

## Rule Extractor's New Position

Rules become a supporting layer.

Rules can be used for:

- Exact entity grounding.
- Deterministic death count parsing.
- Sanity checks.
- Fallback when LLM is unavailable.
- Regression comparison.
- Guard cross-check.
- Emergency no-provider mode.
- Future fast-path cache, only after correctness is proven.

Rules should not:

- Serve as the multi-game primary semantic reader.
- Alone decide confidence.
- Accumulate endless ASR typo / alias patches.
- Override the LLM candidate's semantic interpretation unless guard explicitly classifies the LLM result as unreliable.

## Text And Voice Sources

All user input sources enter the same LLM-primary architecture:

- Typed text: `source = text`.
- Confirmed voice transcript: `source = voice_confirmed`.
- Direct voice transcript: `source = voice_direct`.

Source affects reliability, confidence calibration, and trace. It does not decide whether the LLM path runs.

Direct Conversation rules:

- ASR transcript auto-send enters the normal chat flow.
- The same LLM-primary extraction pipeline runs.
- Memory confirmation is still required.
- Proactive is not triggered by extraction candidates.
- ASR uncertainty lowers source reliability and can lead to `ask_clarification` or `candidate_only`.

There must not be a split design where voice uses LLM but typed text remains rule-first.

## Relationship To Current Shadow Mode

Current Semantic Extraction v2 Shadow Mode:

- Produces candidates only.
- Does not write state.
- Runs in background.
- Emits lifecycle events.
- Includes JSON stabilization and recovery.
- A successful shadow result does not mean apply.

New architecture:

- Reuse Shadow Mode's provider hardening, JSON recovery lessons, safe event vocabulary, timeout handling, and audit model.
- Promote LLM extraction into the foreground semantic extraction path.
- Keep LLM output non-mutating.
- Add a guarded apply layer between candidate and state write.
- Keep Shadow Mode as audit / comparison / rollout fallback if useful.
- Stop treating Shadow as proof that LLM is part of the product path when the actual state writer remains rule-first.

## Memory / Proactive / Persona Boundaries

These boundaries must not regress:

- LLM extraction cannot write long-term memory.
- LLM extraction may emit `memory_candidate_hint`, but it must enter pending memory confirmation through the existing memory pipeline.
- LLM extraction cannot trigger proactive messages.
- Proactive remains controlled by Proactive Safe Gating.
- LLM extraction cannot modify persona.
- Voice Direct Conversation does not bypass memory confirmation.
- Relationship or emotional attachment input should not automatically become memory.
- Game context extraction and memory extraction remain separate modules with separate schemas and guards.

## Safe Trace

Trace fields may include:

- `input_source`
- `extractor`: `llm_primary`
- `llm_status`
- `schema_valid`
- `semantic_confidence`
- `grounding_confidence`
- `context_confidence`
- `apply_confidence`
- `decision`
- `proposed_updates_summary`
- `applied_updates_summary`
- `conflict_summary`
- `fallback_reason`
- `safe_trace_summary`

Trace must not include by default:

- Full transcript.
- Full user input.
- Raw prompt.
- Raw LLM JSON.
- API key.
- `.env`.
- Full local path.
- stdout / stderr.
- Full assistant reply.

Debug / Game workspace should show enough safe information to answer:

- What did the LLM think the user meant?
- Was the schema valid?
- What did guard decide?
- Why did it apply, ask, keep candidate-only, no-op, or fallback?
- Which safe summaries were applied?

## Rollout Plan

### Phase 1: Architecture / Spec

This document and the QA scenario file define the architecture, risks, and acceptance surface.

No runtime behavior changes.

### Phase 2: LLM-primary Extraction v1 Pilot

Implement the foreground LLM extraction path for game context only.

Pilot scope:

- Typed text.
- `voice_confirmed`.
- `voice_direct`.
- High-confidence game context fields only.
- Deterministic guard controls all writes.
- Rules provide guard support and fallback.
- Existing Shadow Mode can remain for audit.

Do not include memory writes, proactive triggers, persona edits, embeddings, or vector DB.

### Phase 3: Extraction Eval Runner v0

Create fixed evaluation samples comparing:

- old rule result,
- LLM candidate,
- guarded decision,
- expected update.

Include voice-ASR-like typos, slang, guide requests, boss switches, death count, clear events, conflicts, invalid JSON, timeout, and memory-sensitive statements.

### Phase 4: Multi-game Catalog Expansion

Scale through:

- catalog grounding,
- game/entity manifests,
- LLM semantic interpretation,
- guard validation.

Avoid alias explosion. Exact aliases are still useful, but only as grounding evidence.

### Phase 5: Memory Candidate Extraction

Create a separate memory-candidate extraction path if needed.

It must remain separate from game context extraction and must route through pending memory confirmation.

## Next Pilot Recommendations

- Start with a narrow guarded apply allowlist: `current_game`, `current_boss`, `death_count_increment`, `death_count_absolute`, `boss_cleared`, and `guide_request`.
- Use safe traces first; do not expose raw LLM JSON in UI.
- Implement provider unavailable / timeout fallback before enabling real apply.
- Keep rule-first behavior available behind fallback during rollout.
- Add an eval runner before broadening to more games.
- Treat voice-direct source as medium reliability even when the transcript looks plausible.
- Prefer `ask_clarification` over wrong state writes.
