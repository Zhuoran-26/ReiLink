# ReiLink Voice v2.2 Release Hardening Checklist

Updated: 2026-07-14

Document status: current reusable release gate for Voice v2.2.

## 1. Candidate And Scope

- Candidate tag: `reilink-v0.2-pre.5`.
- Candidate title: `ReiLink Voice v2.2 — Direct Conversation & TTS Foundation`.
- The title matches the delivered scope: Direct Conversation and TTS foundation, not a new production provider or a real-time voice agent.
- This checklist does not create a tag, GitHub Release, push, merge, or rebase.

Voice v2.2 includes:

- user-triggered Local ASR with audio transferred only to ReiLink's local backend;
- stable main-chat `MediaRecorder` capture with user Stop, internal `stopping`, final `dataavailable` / `onstop`, complete Blob construction, and a 30-second safety limit;
- default `confirm_send`, editable unsent drafts, and explicit opt-in `direct_conversation`;
- `idle`, `listening`, `transcribing`, `auto_sending`, `ready_to_send`, `assistant_thinking`, `speaking`, `interrupted`, and `error`;
- capture-stop, actual-duration, empty-text, short-text, caption / stage-direction-only, max-duration, bounded likely-partial, suspicious-output, and completion-time mode guards;
- Voice Profile `full`, deterministic `brief`, and `silent` behavior;
- TTS Strategy v0, TTS Provider Registry v0, System Speech Synthesis, Test Voice, Stop / interrupt, and text-only fallback;
- metadata-only Voice / TTS Event Stream events;
- bounded GameCatalog bootstrap: generic `探索` does not start Hollow Knight, while exact `史东薇尔` and explicit game switching remain supported.

Voice v2.2 does not include silence detection / VAD, streaming ASR, hands-free or always-listening behavior, wake word, speaker diarization, automatic next-round recording, full duplex, custom character voice, local neural TTS, production external / streaming TTS providers, TTS API keys, cloud audio upload, voice cloning, or Overlay Voice state.

## 2. Automated Regression

Run release validation from a clean `dev/codex-reilink` worktree. Record the exact commit, command, exit status, and test count.

```bash
git diff --check

cd apps/desktop
npm run lint
npm test
npm run build

cd ../../services/backend
. .venv/bin/activate
python -m pytest
```

Core Voice coverage must include:

- final audio chunks, delayed recorder finalization, actual capture duration, pending microphone permission, natural pause, user Stop, cancellation, and 30-second max duration;
- confirm-send draft behavior and Direct Conversation explicit opt-in;
- empty, `嗯`, short recording with longer hallucinated text, caption / stage direction, common likely partial, max-duration, and mode-change guards;
- exactly one auto-send for a normal complete sentence;
- no chat / reply / Extraction / Memory / proactive / Game Context side effects for blocked input;
- generic `探索` no-bootstrap, exact Stormveil detection, and explicit Hollow Knight switch;
- `auto_sending`, `assistant_thinking`, speaking / interrupted, Stop Voice, full / brief / silent, TTS unavailable, provider resolution, provider UI, and Event Stream redaction.

Validate every changed QA JSON with `JSON.parse` or another structured parser and run the repository's QA JSON tests. Do not weaken privacy assertions or add credentials, raw authorization values, raw prompts, provider raw config, transcripts, or user-specific absolute paths to fixtures.

Run the repository safety scan:

```bash
git grep -n -I -E 'sk-[A-Za-z0-9_-]+'
```

Expected: no output.

Docs-only, QA-JSON-only, or pure-test-data changes may run focused docs / QA tests instead of desktop lint / test / build and full backend pytest when the final diff contains no renderer, Electron main, backend runtime, shared API, packaging, Extraction, GameCatalog, Persona, Memory, or other runtime file. The completion report must list the final diff and the reused runtime baseline.

## 3. Evidence Method Labels

Every result must name its method. Do not report simulated or system-rerecorded audio as complete real-human-microphone acceptance.

| Method | What it proves | What it does not prove |
| --- | --- | --- |
| Automated test | Repeatable state, reason, side-effect, and privacy assertions | Real device or human microphone acceptance |
| Simulated MediaRecorder | Final chunks, delayed `onstop`, actual duration, pending permission, and timer boundaries | Browser encoding, OS permission prompts, or physical microphone quality |
| Controlled transcript | Exact empty / short / caption / partial / mode / GameCatalog decisions | That the ASR model generated the text |
| System-speech rerecord | Near-real speaker-to-microphone-to-ASR path | Human accent, physical tapping, or all ambient noise |
| Real microphone | Current machine permission, capture, ASR, draft / auto-send, and exit behavior | Other machines, models, accents, or environments |
| User manual test | Visible UI, interaction rhythm, playback, and recovery | A replacement for automated regression or unrun edge cases |

