# UI/UX Information Architecture v0

Updated: 2026-06-16

This document records the UI/UX IA baseline and the implemented UI Surface v0. UI Surface v0 adds an in-app Panel Launcher & Workspace Shell in the existing React renderer. It does not implement Voice v2, Overlay auto-show, Hermes-style memory, Live2D, or any Electron multi-window change.

## Scope

ReiLink is a Chinese-first desktop AI companion for single-player game players. The current app already has chat, settings, local ASR, voice output, overlay safe mode, memory confirmation, game context, knowledge trace, prompt preview, event stream, semantic shadow diagnostics, and persona pack summaries. These features work, but the product surface now feels like a single stacked diagnostics page instead of a calm companion product.

The v0 IA goal is to define where each capability belongs before changing React structure. The next implementation should preserve existing backend, memory, proactive, Semantic Shadow, persona, packaging, and privacy boundaries.

## Implemented UI Surface v0

UI Surface v0 is now implemented in the desktop renderer:

- The left navigation is a workspace launcher rather than anchor links.
- Home / Chat is the default surface. The right workspace panel is closed by default, so Settings, Debug, Prompt Preview, Event Stream, and feature detail panels do not crowd the ordinary chat view.
- Memory, Game, Voice, Overlay, Settings, Developer / Debug, and Future / Avatar open as focused in-app workspaces.
- Workspaces have titles, tabs, a close button, and Escape-to-close behavior.
- Chat history and unsent chat input remain mounted while workspaces switch.
- Voice now has Conversation, Input / Local ASR, Output, and Voice Profile placeholder tabs. Current Local ASR and Voice Output controls are findable there, but direct spoken conversation is still not implemented.
- Overlay now has Safe Mode, Placement, Content, and Future Game Mode tabs. Safe Mode remains fail-closed on macOS; auto-show was not restored.
- Developer / Debug now owns Event Stream, Prompt Preview, Runtime diagnostics, and Semantic Shadow trace surfaces. Prompt Preview remains a safe summary and does not expose full prompt or persona markdown.
- Future / Avatar is only a placeholder. No Live2D runtime, assets, or presentation layer were added.

Settings still carries some legacy configuration details for regression stability, but the product surface now gives Voice, Overlay, Memory, Game, and Developer / Debug their own homes. A later Debug Split / Settings cleanup can reduce duplicated feature detail.

## Current UI Problems

1. The right side is overloaded. Settings, Memory, Game Context, Debug, Prompt Preview, Event Stream, Voice, Overlay, Local Data, and reset controls compete for the same visual lane.
2. The left navigation behaves mostly like an anchor list. It jumps to sections inside one long surface instead of opening distinct workspaces with clear ownership.
3. Normal user experience and developer diagnostics are mixed. A player can easily land inside Debug, Prompt Preview, Raw JSON, Semantic Shadow trace, or Event Stream even when they only want to talk to Rei.
4. Settings carries too much product weight. It currently holds ordinary preferences, Voice Input / Output, Local ASR setup, Overlay safe mode, backend runtime status, local data controls, game selection, proactive controls, and some reset flows.
5. Voice, Overlay, and Memory all exist, but their product positions are still ambiguous. They are features in Settings or side cards rather than first-class companion surfaces.
6. Debug is valuable for development and QA, but it should not be part of the default ordinary-user journey.
7. Adding Candidate Memory, Session Archive, direct voice loop, Voice Profile, richer Overlay, or Avatar presentation into the current layout will make the page more crowded and harder to test.
8. Prompt Preview is especially sensitive. It must remain a safe summary surface and should live inside Developer / Debug, not near ordinary chat controls.
9. Game Session state and Memory are easy to confuse in the current IA. Game state is short-lived session context; Memory is user-approved longer-term preference or history.
10. Overlay currently has a safe-mode implementation and should not be described as a complete in-game HUD or full overlay companion experience.

## Product Surface Principles

- Chat is the default home. Ordinary users should land in a calm chat workspace, not a debug console.
- Left navigation should be a workspace launcher. Clicking a top-level item should open a workspace, panel, or focused surface, not only scroll to an anchor.
- Debug is opt-in. Developer surfaces should be available but visually and conceptually separated from the player companion experience.
- Voice deserves a first-class home. Current Local ASR is transcript-first, but the long-term product direction is direct spoken conversation with clear state and interruption handling.
- Overlay is a game-safe companion surface, not a replacement for the main app. It should remain fail-closed on macOS until a dedicated packaged QA pass restores auto-show safely.
- Memory needs user trust. Candidate and confirmed memory should be understandable, editable, and separate from game-session state.
- Settings should become configuration, not a dumping ground. Feature-specific setup belongs near the feature workspace, with advanced details collapsed or moved to Developer.
- Future Avatar / Live2D is presentation, not core interaction. It should not outrank Voice, Overlay, or Memory.

