# ReiLink Voice v2.2 Release Hardening Checklist

Updated: 2026-07-12

Document status: current reusable release gate for Voice v2.2.

## 1. Scope

Voice v2.2 includes:

- user-triggered Local ASR with audio transferred only to ReiLink's local backend;
- default `confirm_send` and explicit opt-in `direct_conversation`;
- `idle`, `listening`, `transcribing`, `auto_sending`, `ready_to_send`, `assistant_thinking`, `speaking`, `interrupted`, and `error`;
- empty-text, short-text, short-recording, and likely-partial auto-send guards;
- Voice Profile `full`, deterministic `brief`, and `silent` behavior;
- TTS Strategy v0, TTS Provider Registry v0, System Speech Synthesis, Test Voice, Stop / interrupt, and text-only fallback;
- Event Stream metadata-only Voice / TTS events.

Voice v2.2 does not include hands-free or always-listening behavior, wake word, speaker diarization, automatic next-round recording, custom character voice, local neural TTS, external / streaming TTS providers, TTS API keys, cloud audio upload, voice cloning, or Overlay Voice state.

## 2. Automated Regression

Run from a clean `dev/codex-reilink` worktree. Record the command, exit status, and test count in the release evidence.

From the repository root:

```bash
git diff --check
```

Expected: exit 0 with no whitespace errors.

From the repository root:

```bash
cd apps/desktop
npm run lint
npm test
npm run build
```

Expected: lint, renderer / main tests, and production build all pass. Core Voice coverage must include confirm-send, Direct Conversation auto-send, all four guards, `auto_sending`, `assistant_thinking`, speaking / interrupted, Stop Voice, full / brief / silent, TTS unavailable, provider resolution, provider UI surface, and Event Stream redaction.

From the repository root:

```bash
cd services/backend
. .venv/bin/activate
python -m pytest
```

Expected: full backend regression passes. This task does not require extraction or Persona-Memory live eval because it does not change semantic extraction, model routing, persona assembly, memory retrieval, or Persona-Memory behavior; their runner tests remain covered by backend pytest.

From the repository root:

```bash
git grep -n -I -E 'sk-[A-Za-z0-9_-]+'
```

Expected: no output.

Validate every changed QA JSON with `JSON.parse` or an equivalent structured parser. Do not weaken privacy assertions or add secret-like credentials, raw authorization values, raw prompts, raw provider config, or user-specific absolute paths to fixtures.

## 3. Manual Smoke

- [ ] App starts and the main window is not black.
- [ ] Backend reaches connected state.
- [ ] Normal typed chat sends and receives a text reply.
- [ ] Voice workspace opens; Conversation, Input / Local ASR, Output, and Voice Profile tabs render.
- [ ] Local ASR setup entry remains available and paths are not exposed in Event Stream.
- [ ] Confirm-send fills the composer and waits for user confirmation.
- [ ] Direct Conversation requires explicit opt-in and a user-triggered recording round.
- [ ] Disabling Direct Conversation restores confirm-send.
- [ ] Empty, short, short-recording, and likely-partial guards do not auto-send or trigger memory / proactive behavior.
- [ ] Voice states render without overlap and include visible `auto_sending`, thinking, speaking, interrupted, and recoverable error feedback where applicable.
- [ ] Voice Profile full / brief / silent keeps the full text reply and applies only the expected speech behavior.
- [ ] Test Voice starts only from the explicit control.
- [ ] Stop Voice interrupts Test Voice or assistant playback when active.
- [ ] System Speech Synthesis is the only selectable provider; Local TTS and External TTS remain disabled placeholders.
- [ ] Event Stream shows safe human-readable summaries without full transcript, assistant reply, or spoken text.
- [ ] Settings and Developer / Debug render normally.
- [ ] Quitting the app leaves no bundled backend process started by the app.

## 4. Packaged App Regression

Rebuild and smoke the packaged app after any backend API, shared API, renderer UI, Electron main, packaging, or packaged-runtime change. Backend API or backend runtime changes require packaging backend first:

```bash
make package-backend
make package-desktop
```

Then open `apps/desktop/release/ReiLink-darwin-<arch>/ReiLink.app` and run the manual smoke above. Confirm backend health from the bundled runtime, not only a separate dev backend. Stop Voice can be accepted through explicit automated coverage only when active playback cannot be captured manually; record that limitation rather than claiming a manual pass.