## 4. Manual Smoke

- [ ] App starts, main window is not black, and backend reaches connected state.
- [ ] Normal typed chat sends and receives a text reply.
- [ ] Voice workspace Conversation, Input / Local ASR, Output, and Voice Profile tabs render.
- [ ] Main recording crosses old 3-second / 5-second boundaries and a natural pause without stopping; Audio Capture Probe remains a separate 3-second test.
- [ ] User Stop enters capture `stopping`, waits for final recorder data, and only then starts ASR.
- [ ] `confirm_send` is the default; transcript is editable, clearable, replaceable by re-recording, and remains unsent.
- [ ] Direct Conversation requires explicit opt-in and a user-triggered recording round.
- [ ] Switching modes does not send an existing draft; disabling Direct Conversation during capture returns the round to confirm-send.
- [ ] Empty, `嗯`, sub-800 ms capture with longer hallucinated text, `(字幕:J Chong)`, `(拍摄)`, `[Music]`, common partial, and 30-second max-duration cases do not auto-send.
- [ ] Blocked non-empty text remains editable and creates no user turn, Rei reply, Extraction, Memory, proactive, Game Context, or Boss update.
- [ ] A normal complete sentence auto-sends once in Direct Conversation.
- [ ] Generic `探索` does not bootstrap Hollow Knight; exact `史东薇尔` selects Elden Ring and an explicit Hollow Knight switch still applies.
- [ ] Voice states render without overlap and include visible auto-send, thinking, speaking, interrupted, and recoverable-error feedback.
- [ ] Voice Profile full / brief / silent keeps the full text reply and applies only the expected speech behavior.
- [ ] Test Voice starts only from the explicit control; Stop Voice interrupts active playback when it can be observed.
- [ ] System Speech Synthesis is the only selectable provider; Local TTS and External TTS remain disabled placeholders.
- [ ] Event Stream shows safe metadata without full transcript, raw ASR output, raw audio, assistant reply, spoken text, prompt, credential, provider config, path, or raw stderr.
- [ ] Settings and Developer / Debug render normally.
- [ ] Quitting releases microphone tracks, the app-owned backend, and port 8000.

## 5. Packaged App Regression

Rebuild and smoke the packaged app after any backend API, shared API, renderer UI, Electron main, packaging, or packaged-runtime change:

```bash
make package-backend
make package-desktop
```

Open `apps/desktop/release/ReiLink-darwin-<arch>/ReiLink.app` and run the manual smoke against the bundled backend. Stop Voice can be accepted through explicit automated coverage only when active playback cannot be captured manually; record that limitation instead of claiming a manual pass.

Docs-only, QA-JSON-only, or pure-test-data changes that do not alter runtime may reuse the latest relevant packaged smoke. Name the baseline commit and method coverage, and explain why rebuilding would not test any changed executable behavior.

## 6. Privacy And Repository Safety

Voice / TTS events may store event type, provider id / status, fallback flag, source / mode, profile, capture duration, audio-format summary, stop reason, quality, send decision, safe guard reason, character counts, and completed / stopped / interrupted / unavailable status.

They must not store or render:

- full or partial transcript text as event content;
- raw ASR output, raw audio, audio content, or base64 audio;
- full assistant reply, spoken text, or Test Voice fixed text;
- raw prompt, persona markdown, provider raw response / config, or raw JSON dump;
- `.env`, API keys, raw Authorization values, or secret-like tokens;
- local absolute paths, raw stdout, or raw stderr.

System Speech Synthesis means ReiLink delegates selected text to platform `speechSynthesis`. The verified application boundary is that ReiLink integrates no external TTS endpoint or TTS API key; do not turn that into an undocumented platform privacy promise.

## 7. Known Limitations

- Local ASR can misrecognize game terms, long Chinese sentences, accents, and noisy speech; accuracy and latency depend on the local model, microphone, hardware, and environment.
- The Local ASR response exposes no renderer-usable no-speech probability, segment confidence, or average log probability. Do not invent or claim confidence.
- Partial detection is bounded and best-effort, not complete semantic endpointing. ASR may remove punctuation or make incomplete speech look complete, so some unfinished utterances may pass.
- Do not pursue complete coverage through open-ended sentence-final regexes, unlimited keyword lists, or typo aliases. Use default `confirm_send` when strict review is required.
- Caption protection is finite transcript-structure detection, not VAD. Fully bracketed natural language can be conservatively blocked and remains manually editable.
- Voice v2.2 is click-to-record / push-to-talk, not streaming ASR, hands-free, always-listening, wake-word, or full duplex.
- System voices are not character-grade and may pronounce names or game terms unnaturally. Stop is best-effort through platform cancellation.
- No cloud ASR / audio upload, local neural TTS, production external TTS, streaming TTS, custom voice, voice cloning, or Overlay Voice state.
- The macOS package remains an unsigned local build.