## Recommended Top-Level IA

| Module | Target User | Main Content | Child Tabs / Functions | Default? | Game Mode Fit | Audience | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Home / Chat | Player | Main chat, Rei status, current game chips, input, latest companion state | Chat, Today, Quick actions, compact status | Yes | High | Normal user | P0 |
| Memory | Player | Pending memory, confirmed memory, ignored memory, memory source summaries | Pending, Confirmed, Ignored, Search, Sources, Session Archive later | No | Medium | Normal user | P1 |
| Game | Player | Current game, current boss, game session state, knowledge availability, manual selection | Current, Session, Knowledge, Supported Games, Timeline summary | No | High | Normal user | P1 |
| Voice | Player | Voice Input, Local ASR, Voice Output, future direct conversation state | Conversation, Input, Output, Local ASR Setup, Voice Profile later | No, but visible | Very high | Normal user | P1 |
| Overlay | Player | Safe Mode status, overlay config, recent safe message preview, force close | Safe Mode, Placement, Content, Future Game Mode checklist | No | Very high | Normal user | P1 |
| Settings | Player | App-level preferences and safe setup | Model, Persona Mode, Proactive, Privacy, Local Data, Reset | No | Medium | Normal user | P2 |
| Developer / Debug | Developer / QA | Event Stream, Prompt Preview safe summary, Semantic Shadow trace, Knowledge trace, Runtime status | Events, Prompt Preview, Runtime, Knowledge, Semantic Shadow, Raw JSON safe view | No | Low | Developer | P1 for split |
| Future Presentation / Avatar | Future player-facing presentation | Avatar / Live2D placeholder and presentation policy | Presence, Avatar Policy, Future assets | No | Low to medium | Normal user later | P4 |

## Recommended Feature Placement

| Current / Future Feature | Recommended Home | Notes |
| --- | --- | --- |
| Main chat | Home / Chat | Keep central and stable. Panel switching must not discard input. |
| Pending memory confirmation | Memory | Keep visible to normal users; not Debug-only. |
| Confirmed memory list | Memory | Needed before richer candidate memory. |
| Hermes-style candidate memory | Memory | Needs UI first, then backend architecture. Do not hide under Debug. |
| Session Archive / Search | Memory or Game, depending on scope | User memories go to Memory; per-run gameplay summaries go to Game. |
| Current game / boss | Game | Also shown as compact status chips in Home. |
| Knowledge trace | Developer / Debug | Ordinary Game page can show knowledge availability, not raw trace. |
| Voice Input / Local ASR | Voice | Chat keeps quick mic button; setup belongs in Voice workspace. |
| Voice Output / Test Voice | Voice | Basic output toggle can be mirrored in Settings. |
| Direct voice conversation | Voice | Future Voice v2. Requires state model and interruption policy first. |
| Overlay Safe Mode | Overlay | Settings may keep a compact toggle, but detailed copy belongs in Overlay. |
| Event Stream | Developer / Debug | Not ordinary default surface. |
| Prompt Preview | Developer / Debug | Safe summary only. Never raw prompt or full persona. |
| Semantic Shadow trace | Developer / Debug | Candidate-only diagnostics, not state writer. |
| Persona Pack safe summary | Developer / Debug and Settings summary | Use safe metadata only. |
| Local Data controls | Settings | Destructive actions need confirmation and should not sit near normal chat. |
| Live2D / Avatar | Future Presentation / Avatar | Placeholder only until Voice / Overlay / Memory are stronger. |

## Recommended UI Surface Model

### Candidate Comparison

| Surface | Strengths | Risks | Current Fit |
| --- | --- | --- | --- |
| Right Drawer | Low implementation cost, close to current layout, good for secondary details | Can repeat current right-side overload if every feature becomes a drawer | Useful for compact details, not enough alone |
| Center Modal | Good for confirmation and short setup flows | Bad for long workflows, can block chat input | Use only for focused tasks and confirmations |
| Floating Panel | Flexible and game-like | Harder to test, can overlap input, can feel unstable in Electron | Use sparingly after shell exists |
| Workspace Overlay | Lets left launcher open full focused workspaces while preserving chat | Requires moderate React layout work | Best next step |
| Electron child window | True multi-window separation | Higher Electron complexity, packaging risk, focus bugs, harder QA | Avoid for ordinary panels for now |

### Recommendation

Use an in-app Workspace Shell first:

