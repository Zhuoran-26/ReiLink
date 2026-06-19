# Session Archive v1 Architecture

Status: Session Archive runtime v1 is implemented for manual safe-summary archive, local persistence, recent-session UI, list / read / delete / clear, and privacy-boundary tests. This document still does not implement archive search runtime, vector search, Archive-to-Memory Candidate runtime, prompt retrieval, Voice changes, Overlay changes, or packaging changes.

## Product Positioning

Session Archive is:

```text
A safe, user-controlled session history summary and review layer.
```

Session Archive is not:

```text
Permanent full chat history
Automatic long-term memory
Vector database
Full prompt-history injection
Monitoring log
Raw voice transcript store
```

It should help the user review where they left off, give ReiLink a future path for recent-session continuity, provide a safe source for possible Memory Candidates, support future local Session Search, and preserve local-first privacy boundaries. Archive data must remain deletable, clearable, and disableable by the user.

## Layer Boundaries

### Working Context

Working Context is the current turn and short-lived conversation context. It may affect the current reply, but should not be treated as a durable archive or long-term memory.

### Game Session State

Game Session State is the current play-session state produced by guarded semantic extraction:

- `current_game`
- `current_boss`
- `death_count`
- `frustration_count`
- `current_activity`

It is not Session Archive and is not Long-term Memory. It may produce safe summaries that become Session Archive input if archive is enabled.

### Session Timeline v1

Session Timeline v1 already exists as safe event summaries for the current renderer session. It is non-persistent by default and can be an input source for Session Archive.

### Session Archive

Session Archive is an optional persistent safe-summary layer. It stores session summaries and safe event summaries, not raw prompt text, raw provider JSON, raw chat transcripts, raw voice audio, secrets, or complete local paths.

It does not directly enter the prompt. Future Session Retrieval would need explicit gates and budget limits before any safe archive summary could influence prompt assembly.

### Memory Candidate

Memory Candidate is a guarded candidate for a durable user preference, habit, or fact. Archive summaries can only become Memory Candidates through a detector plus memory guard plus user confirmation.

### Long-term Memory

Long-term Memory is accepted user-confirmed memory. Only accepted / active Long-term Memory can be retrieved by Memory Retrieval v1 and placed into `PromptMemoryBlock`.

### PromptMemoryBlock

`PromptMemoryBlock` remains safe-summary-only and currently contains accepted / active Long-term Memory. Session Archive is excluded by default.

## Archive Content Boundary

Allowed archive content:

- Game context safe summaries: game name, boss / area, death count summary, cleared boss, frustration trend, current activity.
- Session Timeline safe events: boss changed, death count changed, knowledge used, memory accepted / ignored, proactive shown.
- User-visible safe summaries such as `用户在玛尔基特处多次失败`.
- Retrieval / memory usage safe summaries such as `本轮使用了 2 条已确认记忆`.
- Voice mode metadata such as `voice_direct` or `voice_confirmed`, without full transcript by default.

Forbidden archive content:

- raw prompt
- raw model response
- raw JSON
- API key, `.env`, Authorization, bearer token, or other secrets
- full local path
- stdout / stderr
- raw voice audio
- full voice transcript by default
- unredacted raw chat transcript by default
- rejected sensitive memory
- assistant / proactive generated text as a user fact
- unconfirmed Memory Candidate as a long-term fact

## Default Policy

Runtime v1 default:

- Persistent Session Archive is user-controlled through a manual `归档当前会话` action.
- Current-session notes remain short-lived local safe summaries until the user explicitly archives them.
- Manual archive stores safe summaries only.
- Suggested retention: latest 20 sessions or 30 days, whichever is smaller. A stricter privacy mode can use 7 days.
- User controls should include clear archive, delete one session archive entry, and future disable / export.
- Direct Conversation / Voice should not save full transcript or raw audio by default.
- Overlay should not show sensitive archive content.
- Debug / Prompt Preview may show archive safe event summaries, counts, and skip reasons only.

This default is conservative because Session Archive sits between transient session state and durable memory. Runtime v1 is a manual local archive action, not an invisible expansion of memory.

## Runtime v1 Scope

Runtime v1 implements:

- Local file persistence at the backend session data path: `data/session/session_archives.json` in dev, or the packaged user data session directory.
- `GET /session-archives`
- `GET /session-archives/{archive_id}`
- `POST /session-archives/archive-current`
- `DELETE /session-archives/{archive_id}`
- `POST /session-archives/clear`
- Memory workspace `最近会话` tab with archive current, refresh, read detail, delete, and clear controls.
- Safe event stream summaries: `session_archive_created`, `session_archive_deleted`, `session_archive_cleared`, and `session_archive_skipped`.

Runtime v1 deliberately does not implement:

- auto archive on lifecycle events
- local keyword archive search
- semantic / vector search
- Archive-to-Memory Candidate runtime
- prompt archive retrieval
- raw transcript, raw prompt, raw JSON, audio, secrets, or full local path storage
- Memory Retrieval changes
- Persona, Direct Conversation, Overlay, Live2D, or Vision changes

Archive entries are soft-deleted for local auditability and hidden from list / read responses after delete or clear.