Docs-only, QA-JSON-only, or pure-test changes that do not alter runtime / UI / shared / backend behavior may reuse the latest relevant packaged smoke. The completion report must name the reused baseline and explain why a rebuild was unnecessary.

## 5. Privacy And Safety

Voice / TTS events may store event type, provider id / status, fallback flag, source, profile, character counts, duration, safe guard reason, and completed / stopped / interrupted / unavailable status.

They must not store or render:

- full or partial transcript text as event content;
- full assistant reply or spoken text;
- Test Voice fixed text;
- raw ASR output, audio content, or base64 audio;
- raw prompt, persona markdown, or raw JSON dump;
- `.env`, API keys, raw Authorization values, or secret-like tokens;
- local absolute paths, raw stdout / stderr, provider raw response, or provider raw config.

System Speech Synthesis means ReiLink delegates selected text to the platform `speechSynthesis` implementation. The verified application boundary is that ReiLink does not integrate an external TTS endpoint or TTS API key; do not turn that into an undocumented platform privacy promise.

## 6. Known Limitations

- Voice v2.2 is push-to-talk / click-to-record, not a full real-time voice agent.
- Local ASR requires user-managed binary, model, and converter paths.
- ASR accuracy and latency depend on local model, microphone, noise, and hardware.
- System voices are not character-grade and may pronounce names or game terms unnaturally.
- Stop is best-effort through platform speech cancellation.
- No hands-free, wake word, diarization, cloud ASR, cloud audio upload, local neural TTS, external TTS, streaming TTS, custom voice, or voice cloning.
- Overlay does not currently display Voice state.
- The macOS package remains an unsigned local build.

## 7. Release Gate

- [ ] Required tests are green.
- [ ] QA JSON parses and the v2.2 release matrix resolves to existing scenario ids.
- [ ] Repository safety scan has no secret-like match.
- [ ] Packaged backend and desktop builds are green when runtime scope requires them.
- [ ] Packaged smoke is green or a docs/test-only reuse decision is documented.
- [ ] Event Stream payload and rendered summaries pass privacy verification.
- [ ] No secret-like fixtures, raw authorization values, raw prompts, or user-specific absolute paths were added.
- [ ] README, project status, Voice specs, QA, provider docs, checklist, and release note are aligned.
- [ ] Historical Voice docs are marked historical / superseded.
- [ ] Current limitations and future-only capabilities are documented.
- [ ] Worktree is clean after the release-hardening commit.
- [ ] No push, main merge, rebase, tag, or GitHub Release was performed by this checklist.

## 8. Hardening Run Evidence

Latest local hardening run: 2026-07-12 on `dev/codex-reilink`. Replace this evidence for a later release candidate rather than assuming it remains current.

| Check | Result | Evidence |
| --- | --- | --- |
| Focused Voice tests | Passed | `App.test.tsx` 150 and `ttsProviderRegistry.test.tsx` 5 passed. |
| QA JSON / matrix | Passed | 23 QA JSON files parsed, 570 unique scenario ids, all matrix references resolved, and requirements 1-30 were complete. |
| Desktop lint / test / build | Passed | Lint passed; renderer 181 / 181 and main 48 / 48 passed; production build passed. |
| Backend pytest | Passed | 622 / 622 passed, including the v2.2 release-matrix validator. |
| Repository safety | Passed | Required `git grep` and working-tree secret-like scan returned no match. |
| Packaged backend / desktop | Passed | `make package-backend` completed before `make package-desktop`; packaged app includes the rebuilt bundled backend. |
| Packaged smoke | Passed | Packaged app was non-black and backend-connected; typed chat returned HTTP 200 and rendered both reply segments; Voice v2.2 Conversation / Input / Output / Profile, mode toggle, Local ASR setup, provider placeholders, Settings, and Debug rendered. Test Voice entered speaking; Stop showed interrupted / stopped feedback. Event Stream showed provider / status / source / profile / count only and omitted test text, assistant text, environment labels, authorization data, and local paths. Graceful quit removed the app-started backend and released port 8000. |
| Mock / live eval | Not required | No extraction, routing, persona, memory retrieval, or Persona-Memory behavior change. |
