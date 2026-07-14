# ASR Noisy Boss Switch Regression

## Scope

This regression fixes structured Boss switching when a submitted Local ASR transcript contains a small name error. It does not add a game knowledge base, RAG, or a special-case alias for the failed transcript.

The runtime boundary remains:

```text
LLM-primary semantic understanding
-> deterministic grounding / guard
-> safe canonical state apply
```

Typed text, confirmed Voice input, and Direct Conversation all use this path after submission.

## Reproduced Failure

Two submitted turns reproduced the bug:

```text
我现在不打马尔吉特了，我去打接支格瑞克
这个也没打过死了一次
```

The first provider result was schema-valid and already contained the important semantic structure:

- intent: Boss switch;
- previous / negated target: `margit`;
- new target candidate: `godrick`;
- observed surface: `接支格瑞克`;
- candidate reason: descriptive or noisy name.

The old guard treated the descriptive-name warning as stronger than the otherwise consistent switch evidence, so it did not formally apply Godrick. The state fallback cleared the current field in some paths, but `last_attempted_boss` and `abandoned` history were still eligible as unresolved failure context. The second vague reference could therefore rehydrate Margit.

This was not primarily an alias failure: the LLM had already produced the canonical Godrick candidate. It was also not missing game knowledge: the bug lived between candidate grounding, guard policy, and stale-state attribution.

## Multi-Signal Grounding

The deterministic validator now combines bounded signals instead of letting any single fuzzy string match write state:

| Signal | Owner | Effect |
| --- | --- | --- |
| canonical Boss guess | LLM candidate | proposes identity; never writes state directly |
| previous / negated / new target roles | LLM candidate | establishes switch structure |
| Boss entity type and game ownership | finite registry | rejects cross-game or unknown identities |
| current Boss matches the negated target | state + registry | confirms the old side of the transition |
| unique bounded surface match | finite registry | supports the canonical guess; never auto-applies alone |
| vague / uncertain wording | deterministic guard | keeps a candidate from becoming formal state without enough evidence |

`ground_boss_surface` allows at most two edits against the finite registered surfaces, requires a unique winner, and must agree with the LLM canonical hint. Its result is validator evidence with `auto_apply=false`.

`接支格瑞克` is deliberately not added as an exact alias. The successful method is recorded as `llm_canonical_role_unique_noisy_surface`.

## State Policy

The guard has three relevant outcomes:

1. **New target grounded:** apply a Boss switch to canonical Godrick and mark the previous current Boss as abandoned.
2. **Old target explicitly negated, new target unresolved:** apply a clear-only Boss switch, set `current_boss` to none, and retain the new identity only as candidate / unresolved trace.
3. **Vague mention without a committed switch:** keep candidate-only or no-op; do not set a new current Boss.

The forbidden outcome is silently retaining an explicitly negated current Boss.

`abandoned` history is no longer an implicit unresolved antecedent. An explicit rechallenge phrase such as `重新挑战` or `回去打` may intentionally reopen it; a vague failure or pronoun may not.

## Follow-Up Attribution

After a successful noisy switch, `这个也没打过死了一次` resolves against current Godrick and updates Godrick's failure state. If the first turn only cleared the old target, the same follow-up may update generic death / failure state but cannot assign the failure to abandoned Margit.

Session focus also treats an explicit negated-Boss message as a focus boundary. If the noisy new surface cannot be resolved by the lightweight focus detector, it stops searching older messages instead of selecting the abandoned Boss. Formal Game Session State remains the authoritative grounded context.

This is a bounded two-turn safety fix, not a general coreference engine.

## Safe Trace

Debug exposes these structured fields:

- provider status and schema validity;
- intent and switch detection;
- previous target, new target candidate, and canonical candidate;
- grounding method and confidence band;
- a bounded entity surface in Debug only;
- guard decision;
- cleared, applied, and rejected field names;
- rejection reason and follow-up attribution status.

Event Stream receives only safe canonical / status fields. It does not receive the bounded extracted surface, full transcript, raw provider response, raw prompt, assistant reply, secret, authorization value, local path, or raw stderr.

## Regression Coverage

The fixed extraction eval contains 40 scenarios, including:

- standard Margit-to-Godrick switch;
- the noisy switch through text, `voice_confirmed`, and `voice_direct`;
- explicit old-target clear with uncertain new target;
- vague non-switch candidate handling;
- noisy guide discussion target without current-Boss mutation;
- non-game no-switch behavior.

Focused tests additionally cover the two-turn failure attribution, abandoned-history filtering, session-focus boundary, death-count fallback when the provider omits an explicit count, API source equivalence, and Event Stream privacy.

Run from `services/backend`:

```bash
. .venv/bin/activate
python scripts/run_extraction_eval.py --provider mock
python scripts/run_extraction_eval.py --provider live
```

Live provider evaluation is a drift check. The deterministic mock suite remains the required regression gate.

## Out Of Scope

- complete Elden Ring entity coverage;
- Boss strategy, move, drop, route, or story data;
- phonetic ASR engine replacement;
- cloud ASR;
- vector search or RAG;
- general multi-turn coreference;
- Voice / TTS expansion.
