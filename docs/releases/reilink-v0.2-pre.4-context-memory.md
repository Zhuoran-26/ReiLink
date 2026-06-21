# ReiLink v0.2-pre.4 - Context & Memory System

Draft: 2026-06-20

This is a draft release note for the Context & Memory system readiness pass. It is not a tag, push, or published release.

## Highlights

- LLM-primary Guarded Extraction v1 pilot is the foreground semantic reader for game-context candidates, with deterministic guard decisions and rule fallback.
- Candidate Memory v1 / v1.1 provides guarded memory candidates, explicit auto-save where safe, undo, pending confirmation, and safe source summaries.
- Memory Retrieval v1 injects only accepted / active Long-term Memory into a bounded low-priority PromptMemoryBlock.
- Persona-Memory Eval v0.1 adds mock-first regression coverage plus optional live warning tiers for memory-influenced replies.
- Session Archive Runtime v1 provides manual local safe-summary archive, `最近会话` UI, list / read / delete / clear, and empty-timeline skip handling.
- Archive Search v1 provides safe keyword and structured-filter search over archive summaries.
- Archive-to-Memory Candidate Bridge v0 provides explicit user-triggered safe-summary scanning into pending Memory Candidates.

## Safety / Privacy

- Session Archive stores safe summaries only, not raw chat, raw prompt, raw provider JSON, raw voice audio, full voice transcript, secrets, or full local paths.
- Session Archive and Archive Search do not enter PromptMemoryBlock.
- Archive-to-Memory Bridge does not write Long-term Memory directly; it can only create pending candidates through explicit user action and existing memory guards.
- Pending, ignored, rejected, expired, undone, assistant-source, proactive-source, secret-like, and persona-drift memory is excluded from prompt assembly.
- Only accepted / active Long-term Memory can enter PromptMemoryBlock.
- Persona Core remains higher priority than memory.
- Debug, Prompt Preview, Event Stream, archive UI, and QA reports must stay safe-summary-only.

## Suggested Manual QA

1. Run backend QA scenarios and full backend tests.
2. If desktop/runtime changed, run desktop lint, tests, and build.
3. If packaged behavior changed, run `make package-backend`, then `make package-desktop`.
4. Open Memory workspace and confirm `最近会话` / `会话归档` is visible.
5. Confirm archive empty state, `归档当前会话`, `刷新`, delete, clear, search, and explicit candidate scan surfaces are safe.
6. Confirm empty timeline archive skips without error.
7. Confirm accepted memory can influence replies quietly, while pending / rejected / undone memory cannot.
8. Confirm Prompt Preview and Event Stream never show raw prompt, raw JSON, secrets, full transcript, or full local path.
9. Confirm Settings and Voice workspaces still open normally.
10. Confirm packaged app has no backend residual process after quit when packaged smoke is required.

## Known Limitations

- No vector search or embedding retrieval.
- No semantic archive search.
- No archive search auto-candidate generation.
- No prompt archive retrieval.
- No external memory provider.
- No archive export or advanced archive UI.
- No archive scan audit-count dashboard beyond current safe summaries.
- No TTS Strategy v2, Overlay auto-show restore, Live2D, or Vision runtime.

## Release Boundary

This draft documents the current Context & Memory readiness baseline. Publishing, tagging, pushing, merging, or rebasing must be handled separately by the project owner.
