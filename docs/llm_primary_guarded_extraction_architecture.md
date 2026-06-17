# LLM-primary Guarded Extraction Architecture v1.0.2 Pilot

Updated: 2026-06-17

Status: implemented pilot, updated in v1.0.2. ReiLink now has a foreground LLM-primary semantic reader for chat input when an LLM provider is configured, followed by tolerant-but-safe JSON/schema validation and deterministic guard. v1.0.2 stabilizes the primary JSON path by using a compact JSON-only prompt, Shadow-style JSON recovery, a no-response-format compat retry for invalid JSON/schema output, and clearer fallback trace fields. This pilot does not add embeddings or vector databases and does not change memory, proactive, persona, voice core behavior, or Overlay runtime boundaries.

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

## v1.0.1 Runtime Fixes

v1.0.1 fixes the main pilot gap: an exact rule hit is grounding, not the primary semantic interpretation.

The foreground order is:

```text
input
-> LLM primary extraction attempt
-> strict schema validation
-> deterministic guard with rule grounding
-> apply / ask_clarification / candidate_only / no_op / fallback_to_rule
```

Rules may fallback only when the LLM path is unavailable, times out, returns invalid JSON / invalid schema, or when a valid LLM candidate is a true no-op and the rule result is an exact safe match. A high-confidence rule result must not skip or silently overwrite a valid LLM candidate.

Switch and negation examples are explicitly represented:

- `不打 A 了，换去打 B`
- `先不打 A，去 B`
- `从 A 换到 B`
- `我又去打 B 了`

The schema distinguishes:

- `mentioned_entity`
- `negated_entity`
- `previous_target`
- `new_current_target`
- `guide_only_entity`
- `current_target_candidate`
- `boss_switched`

For `不打女武神了，换去打玛尔基特`, rules may ground that `女武神` and `玛尔基特` are known entities, but guard should apply the LLM's `new_current_target=margit` when confidence and grounding are sufficient. Guide-only mentions such as `玛尔基特那边怎么打来着` should remain `candidate_only` / `ask_clarification` and must not switch current boss unless the user explicitly says they are now fighting or switching to that boss.

For voice sources, the LLM may recover likely ASR near-misses into canonical candidates, such as `马尔吉特 -> margit` or `女巫神 -> malenia`, but uncertain candidates should become `ask_clarification` / `candidate_only` rather than silent no-op or unsafe writes.

## v1.0.2 JSON / Schema Stabilization

v1.0.2 fixes the next primary-path gap: the LLM could semantically understand an input but fail the foreground path because the JSON object or schema shape was unstable. Primary extraction now reuses the safe recovery lessons from Shadow Mode:

- compact JSON-only system and user prompts.
- low temperature and fast model provider config.
- `response_format: {"type": "json_object"}` on the first attempt when available.
- safe recovery for strict JSON, fenced JSON, prose around the first JSON object, and arrays whose first item is an object.
- compat retry without `response_format` when the first primary attempt fails JSON parsing or schema validation.
- ultra-compact retry if the compat attempt is still invalid JSON or schema invalid; this uses an even smaller key whitelist so real providers do not expand the full internal schema.
- safe trace fields: `first_attempt_failed`, `compat_retry_used`, `compat_retry_succeeded`, `ultra_compact_used`, and `json_recovery_stage`.

The primary parser accepts both the older expanded object and the v1.0.2 minimal shape:

```json
{
  "is_game_related": true,
  "intent": "boss_switch",
  "confidence": 0.92,
  "requires_clarification": false,
  "updates": [
    {
      "field": "boss",
      "value": "玛尔基特",
      "canonical": "margit",
      "confidence": 0.92,
      "reason": "safe short reason"
    }
  ],
  "previous_target": "malenia",
  "negated_entity": "malenia",
  "new_current_target": "margit",
  "guide_only_entity": null,
  "guide_request": false,
  "strategy_request": false,
  "safe_trace_summary": "safe short summary, no raw user text"
}
```

Optional fields may be absent. Unknown enum-like operations are mapped to `unknown` / `none` instead of failing the whole extraction. Confidence may be `high` / `medium` / `low` or a number in `0..1`. The guard still only applies allowlisted game-context fields; memory and proactive fields remain disabled on this path.

When primary fails and rule fallback is considered, trace must show the path explicitly:

- `primary_extractor=llm`
- `primary_status=failed`
- `fallback_extractor=rule` when fallback is used
- `guard_final_decision=fallback_to_rule` / `no_op` / `apply`
- `applied_by=rule_fallback` when a rule fallback actually writes state

