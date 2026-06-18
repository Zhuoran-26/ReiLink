# Hermes-style Memory Architecture v0

Updated: 2026-06-18

Status: architecture baseline plus Candidate Memory v1, Memory Retrieval v1 runtime slice, and Persona-Memory Regression Eval v0. This document still does not implement Session Archive, vector database, external memory provider, UI popup, or packaging change.

## Purpose

ReiLink is a local-first AI companion for single-player game players. Memory should make Rei feel more consistent and quietly attentive without turning every session event into a permanent fact, without drifting Rei's persona, and without exposing private data.

The target pipeline is:

```text
session event / explicit preference / repeated pattern
-> memory candidate
-> safety / relevance / persona guard
-> user confirmation or weak confirmation handling
-> long-term memory
-> bounded retrieval
-> prompt assembly
-> reply
```

Memory is not a second persona system. Memory is user-specific context; Persona Pack remains the stable Rei core.

After Memory Retrieval v1, accepted memory can finally affect the model prompt. Persona-Memory Regression Eval v0 exists to keep that effect quiet and natural: memory may tune pacing, spoiler level, answer length, and voice brevity, but it must not become a repeated "I remember" template, a hidden system command, or a persona override.

## Research Summary

Light research focused on official Hermes Agent docs and public GitHub material:

- Hermes Persistent Memory docs: bounded curated memory, two stores (`MEMORY.md` and `USER.md`), character limits, prompt injection at session start, write approval, duplicate prevention, security scanning, and session search separation: [Persistent Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory).
- Hermes Memory Providers docs: optional external providers are additive, can prefetch relevant memories, sync turns, extract memories on session end, and provide search/manage tools: [Memory Providers](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers).
- Hermes README: high-level idea of a long-running agent with curated memory, session search, skill creation, and cross-session user modeling: [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).
- Hermes Memory Provider Plugin docs: provider lifecycle hooks such as `system_prompt_block`, `prefetch`, `queue_prefetch`, `sync_turn`, `on_session_end`, and `on_pre_compress`: [Memory Provider Plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin).

Research limits:

- This pass did not audit Hermes source code in depth.
- Hermes is a general self-improving agent; ReiLink is a restrained game companion, so the useful material is architectural, not product behavior.
- ReiLink should not copy Hermes code, prompt text, skill loop, provider abstractions, or auto-save defaults.

Absorbable ideas:

- Keep memory bounded, curated, and compact.
- Separate user profile memory from agent/environment notes.
- Keep session search / session archive distinct from always-injected memory.
- Allow staged writes and user approval before memory becomes durable.
- Treat external providers as optional and additive, not required.
- Use prefetch / retrieval budgets before prompt injection.
- Scan memory entries for unsafe content because injected memory can become prompt input.

Not suitable for ReiLink v0:

- Free-form autonomous memory writes by default.
- Self-evolving skill creation.
- Cloud memory providers as a first-class dependency.
- Long-running multi-platform autonomous agent assumptions.
- Letting user preferences reshape Rei's persona core.

ReiLink translation:

- Use Hermes-style bounded curation, but default to confirmation-first.
- Treat memory candidates as user-visible, safe summaries.
- Store only stable user preferences, interaction preferences, and repeated gameplay patterns.
- Keep Game Session State, Session Timeline, Knowledge Retrieval, Persona Pack, and Long-term Memory separate.

## Memory Layers

### Working Context

Current turn and short conversational context. It can influence the immediate reply but is not durable by itself.

Examples:

- The user is currently asking how to handle Margit's second phase.
- Rei has just asked a clarification question.
- A voice transcript is waiting for user confirmation.

Rules:

- It may include current conversation state.
- It should not become long-term memory unless converted into a guarded Memory Candidate.
- It should be dropped or summarized when the session moves on.

### Game Session State

Current-game state, owned by Game Session runtime:

- `current_game`
- `current_boss`
- `death_count`
- `frustration_count`
- `current_activity`
- `last_cleared_boss`

This can come from LLM-primary extraction, but it is not long-term memory.

Examples:

- `current_boss=恶兆妖鬼 Margit`
- `death_count=3`
- `current_activity=boss_failed`

Rules:

- Single-session state can inform replies and proactive checks.
- It should not be saved as long-term memory just because it happened.
- Session Archive v1 may later summarize it, but that is a separate pipeline.

### Session Timeline

Current renderer-session safe event summaries. This already exists as v1.

Examples:

- `检测到 Boss：Margit`
- `死亡次数更新：3`
- `记忆已接受`

Rules:

- Default is non-persistent.
- It is a possible future input to Session Archive.
- It is not long-term memory and should not be injected wholesale into prompts.

### Candidate Game Understanding

LLM-primary Extraction v1.0.3 candidate fields:

- `candidate_boss`
- `candidate_event`
- `candidate_game`
- `candidate_confidence`
- `candidate_reason`
- `needs_confirmation`
- `guide_entity`
- `confirmation_intent`

Rules:

- These fields may help Rei phrase the current reply.
- They are not formal Game Session State.
- They are not Long-term Memory.
- They may contribute to a Memory Candidate only if the content is about stable user preference or repeated pattern, not a one-off boss guess.

### Memory Candidate

A safe, user-visible proposal that might become Long-term Memory.

Examples:

- User prefers exploring before fighting bosses.
- User dislikes detailed spoilers.
- User wants shorter replies.
- User often gets impatient after repeated fast deaths.

Rules:

- It must pass memory guard before it reaches pending UI or explicit auto-save.
- It must be confirmable, ignorable, revisable, and expirable.
- It must preserve evidence as a safe summary, not raw transcript.
- It must never be created from assistant replies or proactive text alone.

Current v1.1 runtime:

- Reuses the existing pending memory API, Memory workspace Pending tab, and undoable Long-term Memory items.
- Stores `summary`, `evidence_summary`, `guard_reason`, `expires_at`, source metadata, and voice / assistant / proactive flags.
- Shows pending candidates only after guard passes; explicit remember requests can auto-save after guard and show a lightweight undo hint.
- Stores rejected guard results outside pending UI for no-memory, secret, persona drift, assistant source, or proactive source cases.

### Long-term Memory

Confirmed durable user preference, habit, or important fact.

Rules:

- Must be user-visible.
- Must be deletable.
- Must be local-first.
- Must not contain unconfirmed guesses.
- Must not contain secrets, paths, `.env`, API keys, raw logs, or raw transcripts.
- Must not rewrite Persona Core.

### Retrieved Memory

Relevant memories selected for the current reply.

Rules:

- Retrieval is query/context-dependent.
- It should have item and token budgets.
- It should use safe summaries.
- It should not inject the entire memory store.
- Explicit current user input beats stale retrieved memory.

### Prompt Memory Block

The bounded prompt section produced by Memory Retrieval.

Rules:

- It must have `max_items`.
- It must have `token_budget`.
- It should include omitted count and safety notes.
- It should be injected as user-specific context, not identity or system instruction.

### Persona Core

Rei's stable character policy from Persona Pack.

Rules:

- Persona Core is higher priority than memory.
- Memory can tune response strategy within bounds.
- Memory cannot make Rei sweet, customer-service-like, therapist-like, or mascot-like.
- Persona drift requests become bounded preferences only when safe.

## Memory Guard Rules

### Can Become Memory Candidate

- Explicit remember request:
  - `记住我打 Boss 前喜欢先探索地图。`
- Stable gameplay preference:
  - prefers exploration before bosses.
  - dislikes direct hard rushing.
  - avoids detailed spoilers.
- Stable interaction preference:
  - wants shorter answers.
  - wants less voice output.
  - prefers fewer strategy details unless asked.