1. Keep Home / Chat as the default workspace.
2. Convert the left navigation from anchors into a workspace launcher.
3. Let each top-level module open a focused in-app workspace or panel layer.
4. Preserve the chat input state when switching workspaces.
5. Use a right drawer only for compact contextual details inside a workspace.
6. Use center modals only for confirmations, setup steps, and destructive actions.
7. Keep native Electron child windows only for the existing Overlay path and future tasks that truly require OS-level behavior.

This model has the best balance for ReiLink now: it is less invasive than native multi-window work, easier to test than floating panels, safer for packaged `.app`, and flexible enough for Voice, Memory, Overlay, and Debug split.

## Voice IA Position

Voice should become a first-class top-level module, while Home / Chat keeps a compact mic entry near the input.

Current state:

- Local ASR v1 is available when the user configures a local whisper-like binary, model, and optional converter.
- The current flow is record / transcribe / fill input / user confirms send.
- Voice Output uses renderer-side `speechSynthesis`.
- Voice Output has toggle, Test Voice, rate, and volume.
- Current Voice is not natural direct conversation.

Future Voice v2 direction:

- User can speak directly.
- Rei can listen, transcribe, answer, and speak back.
- User can choose auto-send or confirm-send.
- Rei reply can be spoken automatically when enabled.
- User can interrupt Rei.
- TTS and recording must not conflict.
- Game mode should prefer short, low-interruption spoken replies.
- Audio should not be uploaded.
- Unconfirmed transcript must not enter memory, prompt, knowledge retrieval, game context, or proactive.
- Debug, Prompt Preview, internal trace, raw prompt, and full transcript must not be spoken.

Recommended Voice states:

- `idle`
- `listening`
- `transcribing`
- `ready_to_send`
- `assistant_thinking`
- `speaking`
- `interrupted`
- `error`

Recommended Voice workspace tabs:

- Conversation: future direct voice loop state, listen/speak status, interruption state.
- Input: Local ASR status, record/transcribe controls, transcript confirmation boundary.
- Output: Voice Output toggle, Test Voice, rate, volume, system voice notes.
- Local ASR Setup: binary/model/converter configuration with privacy copy.
- Voice Profile later: voice personality and output strategy, after TTS strategy is chosen.

Do not implement Voice v2 in this IA task.

## Overlay IA Position

Overlay should be a top-level module for a game-safe companion surface. It should remain macOS safe mode for now.

Current boundaries:

- macOS auto-show is intentionally fail-closed.
- Main window stability has priority over overlay visibility.
- Settings can force-close Overlay.
- Overlay currently shows only safe short summaries.
- Overlay must not expose raw prompt, full reply, full user input, memory, Debug raw JSON, transcript, API key, `.env`, full paths, stdout, or stderr.

Future Overlay direction:

- Show the latest 1-2 safe companion lines.
- Show Voice state such as listening, transcribing, speaking, interrupted, or error.
- Show low-interruption hints during game play.
- Stay out of the way of Settings and main chat.
- Restore auto-show only in a dedicated Overlay task with packaged `.app` smoke.

Do not describe Overlay as a fully available game HUD yet. Do not restore auto-show in this IA task.

## Memory IA Position

Memory should be a normal user feature, not a Debug feature.

Current state:

- Pending memory confirmation exists.
- Accepted / ignored memory events exist.
- Local data status exists.

Recommended Memory workspace:

- Pending: candidate memories waiting for user confirmation.
- Confirmed: accepted long-term memories with source summaries.
- Ignored: ignored or do-not-ask-again items.
- Search: local search across confirmed memory and later session archive.
- Sources: where a memory came from, using safe summaries.
- Session Archive later: chat/game-session summaries that are not long-term memory.

Key boundaries:

- Candidate Memory implementation needs this UI position before backend expansion.
- Confirmed long-term memory and Game Session state must stay separate.
- Session Archive and Search should not be mixed directly into the main Chat surface.
- Memory should expose edit, delete, ignore, and do-not-ask-again as explicit user actions.
- Memory writes must keep the current confirmation boundary.

## Game IA Position

Game should be a normal user workspace for current play context, not only a Debug readout.

Recommended Game workspace:

- Current: detected/manual game, current boss, support status.
- Session: death/frustration counts, recent challenge, recent cleared state.
- Knowledge: supported games and knowledge availability without raw trace.
- Timeline: user-readable session events, not raw Event Stream.
- Manual Control: selected game override and clear actions.

Game should expose what Rei believes about the current play session without turning into a developer console.

## Developer / Debug IA Position

Developer / Debug should be opt-in and separated from ordinary experience.

Recommended Debug workspace:

- Event Stream: safe summaries only.
- Prompt Preview: safe assembled prompt summary only.
- Semantic Shadow trace: candidate-only diagnostics.
- Knowledge trace: retrieval status and safe snippet metadata.
- Persona Pack summary: id, version, sections, fallback and truncation summary.
- Runtime status: backend source, knowledge source, model routing, local data status.
- Raw JSON safe view: collapsed by default and still sanitized.

Developer / Debug must not show:

- Raw prompt.
- API key.
- `.env`.
- Complete local paths.
- stdout / stderr.
- Full persona markdown.
- Full assistant reply in Event Stream.
- Full user input or full ASR transcript.
- Raw provider response.

## Live2D / Avatar Position

Live2D / Avatar should be treated as a future presentation layer.

Current recommendation:

- Keep only a placeholder or future entry in IA.
- Do not make Avatar the main experience.
- Prioritize Voice, Overlay, Memory, and Debug separation first.
- Game players usually look at the game screen, so voice companionship is likely more useful than an always-visible character view.
- Add Live2D Presentation Policy before implementing Live2D v1.

## Recommended Next Task Order

Completed:

- UI Surface v0 - Panel Launcher & Workspace Shell.
  - Implemented as an in-app workspace shell.
  - Preserves chat input across workspace switches.
  - Avoids native Electron child-window complexity for ordinary modules.

Next:

1. Debug Split v1.
   - Move Event Stream, Prompt Preview, Semantic Shadow, Knowledge trace, Persona Pack summary, and runtime diagnostics into Developer / Debug.
   - Reduces ordinary-user clutter and lowers privacy risk.
2. Core UI Visual Polish v1.
   - Polish the new shell after the IA is real, not before.
   - Improve density, contrast, responsive behavior, and language consistency.
3. Voice Interaction v2 Spec.
   - Define direct conversation states, auto-send vs confirm-send, interruption, TTS/listening conflict, privacy, and Game Mode behavior.
   - Should use the Voice workspace created by step 1.
4. Hermes-style Memory Architecture v0.
   - Design candidate memory, source summaries, confirmed list, ignore/delete/do-not-ask-again, and session archive boundaries.
   - Depends on Memory workspace placement.
5. Candidate Memory v1.
   - Implement after the memory UI contract is clear.
   - Must keep user confirmation before writes.
6. Voice Interaction v2 Implementation.
   - Implement only after Voice spec and shell are ready.
   - Keep Local ASR no-upload and transcript safety boundaries.
7. Voice Profile v1 and TTS Strategy Spike.
   - Explore character voice quality and output strategy after direct conversation behavior is defined.
   - Do not commit to commercial TTS by default.
8. Overlay v1.2.
   - Add drag / lock / content state only after shell and Voice state are stable.
   - Restore macOS auto-show only as a separate, packaged-smoke-gated task.
9. Session Archive + Search v1.
   - Implement after Memory and Game boundaries are settled.
10. Persona / Memory Eval Runner v0.
   - Useful after Candidate Memory and persona regression surfaces are stable.
11. Live2D Presentation Policy.
   - Define role, safety, voice relationship, and game-mode constraints before assets or runtime.
12. Live2D v1.
   - Do not start until Voice, Overlay, Memory, and Debug split are stable.

Parallelizable work:

- Core UI visual exploration can run beside Debug Split after the shell direction is accepted.
- Voice Interaction v2 Spec can begin while the shell is implemented, but implementation should wait.
- Hermes-style Memory Architecture can be drafted in parallel with Debug Split, but Candidate Memory should wait for the Memory workspace.
- TTS Strategy Spike can run after Voice Spec has state language, without blocking Panel Shell.

Do not do now:

- Voice Interaction v2 implementation.
- Overlay auto-show restore.
- Native Electron child windows for normal panels.
- Hermes-style memory writes.
- Live2D v1.
- Large React component rewrite beyond the shell task.

## QA Coverage

Machine-readable IA scenarios live in `docs/qa/ui_ux_information_architecture_scenarios.json`. UI Surface implementation smoke scenarios live in `docs/qa/ui_surface_scenarios.json`.

Manual acceptance for IA and UI Surface v0:

1. Ordinary users should default to Home / Chat, not Debug.
2. Memory, Game, Voice, Overlay, Settings, and Developer should each have a clear top-level IA home.
3. Prompt Preview and Event Stream should live under Developer / Debug and remain safe summaries.
4. Overlay should remain documented as safe mode, not a complete game HUD.
5. Voice should be documented as a future direct conversation surface without implementing Voice v2.
6. Memory should be understandable to ordinary users and separate from Game Session state.
7. Live2D should remain a future presentation placeholder.
8. Panel Shell switching should not discard chat input.
9. Memory, Game, Voice, Overlay, Settings, Developer / Debug, and Future / Avatar should open as workspace panels and close with the close button or Escape.