## LLM Candidate Schema v1 Pilot

The foreground LLM returns one JSON object. It uses constrained IDs for the current pilot and must keep memory / proactive candidates disabled. v1.0.2 prefers the minimal `updates` shape above, while the parser still accepts the expanded object below for compatibility.

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
  "boss_switched": {"value": false, "confidence": "low"},
  "mentioned_entity": {"value": null, "surface_label": null, "confidence": "low"},
  "negated_entity": {"value": null, "surface_label": null, "confidence": "low"},
  "previous_target": {"value": null, "surface_label": null, "confidence": "low"},
  "new_current_target": {"value": null, "surface_label": null, "confidence": "low"},
  "guide_only_entity": {"value": null, "surface_label": null, "confidence": "low"},
  "current_target_candidate": {"value": null, "surface_label": null, "confidence": "low"},
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
- `boss.value`: `margit`, `malenia`, `tree_sentinel`, `false_knight`, `unknown`, or `null`.
- `boss.surface_label`: nullable safe short label.
- target-role entity `value`: the same constrained boss IDs as `boss.value`.
- `boss_switched.value`: boolean switch intent candidate.

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
| `fallback_to_rule` | LLM unavailable / timeout / invalid JSON / invalid schema, or LLM no-op plus exact safe deterministic rule evidence; switch / negation text with multiple boss mentions must not fallback to the old negated target |

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
- Timeout, invalid JSON, or schema invalid and rule exact match exists.
- Fallback reason must be traced as `llm_timeout`, `llm_invalid_json`, or `llm_schema_invalid` equivalent runtime fields.
- Trace must show the rule path as fallback with `fallback_extractor=rule` and `applied_by=rule_fallback` when it writes state.
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

Completed before the v1 runtime pilot.

### Phase 2: LLM-primary Extraction v1 / v1.0.1 Pilot

Implemented foreground LLM extraction path for game context only.

Pilot scope:

- Typed text.
- `voice_confirmed`.
- `voice_direct`.
- High-confidence game context fields only.
- Deterministic guard controls all writes.
- Rules provide guard support and fallback.
- Existing Shadow Mode remains for audit.
- v1.0.1 adds target-role fields, switch / negation guard behavior, ASR typo candidate trace, and Direct Conversation partial-transcript protection.

Do not include memory writes, proactive triggers, persona edits, embeddings, or vector DB.

### Phase 3: Extraction Eval Runner v0

Implemented as a backend module plus CLI:

- runner module: `services/backend/app/modules/dialogue_agent/extraction_eval.py`
- CLI entrypoint: `services/backend/scripts/run_extraction_eval.py`
- fixed scenarios: `docs/qa/extraction_eval_scenarios.json`

The default command is deterministic and safe for CI:

```bash
cd services/backend
. .venv/bin/activate
python scripts/run_extraction_eval.py --provider mock
```

The optional live-provider drift check is manual:

```bash
cd services/backend
. .venv/bin/activate
python scripts/run_extraction_eval.py --provider live --allow-failures
```

The runner reuses the runtime `extract_semantics` path and `GameSessionStore`; it does not copy extraction business logic into a second ruleset. For each scenario it compares the guarded decision and state delta against expected results, applies only `final_decision.game_event`, and keeps raw user text / raw provider JSON / raw prompts / secrets out of the report.

Fixed scenarios cover typed text, `voice_confirmed`, `voice_direct`, ASR-like variants, slang, guide-only references, boss set / switch, switch negation, death count absolute / increment, boss clear, rule conflict, invalid JSON, schema invalid, compat retry, ultra-compact retry, low-confidence candidate-only, and memory-sensitive boundaries.

Metrics include total / passed / failed / pass_rate, LLM-primary success count, schema valid count, invalid_json count, schema_invalid count, fallback-to-rule count, compat retry count, ultra-compact retry count, wrong apply count, missed apply count, and correct candidate-only count.

Known v0 limits:

- Mock mode validates fixed guarded behavior and state deltas, not real-provider determinism.
- Live mode is a drift / observation tool and can fail because of auth, timeout, quota, or provider output variance.
- The runner applies only the guarded semantic event to isolate LLM-primary extraction from later raw-message rule re-interpretation.
- Some ASR near-miss guide requests may still be blocked by upstream gating before the LLM path; v0 treats "no wrong state write" as acceptable until alias / gating expansion is separately scoped.

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
- Keep the Extraction Eval Runner v0 mock suite green before broadening to more games.
- Treat voice-direct source as medium reliability even when the transcript looks plausible.
- Prefer `ask_clarification` over wrong state writes.