## 8. Release Gate

- [ ] Required tests are green for the final diff scope.
- [ ] QA JSON parses and the v2.2 release matrix resolves to existing unique scenario ids.
- [ ] State names, stop reasons, guard reasons, quality values, and provider capabilities match runtime code.
- [ ] Repository safety and secret scans have no unexpected match.
- [ ] Packaged backend and desktop builds are green when runtime scope requires them.
- [ ] Packaged smoke is green or a docs / test-only reuse decision is documented.
- [ ] Event Stream payload and rendered summaries pass privacy verification.
- [ ] No secret-like fixtures, raw authorization values, raw prompts, transcripts, or user-specific absolute paths were added.
- [ ] README, project status, Voice specs, QA, provider docs, checklist, and release note are aligned.
- [ ] Partial-guard, ASR-confidence, caption false-positive, and real-time-voice limitations are explicit.
- [ ] Candidate tag / title are recorded without creating a tag or release.
- [ ] Worktree is clean after the release-documentation commit.
- [ ] No push, main merge, rebase, tag, or GitHub Release was performed.

## 9. Reused Runtime Baseline

Runtime baseline: `6e9512e fix: harden direct conversation auto-send safety` on `dev/codex-reilink`. This evidence comes from the implementation hardening runs and is reused by later docs-only alignment; it is not relabeled as a new runtime run.

| Check | Result | Evidence |
| --- | --- | --- |
| Desktop automated | Passed | Renderer 213 / 213 and Electron main 48 / 48 passed at the runtime baseline. |
| Backend automated | Passed | Full backend 667 / 667 passed; focused Game / Knowledge / Dialogue regression 104 passed. |
| Extraction regression | Passed | Focused extraction 131 passed and deterministic mock eval passed 40 / 40. No live eval was required. |
| Simulated capture / controlled transcript | Passed | Final chunk, delayed teardown, actual duration, pending permission Stop, natural pause, short capture hallucination, captions, common partial, max duration, mode change, privacy, and side-effect boundaries passed. |
| System-speech rerecord | Passed with stated scope | Common partial and `嗯` were blocked; a normal complete sentence auto-sent. This is not human-microphone or physical-tapping coverage. |
| Real microphone | Passed with stated scope | Immediate silent Stop returned without chat or game update; a 30-second capture remained an unsent draft. Empty immediate Stop produced no draft because there was no transcript. |
| GameCatalog acceptance | Passed | Clean-context noisy `探索` stayed null across text / voice-confirmed / voice-direct; exact `史东薇尔` selected Elden Ring; explicit Hollow Knight switch applied. |
| Packaged backend / desktop | Passed | Backend and desktop packages were rebuilt for the runtime baseline. |
| Packaged UI / exit smoke | Passed | App was non-black and backend-connected; chat, Voice, Settings, Debug, provider placeholders, and privacy surfaces rendered; graceful quit removed the app-owned backend and released port 8000. Active Stop Voice visibility remains a manual recheck focus if playback timing cannot be captured. |

## 10. Docs Alignment Run

For a docs / QA-only alignment commit, record `git diff --check`, structured JSON parsing, QA scenario tests, code-name searches, repository safety, secret scan, final changed-file scope, and clean worktree. Packaging, packaged smoke, extraction mock / live eval, and Persona-Memory eval are not rerun when no executable behavior changed; the completion report must state that basis.

Current alignment run: 2026-07-14 on `dev/codex-reilink`, based on runtime commit `6e9512e`.

| Check | Result | Evidence |
| --- | --- | --- |
| Diff scope | Passed | Final candidate diff is limited to Markdown and Voice QA JSON; no runtime, renderer, Electron main, backend, shared API, packaging, Extraction, GameCatalog, Persona, or Memory file changed. |
| Format / JSON | Passed | `git diff --check` passed; 23 QA JSON files parsed, 600 unique scenario ids were found, 44 Voice v2.2 refs resolved, and requirements 1-30 remained complete. |
| Repository docs / QA tests | Passed | `python -m pytest tests/test_qa_scenarios.py`: 44 / 44 passed. |
| Runtime-name audit | Passed | Source search confirmed the nine states, four capture stop reasons, seven quality values, eight block reasons, `confirm_send` default, 800 ms / four-character thresholds, 30-second limit, and TTS provider ids / capabilities. |
| Repository safety / secret scan | Passed | Changed paths contain only allowed docs / QA assets; no forbidden artifact path, secret-like token, credential value, or user-specific absolute path was added. |
| Packaging / packaged smoke | Reused | Not rerun because no executable or packaging input changed; runtime and packaged baseline remains `6e9512e`. |
| Mock / live eval | Not required | No semantic extraction, model routing, Persona, Memory, or eval behavior changed. |