- Repeated gameplay pattern:
  - repeatedly gets impatient after fast deaths.
- User-confirmed fact:
  - `对，我确实不喜欢直接冲 Boss。`
- Bounded accessibility / comfort preference:
  - prefers brief voice replies.
  - wants text-first for long strategy.

### Must Not Become Long-term Memory

- One-off game event:
  - `我刚刚死了三次。`
- Unconfirmed candidate:
  - `可能是大树守卫吧。`
- Assistant reply content.
- Proactive message content.
- Game knowledge / guide content.
- Low-confidence extraction candidate.
- Persona-changing request:
  - `以后你都撒娇一点。`
  - `以后你像客服一样鼓励我。`
- Sensitive personal information unless explicitly requested and safe.
- API keys, file paths, `.env`, system logs, raw stdout/stderr, raw JSON.
- Raw ASR transcript or raw prompt.

## Anti Persona Drift

Memory may affect strategy, not identity.

Allowed bounded preferences:

- `reply_length=short`
- `avoid_spoilers=true`
- `voice_reply_brief=true`
- `strategy_detail=low_until_asked`
- `check_in_frequency=low`

Rejected persona-changing memory:

- `Rei becomes cheerful`
- `Rei should always praise the user`
- `Rei should speak like customer support`
- `Rei should be affectionate by default`
- `Rei must comfort intensely after every death`

Examples:

| User request | Memory outcome |
| --- | --- |
| `以后回答短一点。` | Candidate: interaction preference, short replies. |
| `别剧透支线，除非我问。` | Candidate: gameplay / knowledge preference, avoid spoilers. |
| `以后你撒娇一点。` | Rejected by persona guard; optionally candidate: avoid overly formal tone only if safe. |
| `每次我死了都夸我。` | Rejected / bounded; could become low-intensity encouragement preference only after confirmation. |
| `语音少说点，文字里展开。` | Candidate: voice brief + text detail preference. |

## Candidate Lifecycle

```text
source event
-> semantic extraction / memory intent / repeated-pattern detector
-> MemoryCandidate draft
-> memory guard
   -> rejected_by_guard
   -> explicit_auto_saved
   -> pending
-> user response
   -> accepted
   -> ignored
   -> revised
   -> uncertain / weak confirmation
   -> expired
-> LongTermMemory
-> retrieval index / prompt block
```

Candidate sources:

- explicit user request.
- LLM-primary memory intent.
- user confirmation or correction.
- repeated safe pattern from session timeline.
- future Session Archive summary.

Candidate statuses:

- `pending`
- `accepted`
- `ignored`
- `expired`
- `rejected_by_guard`

User confirmation:

- `confirm`: accept if guard still passes.
- `deny`: ignore.
- `correct`: revise candidate, then require confirmation or accept exact bounded correction.
- `uncertain`: keep pending, reduce confidence, avoid immediate save.
- `unrelated`: leave candidate unchanged and let it age.
- `unknown`: no state change.

Important: weak confirmation such as `也许吧` or `可能是` is not enough to create Long-term Memory.

## Confirmation Flow

### Candidate Creation

Memory Candidate generation can use:

- existing pending memory trigger for explicit remember requests.
- LLM-primary semantic extraction for memory intent and confirmation intent.
- future repeated-pattern detection over Session Timeline.

The candidate should include:

- safe user-visible summary.
- why it might matter.
- confidence.
- expiry.
- guard reason.
- source summary.

### User Presentation

Default UI:

- Memory workspace Pending tab.
- Low-noise inline chat hint for explicit remember requests, with undo.
- Debug safe trace for candidate lifecycle.

Voice / Direct Conversation:

- Avoid interrupting active gameplay.
- Prefer a short non-blocking cue only when user explicitly requested remembering.
- For implicit candidates, stage silently and surface later in Memory workspace.
- Do not repeatedly ask in the same session.

Overlay:

- Default: do not show memory candidates.
- Future: only show non-sensitive, explicit pending confirmations if user enables it.

### Accept / Ignore / Delete / Revise

- Accept moves pending candidate into Long-term Memory.
- Explicit auto-save moves guarded explicit remember requests into Long-term Memory and exposes undo.
- Ignore marks candidate as ignored and suppresses near-duplicate prompts.
- Delete / undo deactivates Long-term Memory and removes it from retrieval / prompt assembly.
- Revise creates an updated candidate or edits the user-visible text after confirmation.

### Expiry And Dedup

- Explicit remember candidates: longer expiry, e.g. 7 days.
- Implicit repeated-pattern candidates: shorter expiry, e.g. current session or 24 hours.
- Weak-confirmed candidates: keep pending but do not promote.
- Duplicate candidates: merge evidence summaries, raise confidence only if sources are compatible.
- Do-not-remember preference suppresses future candidates of the same class.

## Prompt Assembly

Runtime v1 prompt stack:

1. App identity and safety.
2. Persona Pack / Persona Core.
3. Retrieved Memory block, only accepted / active user-specific preferences and bounded facts.
4. Voice Profile / current interaction mode.
5. Current explicit user input and Working Context.
6. Formal Game Session State.
7. Knowledge Retrieval snippets.
8. Candidate Game Understanding for current turn only.

Memory rules:

- Memory is user-specific context, not system instruction.
- Memory cannot override Persona Core, safety, or current explicit input.
- The prompt memory block explicitly states that current user input has priority.
- Memory should not override current Game Session State when the user is explicitly reporting a new state.
- Memory should be injected as safe summaries, not raw transcript.
- Memory should be limited, for example `max_items=3` and a small token budget.
- Memory use should be natural. Rei should not over-explain "I remember..." unless it helps.
- Prompt Preview / Debug may show retrieved count, omitted count, memory types, memory ids, token estimate, and safe summaries, but not raw prompt or raw evidence.

Prompt memory block example:

```json
{
  "max_items": 3,
  "token_budget": 220,
  "memories": [
    {
      "memory_id": "mem_123",
      "type": "gameplay_preference",
      "safe_summary": "User prefers light hints before detailed boss strategy.",
      "injectable_text": "User prefers light hints before detailed strategy.",
      "token_estimate": 12
    }
  ],
  "omitted_count": 2,
  "safety_notes": ["persona_core_has_priority", "raw_transcript_omitted"]
}
```

## Data Model Draft

### MemoryCandidate

```json
{
  "id": "cand_...",
  "source": "explicit_user_request | semantic_extraction | session_timeline | direct_voice | manual",
  "source_event_id": "event_...",
  "created_at": "2026-06-18T00:00:00Z",
  "expires_at": "2026-06-25T00:00:00Z",
  "type": "gameplay_preference | interaction_preference | emotional_pattern | accessibility_preference | do_not_remember",
  "summary": "User prefers exploring before boss attempts.",
  "evidence_summary": "User explicitly asked Rei to remember this preference.",
  "confidence": "high | medium | low",
  "requires_confirmation": true,
  "status": "pending | accepted | ignored | expired | rejected_by_guard",
  "guard_reason": "explicit_memory_request | requires_confirmation",
  "privacy_level": "normal | sensitive | secret_rejected",
  "related_game": "elden_ring",
  "related_entity": "boss",
  "from_voice": false,
  "from_proactive": false,
  "from_assistant": false,
  "confirmation_intent": "confirm | deny | correct | uncertain | unrelated | unknown"
}
```

### LongTermMemory