## Data Model Draft

### SessionArchiveEntry

```text
id
session_id
created_at
updated_at
started_at
ended_at
source
game
area
boss
summary
event_count
safe_event_summaries
memory_candidate_count
accepted_memory_count
privacy_level
retention_policy
is_deleted
deletion_status
```

### SessionArchiveEvent

```text
id
session_id
timestamp
event_type
safe_summary
source
input_source
related_game
related_entity
risk_flags
privacy_level
can_generate_memory_candidate
```

### SessionArchiveSearchResult

```text
archive_id
event_id
relevance_score
reason
safe_summary
matched_tags
related_game
related_entity
```

### ArchiveToMemoryCandidateBridge

```text
archive_event_id
candidate_type
candidate_summary
evidence_summary
confidence
requires_confirmation
guard_reason
status
```

## Archive -> Memory Candidate Bridge

Session Archive must not directly become Long-term Memory.

Correct flow:

```text
Session Archive safe event summary
-> archive-to-memory candidate detector
-> memory guard
-> pending Memory Candidate
-> user accept / ignore
-> Long-term Memory
```

Good bridge signals:

- Repeated preference across sessions, such as consistently avoiding spoilers.
- Repeated interaction preference, such as repeatedly asking for shorter replies.
- Stable gameplay habit, such as repeatedly exploring before bosses.
- Explicit save request, such as `以后都记住这个`.
- User correction, such as `不是，我不是想要详细攻略`.

Signals that should not generate Memory Candidates:

- A single death event.
- A single emotional spike.
- Assistant / proactive content alone.
- Low-confidence guesses.
- Rejected, sensitive, or secret content.
- Game knowledge itself.
- Unconfirmed archive summary treated as fact.

The bridge should produce evidence summaries, not raw evidence. It should set `requires_confirmation=true` except for a future explicit user save flow that reuses the existing Memory Candidate guard and undo pattern.

## Session Search

Session Search v1 should be local, safe-summary-only, and non-vector by default.

Supported filters:

- game, such as Elden Ring or Hollow Knight
- boss / area
- event type, such as death, cleared, memory accepted, knowledge used
- time range
- safe summary keyword

Result requirements:

- Show only `safe_summary`.
- Hide raw transcript, raw prompt, raw provider JSON, secrets, and local paths.
- Include why a result matched, using safe labels such as game, boss, event type, or matched tag.
- Support future delete for the related archive entry.

Future semantic search can be explored later, but v1 must not require vector database or external retrieval services.

## Prompt Assembly Boundary

Session Archive does not enter prompt by default.

Future Session Retrieval would require:

- recency gate
- relevance gate
- token budget
- safe-summary-only data
- user control
- privacy-level filter
- current-input priority check

Priority order remains:

1. App safety / privacy boundary
2. Persona Core
3. Current user input
4. Accepted / active Long-term Memory
5. Future gated Session Archive summary

Long-term Memory has higher priority than Session Archive because it is user-confirmed and intentionally durable.

## UI / Workspace Direction

Future Memory workspace can expand into:

- Saved Memories
- Pending Memories
- Session Archive / Recent Play Summaries
- Delete / Clear / Privacy Settings

Session Archive UI should support:

- recent session list
- session safe summary
- event timeline
- local search
- delete session archive
- clear all archive
- disabled state explanation
- user confirmation when archive produces a Memory Candidate

Voice / Direct Conversation should not show blocking prompts during active play. A session-end hint such as `本局有 1 条可能值得保存的偏好` is acceptable if it is non-blocking and user-controlled.

## Privacy And Safety

- Local-first by default.
- Archive is not uploaded by default.
- Raw voice audio is not saved by default.
- Full voice transcript is not saved by default.
- Secrets are never archived.
- User can clear archive.
- User can disable archive.
- Archive is not Long-term Memory.
- Archive is not prompt context.
- Debug / Prompt Preview shows only archive safe summaries, counts, and skip reasons.

## QA Scenarios

Machine-readable architecture scenarios live in:

```text
docs/qa/session_archive_scenarios.json
```

Machine-readable runtime scenarios live in:

```text
docs/qa/session_archive_runtime_scenarios.json
```

Architecture scenarios cover safe archive input, forbidden raw content, voice transcript boundaries, memory bridge requirements, search safe summaries, user delete / disable controls, retention, export placeholder, prompt exclusion, current-input priority, Persona Core priority, and privacy-level retrieval blocking.

Runtime scenarios cover manual archive-current, safe summary generation, local persistence, list / read / delete / clear, UI rendering, empty timeline skipping, repeated archive idempotency, Event Stream safety, and prompt / memory privacy boundaries.

## Implementation Roadmap

1. Session Archive v1 runtime: local safe-summary persistence, latest-20 retention, delete / clear, and Memory workspace recent sessions tab. Implemented.
2. Archive Search v1: local keyword and structured filters over safe summaries.
3. Archive-to-Memory Candidate v1: repeated-pattern detector plus Memory Candidate guard and user confirmation.
4. Session Archive UI expansion: search, filters, retention controls, and future export.
5. Optional semantic search later: only after safe-summary storage, privacy filters, and user controls are stable.
