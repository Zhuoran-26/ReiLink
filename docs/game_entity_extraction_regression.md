# Game Entity Extraction Regression Fix

## Scope

This fix restores the structured game-state path for natural Boss names without changing how Rei's reply is generated.

The two layers remain separate:

```text
chat reply understanding != formal Game Context
```

The reply model may understand a name from conversational context even when the structured extraction provider was never called. Formal state still requires schema validation, canonical grounding, deterministic guard, and state apply.

## Root Cause

Before this fix, Boss identity was split across several local lists:

- the intent router and session focus knew `玛尔基特` and `Margit`, but not `玛尔吉特`;
- the semantic-call gate therefore classified `我刚才打玛尔吉特又失败了` and `玛尔吉特怎么打` as `no_semantic_signal`;
- the foreground extraction provider was not called for those inputs;
- `Godrick` existed in the knowledge pack but not in the extraction schema's canonical Boss set;
- guide-only candidates were visible in trace but had no non-committal game-session destination.

This explains why the main reply could be correct while Game Context remained empty. It was not a Voice routing defect: typed text, confirmed ASR, and Direct Conversation already converged on `/api/chat`; the shared structured pipeline failed after submission.

## Canonical Registry

`app/modules/game_context/entity_registry.py` is the constrained source of truth for Boss IDs, display names, game ownership, and accepted aliases used by extraction, intent routing, session focus, and knowledge lookup.

For Margit:

| Surface | Canonical ID | Display name | Match policy |
| --- | --- | --- | --- |
| `玛尔吉特` | `margit` | `恶兆妖鬼 Margit` | registered exact alias, auto-groundable |
| `玛尔基特` | `margit` | `恶兆妖鬼 Margit` | registered exact alias, auto-groundable |
| `Margit` | `margit` | `恶兆妖鬼 Margit` | canonical/registered alias, auto-groundable |
| an unregistered one-character near miss | candidate `margit` | `恶兆妖鬼 Margit` | `near_alias`, never sufficient by itself for formal apply |

Known ASR/transliteration forms are bounded registry entries. General one-edit matching is only candidate evidence. Descriptive names such as `树守卫` or `那个骑马金甲大哥` do not become exact aliases and still require model/context confirmation.

The same registry now exposes `godrick`, so `接肢葛瑞克` can pass schema normalization and deterministic grounding instead of collapsing to `unknown`.

## State Semantics

### Current challenge

Explicit current progress such as `我刚才打玛尔吉特又失败了` may update:

- `current_boss`;
- `last_attempted_boss` / `last_failed_boss`;
- `current_activity`;
- existing frustration/death counters when their existing signals are present.

### Guide discussion

Guide questions such as `玛尔吉特怎么打` apply a session-level `discussion_target` with activity `guide_request`.

`discussion_target`:

- is not `current_boss` and does not switch the current challenge;
- does not increment death or frustration counters;
- is stored only with Game Session State;
- is not copied into Long-term Memory, Pending Memory, Session Archive, or proactive triggers;
- is replaced by the next grounded guide target;
- is cleared by a formal challenge transition, explicit abandon/switch, or game-session reset;
- is retained across unrelated chat so a non-game message does not itself mutate Game Context.

### Historical and negative mentions

Historical statements such as `我以前打过玛尔吉特` remain candidates and cannot mark the Boss current, failed, or cleared. Explicit negation/switch semantics cannot fall back to the old mentioned target when the provider is unavailable.

## Submitted Input Equivalence

After a message is truly submitted, these sources use the same pipeline:

```text
text
voice_confirmed
voice_direct
  -> semantic extraction
  -> schema validation
  -> canonical registry grounding
  -> deterministic guard
  -> Game Session State apply
```

The source remains privacy/trace metadata. Pre-submit Voice guards may reject empty, short, partial, or too-short-recording transcripts before `/api/chat`; once submitted, the same text has the same candidate entity, canonical entity, guard decision, and state result.

## Safe Trace

Developer Trace and Event Stream may expose only safe structured fields:

- provider status and schema validity;
- candidate/canonical entity IDs and canonical display name;
- grounding status and match type;
- guard decision/reason;
- applied and rejected field names;
- source metadata and latency.

They must not expose full user input, raw ASR transcript, assistant reply, spoken text, raw provider response, raw prompt/JSON, secrets, authorization data, or local paths.

## Known Limit

Short multi-turn coreference remains bounded. A follow-up such as `它二阶段怎么躲？` can use existing session focus when a recent explicit Boss is available, but this task does not add a general coreference engine. Trace must not imply that an unresolved pronoun was canonically grounded when no safe recent target exists.

## Regression Gates

The fixed eval fixture covers:

- the Margit failure sentence through text, `voice_confirmed`, and `voice_direct`;
- guide discussion target without current-Boss switch;
- Margit-to-Godrick negation/switch;
- historical mention no-op;
- non-game no-context-change behavior.

Run from `services/backend`:

```bash
. .venv/bin/activate
python scripts/run_extraction_eval.py --provider mock
python scripts/run_extraction_eval.py --provider live
```