```json
{
  "id": "mem_...",
  "created_at": "2026-06-18T00:00:00Z",
  "updated_at": "2026-06-18T00:00:00Z",
  "type": "gameplay_preference",
  "summary": "User prefers exploring before boss attempts.",
  "normalized_value": {"boss_approach": "explore_first"},
  "user_visible_text": "打 Boss 前喜欢先探索地图。",
  "confidence": "high",
  "source_candidate_id": "cand_...",
  "last_used_at": null,
  "use_count": 0,
  "is_active": true,
  "deletion_status": "active | deleted | pending_delete",
  "related_game": "elden_ring",
  "related_entity": "boss",
  "retrieval_tags": ["boss", "approach", "exploration"]
}
```

### MemoryRetrievalResult

```json
{
  "memory_id": "mem_...",
  "relevance_score": 0.82,
  "reason": "current query asks for boss strategy",
  "safe_summary": "User prefers light hints before detailed boss strategy.",
  "injectable_text": "User prefers light hints before detailed boss strategy.",
  "token_estimate": 12
}
```

### PromptMemoryBlock

```json
{
  "max_items": 3,
  "token_budget": 220,
  "memories": [],
  "omitted_count": 0,
  "safety_notes": []
}
```

## Relationship To Existing Modules

### LLM-primary Extraction

- Provides memory intent and confirmation intent.
- Candidate Game Understanding is separate from Memory Candidate.
- Low-confidence extraction candidates should not become Long-term Memory.
- `confirmation_intent=uncertain` keeps candidates pending.

### Game Context

- Owns current game/session facts.
- Does not become Long-term Memory by default.
- Current explicit user input and Game Session State override stale memory.

### Session Timeline

- Stores safe event summaries for current session.
- Future Session Archive may summarize repeated patterns.
- Timeline is not injected wholesale and is not Long-term Memory.

### Proactive

- May read accepted memory to tune low-interruption behavior.
- Must not write memory from its own messages.
- Must not create memory candidates without a user signal or repeated user pattern.

### Persona Pack

- Persona Core always wins.
- Memory can tune response length, spoiler level, voice brevity, and interaction preferences.
- Memory cannot change Rei into another character or tone family.

### Knowledge Retrieval

- Knowledge is factual game content.
- User Memory is personal preference / habit / confirmed fact.
- Knowledge snippets should never become user memory.

### Voice / Direct Conversation

- Voice transcript can produce Memory Candidate only after normal chat flow and guard.
- Direct Conversation should avoid frequent confirmation interruptions.
- Voice confirmation should use short, safe wording.

### Overlay

- Overlay should not show sensitive memory by default.
- Future overlay memory cue must be opt-in and safe-summary-only.

### Debug Trace

- May show candidate status, type, guard reason, and safe summary.
- Must not show raw transcript, raw prompt, raw model JSON, API key, `.env`, paths, stdout/stderr, or secrets.

## QA Scenarios

Machine-readable scenarios live in:

```text
docs/qa/memory_architecture_scenarios.json
docs/qa/candidate_memory_scenarios.json
docs/qa/memory_ux_v1_1_scenarios.json
docs/qa/memory_retrieval_scenarios.json
docs/qa/persona_memory_regression_scenarios.json
```

The scenarios cover explicit memory requests, auto-save hints, undo, negative memory requests, one-off session events, spoiler and reply-length preferences, LLM-primary candidate checks, rule prefilter boundaries, persona drift rejection, accept / ignore / delete / revise flows, weak confirmation, voice and proactive boundaries, knowledge / memory separation, prompt budget, game-context conflict priority, sensitive data rejection, duplicate handling, accepted-memory retrieval, inactive / pending / rejected exclusion, use-count updates, Memory workspace visibility, Direct Conversation interruption policy, Overlay privacy, Debug safe trace, and Persona-Memory regression behavior after retrieval.

## Roadmap

### Candidate Memory v1.1

Status: implemented as the first minimal runtime slice plus explicit auto-save / undo.

- Normalizes MemoryCandidate schema.
- Routes explicit remember requests through Memory Candidate guard into undoable Long-term Memory; selected stable implicit preferences become pending candidates.
- Adds guard reasons, expiry, source metadata, safe evidence summaries, and voice flags.
- Keeps current pending memory UI while adding chat hints, undo, and safe source / guard display.
- Explicit auto-save and accepted candidates write visible long-term memory items; undone / inactive, pending, ignored, expired, and rejected candidates are not injected into prompts.
- v1.1.1 keeps memory transparency in UI hints instead of Rei's persona reply. The prompt layer tells Rei not to explain candidate, guard, pending workflow, or long-term-memory mechanics; Rei should only acknowledge the user's boundary or preference naturally and briefly.

### Memory Retrieval v1

Status: implemented as a minimal local-first prompt assembly slice.

- Retrieves only accepted / active Long-term Memory.
- Excludes pending, ignored, expired, rejected, undone / inactive, deleted, `do_not_remember`, assistant / proactive sourced, secret-like, and persona-drift memory.
- Uses explainable v1 structured / heuristic matching over memory type, current input, current game, current boss, input source, and retrieval tags; this is not vector search.
- Builds PromptMemoryBlock with `max_items`, `token_budget`, `omitted_count`, safety notes, safe summaries, and low-priority wording.
- Tracks `last_used_at` and `use_count` when chat retrieval actually injects memory; prompt preview does not increment usage.
- Keeps Persona Core and current explicit user input higher priority than memory.
- Keeps Debug / Prompt Preview safe-summary-only and omits raw prompt, raw transcript, raw JSON, API keys, `.env`, full paths, stdout/stderr, and secrets.

### Persona-Memory Regression Eval v0

Status: implemented as a mock-first eval / tests / docs surface.

- Verifies accepted memory can naturally influence replies without mechanical memory announcements.
- Checks that Persona Core stays higher priority than memory and blocks persona drift such as sweetness, customer-service encouragement, praise loops, or mascot-like behavior.
- Covers gameplay preference, reply-length preference, spoiler preference, accessibility / voice brevity, emotional pattern, multiple-memory budget, game mismatch, assistant-source blocking, secret filtering, pending exclusion, rejected exclusion, and undone / inactive exclusion.
- Uses deterministic prompt assembly checks plus fixed mock reply checks. The mock path is stable enough for automated tests.
- Provides optional live provider evaluation for manual drift checks, but live eval is not required for CI because provider cost, auth, timeout, and model drift should not block local regression.
- Tracks coarse v0 metrics: `prompt_memory_block_correct_count`, `pending_memory_blocked_count`, `inactive_memory_blocked_count`, `persona_drift_blocked_count`, `mechanism_phrase_violation_count`, `mechanical_memory_recall_count`, `persona_override_violation_count`, `secret_leak_count`, and `current_input_priority_count`.
- Keeps eval reports safe by omitting raw prompts and filtering secret-like terms. Reports may show safe reply previews and safe ids, but not raw transcript, raw evidence, API keys, `.env`, full paths, stdout/stderr, or raw provider JSON.
- Known limitation: forbidden phrase checks are intentionally coarse. They catch obvious mechanism leaks and template failures, but real model naturalness still needs occasional human sampling or a future style judge.

### Session Archive v1

- Summarize Session Timeline into safe session archive candidates.
- Keep archive separate from Long-term Memory.
- Promote only repeated user patterns through candidate flow.

### Memory Workspace Polish

- Show Pending / Confirmed / Ignored / Deleted.
- Support delete and revise.
- Show source and guard reason as safe summaries.
- Add duplicate merge explanations.

### Direct Voice Confirmation Flow

- Use short, low-interruption confirmation.
- Avoid confirming implicit candidates during active gameplay.
- Keep uncertain confirmation pending.

## Non-goals For v0

- No vector database.
- No external memory framework.
- No Hermes provider integration.
- No automatic saving of all input.
- No runtime rewrite of Persona Pack.
- No Overlay auto-show.
- No Live2D / Vision.
- No packaging change.
