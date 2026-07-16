# ReiLink UI Architecture Audit v0

- Date: 2026-07-15
- Status: Architecture audit and redesign planning only
- Scope: `apps/desktop/src/renderer`
- Implementation changes: None

> Historical snapshot: this audit describes the renderer before Redesign Phase 1. For the implemented and frozen UI foundation built from baseline `c7867b8`, see `docs/design/reilink_ui_redesign_phase_v0.md`.

## 0. Audit Scope And Conclusion

This audit reviews the current Desktop Renderer structure before ReiLink UI Redesign v1. It does not propose changes to backend contracts, IPC behavior, Voice logic, memory logic, extraction, or runtime behavior.

The audit used the following as its design and product baseline:

- `AGENTS.md`
- `docs/design/reilink_ui_guidelines.md`
- `docs/ui_ux_information_architecture.md`
- `docs/PROJECT_STATUS.md`
- Existing frontend skills under `.agents/skills/`
- Current renderer code and tests

No source-of-truth conflict was found. The code still differs materially from the target visual direction, but that is an implementation gap rather than a documentation conflict. The current IA document already identifies Debug Split v1 and Core UI Visual Polish v1 as follow-up work.

### Executive Summary

1. The renderer is functionally mature but structurally monolithic. `App.tsx` is 9,401 lines and owns most UI state, API orchestration, subscriptions, event emission, and nearly all workspace markup.
2. The current in-app workspace shell is a useful migration scaffold. It preserves chat state while secondary workspaces open, but it is not yet a real Player Mode / Developer Mode boundary.
3. Voice, TTS, capture, transcript-quality, event, and timeline logic already have useful module boundaries. The redesign should wrap and preserve those modules rather than rewrite them.
4. The styling layer is best classified as **B. 半组件化（明显偏向页面级 CSS）**. Repeated classes exist, but there are no semantic design tokens, component primitives, CSS modules, or theme architecture.
5. The largest UI technical debt is not any single visual style. It is the combination of a stateful 9,000-line root component and a 1,900-line global stylesheet, which makes visual changes difficult to isolate from behavior.
6. The recommended path is **custom CSS variables and semantic design tokens, followed by incremental component extraction**. A full UI library or Tailwind migration is not recommended for Redesign v1.
7. The next implementation task should be a behavior-preserving **Shell Prototype v0**, with Player / Developer navigation separation, semantic tokens, and screenshot-driven review before feature workspaces are restyled.

## 1. Current Renderer Directory Structure

The current renderer is flat rather than organized by page, feature, or component ownership.

```text
apps/desktop/src/renderer/
├── App.tsx
├── OverlayApp.tsx
├── main.tsx
├── overlayRoute.ts
├── styles.css
├── audioCapture.ts
├── eventBus.ts
├── sessionTimeline.ts
├── ttsProviderRegistry.ts
├── ttsStrategy.ts
├── voiceInput.ts
├── voiceOutput.ts
├── voiceProfile.ts
├── voiceState.ts
├── voiceTranscriptQuality.ts
├── vite-env.d.ts
├── testSetup.ts
└── __tests__/
```

### Responsibility Map

| Area | Current files | Current responsibility | Assessment |
| --- | --- | --- | --- |
| Entry | `main.tsx`, `overlayRoute.ts` | Selects the main app or Overlay renderer from the URL and mounts React | Small and clear |
| Main application | `App.tsx` | Shell, navigation, workspaces, state, API calls, effects, user actions, event emission, most presentation | Primary structural bottleneck |
| Overlay surface | `OverlayApp.tsx` | Separate lightweight Overlay renderer and native runtime subscription | Good isolation; shares global CSS |
| Voice behavior | `audioCapture.ts`, `voiceInput.ts`, `voiceOutput.ts`, `voiceState.ts`, `voiceProfile.ts`, `voiceTranscriptQuality.ts` | Capture, recognition, playback, state derivation, output policy, transcript safeguards | Useful behavior seams to preserve |
| TTS behavior | `ttsStrategy.ts`, `ttsProviderRegistry.ts` | Strategy fallback and provider capability metadata | Useful behavior seam to preserve |
| Event and timeline behavior | `eventBus.ts`, `sessionTimeline.ts` | Safe interaction events and derived session timeline summaries | Useful behavior seam to preserve |
| Styling | `styles.css` | Base styles, shell, all workspaces, all controls, Overlay, responsive rules | Global and highly coupled |
| Tests | `__tests__/` | Root integration coverage plus focused tests for extracted behavior modules | Strong behavior safety net, but root test is also monolithic |

### Requested Structural Categories

| Category | Current state |
| --- | --- |
| `pages/` | Does not exist. All main user surfaces are conditional branches inside `App.tsx`. |
| `components/` | Does not exist. Only a few components are extracted within `App.tsx`: `TtsProviderSurface`, `EventStreamPanel`, `SessionTimelinePanel`, and `BooleanBadge`. |
| `hooks/` | Does not exist. Effects and controller subscriptions live directly in `App`. |
| `styles/` | Does not exist. One global `styles.css` owns both the main app and Overlay. |
| `state/` | Does not exist. Main state is local React state in `App`; behavior controllers hold their own module-level state. |
| `utils/` | Does not exist. Formatting, labels, sanitization helpers, and view-model functions are mixed into `App.tsx`; focused utilities live as top-level renderer modules. |

This flat structure was sufficient while capabilities were landing quickly. It is now the main obstacle to a controlled visual redesign.

## 2. Current Pages And Entry Points

The renderer does not use a client router. There are two renderer entry surfaces:

1. `main.tsx` renders `App` for the normal desktop window.
2. `main.tsx` renders `OverlayApp` when `overlayRoute.ts` detects the Overlay query or hash route.

Inside `App`, user-visible "pages" are state-driven workspaces. `activeWorkspace` selects one of:

```text
home | memory | game | voice | overlay | settings | debug | presentation
```

The chat surface remains mounted while a secondary workspace opens in the right panel. This is an important behavior contract because it preserves message history and the unsent draft.

### Workspace Inventory

| User-visible surface | Entry | Main implementation | Primary data sources |
| --- | --- | --- | --- |
| Home / Chat | Sidebar Chat item; default workspace | Chat header, notices, message list, composer, compact Voice state in `App.tsx` | `api.chat`, `api.checkProactive`, app settings, Voice modules, event bus, Overlay bridge |
| Memory | Sidebar Memory item; tabs for pending, confirmed, archive, local, future | Pending-memory decisions, long-term memories, archive search/detail/actions, local data status | Memory/profile/archive endpoints in `shared/api.ts`; runtime open-directory bridge |
| Game | Sidebar Game item; tabs for current, timeline, knowledge, manual | Current game/session facts, boss history, safe timeline, knowledge status, manual context | Game status/context/session endpoints, chat debug summary, semantic summary, session timeline |
| Voice | Sidebar Voice item; tabs for conversation, input, output, profile | Direct Conversation state, Local ASR setup/capture, TTS controls/provider surface, Voice Profile | Voice controller modules, audio capture, Local ASR APIs, settings, native file picker IPC |
| Overlay settings | Sidebar Overlay item; tabs for safe mode, placement, content, future | Overlay enable/force-off, position, opacity, safe content settings | App settings and `window.reilinkRuntime` Overlay bridge |
| Settings | Sidebar Settings item; tabs for app, provider, privacy, advanced | General preferences, provider/setup status, privacy/data actions, duplicated advanced Voice and Overlay controls | Settings/setup/runtime APIs, Local ASR APIs, runtime bridge |
| Developer / Debug | Sidebar Debug item; tabs for events, prompt, runtime, trace | Event Stream, Prompt Preview, runtime/provider facts, semantic and extraction traces | Event bus plus debug, prompt, provider, semantic, game-session, and runtime APIs |
| Future / Avatar | Sidebar Future item | Static future presentation placeholders | Local constants only |
| Native Overlay | Separate renderer route/window | `OverlayApp.tsx` avatar and recent safe message bubbles | `window.reilinkRuntime.getOverlayStatus` and `onOverlayState` |

### Page-level Findings

- Current display language mixes Chinese with engineering English: for example, `Home / Chat`, `Developer / Debug`, `Overlay`, and `Future / Avatar`. This conflicts with the intended player-facing terminology even though it accurately describes the current architecture.
- Settings still duplicates substantial Voice and Overlay configuration. The IA separation exists, but ownership is incomplete.
- Game is currently presented mostly as context/status. The redesign should frame the player-facing portion as **旅程**, while preserving deep session facts and extraction details for Developer Mode.
- Memory contains both companion-facing concepts and administrative data controls. Those need separate visual hierarchy, not necessarily separate backend APIs.
- Presentation / Avatar is a placeholder and should remain outside Redesign v1's critical path.

## 3. Current Shell Architecture

### Layout

The main shell is implemented directly in `App.tsx`:

```text
App
└── main.shell
    ├── aside.appSidebar
    │   ├── brand
    │   ├── workspace launcher
    │   └── companion/backend status
    └── section.appWorkspace
        ├── global companion header + status strip
        └── section.workspaceGrid
            ├── chatColumn (always mounted)
            └── workspacePanel (conditional)
                ├── fixed panel header
                ├── workspace tabs
                └── scrollable panel body
```

Desktop layout uses a fixed 164px sidebar and a chat-plus-panel grid. At widths below 960px, the right workspace moves below chat. At widths below 820px, the sidebar becomes a top section and eight navigation entries become a four-column icon grid.

### Navigation And Panel State

- There is no router and no URL state for normal workspaces.
- `activeWorkspace` controls whether the right panel is open.
- Workspace tab state is stored per workspace.
- Escape closes the secondary workspace.
- Chat and its draft stay mounted during workspace changes.
- The panel header and tabs are outside the scroll container, preserving the UI Surface v0.1 regression fix.

These are valuable contracts and should survive redesign even if the DOM structure changes.

### Player Mode / Developer Mode Fitness

The current shell is **suitable as a migration scaffold, but not as the final mode architecture**.

What already works:

- Chat is the default surface.
- Secondary capabilities open without discarding chat state.
- Developer content has a dedicated workspace rather than being fully stacked beside chat.
- The native Overlay remains isolated from ordinary panels.

What prevents a true mode split:

- Developer / Debug is still a peer in the primary player navigation.
- Provider, model, runtime, proactive, game, and boss diagnostics appear in the global status strip.
- Settings Advanced repeats Voice and Overlay implementation details.
- `debug_panel` changes panel visibility but does not establish a distinct navigation or information-density mode.
- Player and developer labels, cards, density, and status patterns all use the same presentation grammar.

### Recommended Split

Use one shared `AppShell`, not two independent applications:

- **Player Mode**: 聊天、旅程、回忆、声音、设置. Overlay may remain a contextual feature entry, depending on the Shell prototype.
- **Developer Mode**: Event Stream, Prompt Preview, extraction/knowledge trace, provider/runtime diagnostics, safe raw views.
- Developer Mode should be explicitly enabled from an advanced setting or developer affordance and should not occupy the default navigation.
- The mode boundary should control navigation and information visibility, while shared settings and state remain single-source.
- Do not duplicate chat state, backend subscriptions, or Voice controllers between modes.

The P0 shell work should establish this boundary. The detailed Developer workspace can still be visually redesigned later at P6.

### State Management And Data Flow

The renderer does not use Context, a reducer-based store, a query cache, or an external state library. `App.tsx` contains roughly 82 `useState` usages, 18 effects, 45 callbacks, and 22 refs. Most state therefore has global root lifetime even when only one workspace needs it.

Current state falls into four layers:

| State layer | Examples | Current owner |
| --- | --- | --- |
| Shell/UI state | Active workspace, per-workspace tabs, open folds, form drafts, busy/error messages | `App` local state |
| Backend snapshots | Settings, setup, memory, game, provider, prompt, semantic, proactive, archive data | `App` local state populated by `shared/api.ts` |
| Interaction state | Voice input/output, audio capture, events, TTS strategy status | Module-level controllers with subscriptions mirrored into `App` |
| Native runtime state | Backend process status, file selection, Overlay status/config/content | `window.reilinkRuntime` IPC bridge plus `App` effects |

```text
HTTP API snapshots ─┐
Electron IPC ───────┼──> App state/effects ──> all workspace JSX
Voice/event modules ┘           │
                                └──> mutations/events/refreshStatus
```

`refreshStatus` is the central synchronization path. It serially loads health, setup, settings, Local ASR, game, memory, debug, provider, proactive, semantic, prompt, and pending-memory data. A failure anywhere reaches one shared error path and marks the backend disconnected. Mutations commonly call the same broad refresh afterward.

This design keeps behavior discoverable in one file and avoids state-library complexity, but it has three redesign costs:

- Feature ownership is unclear, so moving a visual panel can accidentally move loading or side-effect behavior.
- Unrelated backend snapshots and subscriptions share the same render root and error surface.
- Polling, timers, refs, and workspace markup are interleaved, making extraction order important.

The redesign should first extract presentational props from this state. Feature hooks and narrower refresh boundaries can follow after behavior parity is proven; state restructuring should not be bundled into the Shell prototype.

## 4. Design System Status

### Current Foundations

| Design-system area | Current state | Finding |
| --- | --- | --- |
| Color tokens | Direct hex/RGBA values throughout `styles.css`; static scan finds roughly 80 distinct hex values | No semantic color system |
| Theme variables | No app theme variables; only runtime `--overlay-bg-opacity` is used | No light/dark theme architecture |
| Spacing | Repeated direct pixel values across padding, gaps, and sizes | Informal rhythm, no documented scale |
| Typography | Root font stack plus many direct font sizes and weights | No role-based type scale |
| Radius | Many direct values from small radii through pill/circle values | No controlled radius policy |
| Elevation | Repeated custom borders, shadows, blur, and translucent layers | No semantic surface/elevation levels |
| Component variants | Class combinations such as `smallButton quiet`, message role classes, status classes | Informal variants without typed components |
| Responsive behavior | Two global breakpoints at 960px and 820px | Functional but shell-specific and coarse |
| Icons | `lucide-react` is already installed and used | Good reusable dependency |

### Classification

**B. 半组件化（明显偏向页面级 CSS）**

Reasons:

- Reusable visual class patterns exist: `infoCard`, `smallButton`, `iconButton`, `settingRow`, `workspaceTab`, `statusDot`, `messageBubble`, and `debugFacts`.
- Those patterns are reused directly from JSX, so the styling is not completely ad hoc.
- There are no React primitives that own semantics, variants, accessibility defaults, or class composition.
- There are no CSS modules despite option A's generic wording; the current implementation is one global stylesheet.
- Feature-specific and primitive styles share the same global namespace and source file.
- The same styles serve both the main desktop window and the separate Overlay renderer.

### Visual Gap Against The Guideline

The current UI uses a dark blue/slate/purple glass-panel language with radial gradients, high card density, status chips, borders, and developer facts. It is polished enough for a technical prototype, but it still reads closer to an AI dashboard than a quiet fantasy journal.

The redesign needs to change the system, not only recolor it:

- Replace always-visible diagnostics with calm, contextual feedback.
- Use semantic surfaces and restrained elevation instead of stacking translucent cards.
- Reserve pills and badges for real statuses rather than general layout.
- Give conversation and Rei's presence more visual importance than runtime state.
- Introduce Chinese-first labels at the navigation and component-contract level.
- Support warm light and night-oriented dark themes through semantic tokens rather than duplicated CSS values.

## 5. Component Reuse Analysis

Static inspection shows repeated UI patterns: more than twenty direct `infoCard` uses, more than twenty `cardHeader` uses, dozens of small buttons, and many repeated setting rows. These are strong extraction candidates.

### Recommended `components/ui/` Primitives

| Current pattern | Future primitive | Responsibility |
| --- | --- | --- |
| `infoCard`, nested panel backgrounds | `Surface` | Semantic surface level, padding, border/elevation, optional section role |
| Companion- or journey-specific cards | `ReiCard` or `JourneyCard` | Domain presentation built on `Surface`; do not make every surface Rei-branded |
| `smallButton`, `sendButton` | `SoftButton` | Typed `primary`, `secondary`, `quiet`, `danger` variants and busy/disabled state |
| `iconButton` | `IconButton` | Stable icon dimensions, accessible label, tooltip contract |
| `workspaceTabs`, mode toggles | `Tabs` and `SegmentedControl` | Correct semantics, focus behavior, selected state, stable sizing |
| `statusDot`, `connection`, count pills | `StatusIndicator`, `StatusBadge` | Semantic status color and concise labels |
| `settingRow`, range/select rows | `FieldRow`, `SettingGroup` | Label, control, hint, error, and disabled layout |
| `foldHeader` and collapsible details | `Disclosure` | Accessible expansion state for advanced and developer detail |
| Empty paragraphs and placeholder cards | `EmptyState` | Calm, concise empty/error feedback |
| Inline destructive controls | `ConfirmDialog` | Future focused confirmation for destructive actions; no shared modal exists today |
| `debugFacts` | `DefinitionList` | Developer-only key/value display; should not become a player-facing primitive |

### Recommended Companion Components

| Current pattern | Future component | Notes |
| --- | --- | --- |
| `miniAvatar`, `companionAvatar`, Overlay avatar | `ReiAvatar` | Shared visual identity with explicit size/state variants |
| Header and compact Voice status | `ReiPresence` | Quiet state feedback for idle/listening/thinking/speaking |
| Assistant message bubble | `ReiMessage` | Companion-specific message treatment and optional pending/proactive state |
| User message bubble | `UserMessage` | Separate semantics and alignment from Rei messages |
| Composer Voice feedback | `VoiceStateIndicator` | State label and interruption/error feedback without decorative constant motion |

### Reuse Rules

- Put low-level visual and interaction contracts in `components/ui/`.
- Put identity-specific presentation in `components/rei/`.
- Put Game/Journey, Memory, Voice, and Developer concepts inside feature folders.
- Avoid a generic `Card` with many boolean props. Use a small `Surface` base and compose domain components.
- Do not extract a component only to shorten JSX; extract it when it owns a reusable semantic or behavior contract.
- Preserve accessible names and roles because the current tests rely heavily on semantic queries.

## 6. UI Redesign Priorities

The priorities below reflect player value, migration risk, and technical dependency. P6 refers to the full Developer surface redesign; hiding developer navigation and diagnostics from Player Mode starts in P0.

| Priority | Area | User value | Risk | Dependencies and rationale |
| --- | --- | --- | --- | --- |
| **P0** | App Shell / Layout | Very high | Medium | Establishes Player / Developer boundaries, navigation language, responsive geometry, and token usage. Every later screen depends on it. Preserve chat mounting, tab state, close, Escape, and Overlay separation. |
| **P1** | Chat UI | Highest | High | Chat is ReiLink's core experience and should define the visual language. Start with presentational extraction; keep send orchestration in the existing container until characterization tests protect Voice, Memory, TTS, Overlay, and event side effects. |
| **P2** | Voice UI | High | High | Voice has strong product value and reusable behavior modules, but capture, Direct Conversation, interruption, and TTS are timing-sensitive. Build views around existing controller snapshots; do not redesign the state machine during visual work. |
| **P3** | Journey / Game Context | High | Low to medium | Mostly read-oriented and a good place to express the fantasy-journal direction. Show player-readable journey state; move extraction and raw session detail to Developer Mode. Rename the player surface from engineering-oriented Game Context to 旅程. |
| **P4** | Memory | Medium to high | Medium | Important for trust and companionship. Separate 回忆, pending decisions, archives, and data administration visually while preserving explicit confirmation and deletion boundaries. |
| **P5** | Settings | Medium | Medium to high | Lower daily value, but high persistence risk. Reduce duplication only after Voice and Overlay components have stable reusable contracts. Keep ordinary preferences separate from advanced setup. |
| **P6** | Developer Mode | Low for players, high for QA | Medium | Full visual redesign comes after the player shell. Keep diagnostics complete and privacy-safe, but place them behind explicit mode entry. Do not delete diagnostic capabilities merely to simplify the player UI. |

### Parallel Lanes

- **Overlay** should remain a separate preservation lane. Shared tokens may be adopted later, but native lifecycle, safe-content limits, and macOS fail-closed behavior should not be folded into ordinary shell work.
- **Future / Avatar** stays outside the Redesign v1 critical path. Rei presence can improve through avatar and state components without adding Live2D or a character showcase.
- **Debug Split** begins architecturally at P0 even though detailed Developer polish is P6.

## 7. Technical Approach Comparison

### Option A: Continue Existing CSS / CSS Modules

The current code does not use CSS modules; this option effectively means continuing the single global stylesheet or beginning isolated modules without a token foundation.

**Advantages**

- Lowest immediate migration cost.
- No dependency or build changes.
- Existing selectors and tests remain stable.

**Disadvantages**

- Direct values and global selectors continue to spread.
- Light/dark themes remain expensive.
- Repeated JSX class combinations continue to substitute for component APIs.
- Overlay and main-window styles remain vulnerable to unintended cross-effects.

**Verdict:** Useful only as a temporary compatibility layer during migration, not as the redesign architecture.

### Option B: CSS Variables + Custom Design Tokens

Introduce global semantic tokens and build small typed React primitives around them. Existing CSS can consume tokens gradually; feature styles can move into scoped files or CSS modules as components are extracted.

**Advantages**

- Best fit for ReiLink's highly customized visual identity.
- No runtime dependency and negligible Electron cost.
- Supports warm light and night dark themes through the same semantic API.
- Enables incremental migration without rewriting all markup.
- Keeps product language and accessibility contracts inside owned components.

**Disadvantages**

- Requires discipline and a documented token vocabulary.
- Does not provide complex accessible primitives automatically.
- A partial migration can temporarily contain old and new style systems.

**Verdict:** **Recommended foundation.**

### Option C: Introduce A UI Component Library

A complete visual library would provide controls quickly, but its defaults would need substantial restyling to avoid a generic SaaS/dashboard result.

**Advantages**

- Mature accessibility and interaction behavior for complex controls.
- Faster implementation of dialogs, menus, and form primitives.

**Disadvantages**

- Visual defaults conflict with ReiLink's custom companion identity.
- Adds dependency, bundle, and theming surface to a currently small React app.
- Risks replacing one large styling layer with library override CSS.

**Verdict:** Do not adopt a full visual library for Redesign v1. Selective headless primitives may be considered later for dialogs or menus if accessibility complexity justifies them.

### Option D: Tailwind + Component Primitives

**Advantages**

- Fast local styling and a shared utility vocabulary.
- Good ecosystem for headless components.

**Disadvantages**

- Requires a broad rewrite of a 9,401-line JSX surface.
- Creates large class diffs before component ownership is fixed.
- Does not solve state, API, or workspace coupling.
- Adds a second design vocabulary during migration and can encourage page-local styling.

**Verdict:** Not recommended for the current redesign. Reconsider only after component boundaries are stable and a concrete utility-first need appears.

### Recommended Stack

Use **Option B**, with the following shape:

```text
styles/
├── tokens.css       # semantic color, spacing, radius, type, elevation, motion
├── themes.css       # warm light and night dark token values
├── base.css         # reset, body, focus, typography defaults
└── utilities.css    # only a very small set of layout/accessibility utilities
```

Then use component-scoped CSS or CSS modules for `components/ui/` and feature views. Keep the old `styles.css` during migration and shrink it feature by feature rather than replacing it in one commit.

Recommended token categories:

- Semantic colors: canvas, surface, raised surface, text, muted text, accent, highlight, success, warning, danger, focus.
- Spacing: a small consistent scale rather than arbitrary per-page values.
- Typography: conversation, body, label, caption, section heading, workspace title.
- Radius: restrained surface radii, with circles reserved for avatars and status dots.
- Elevation: flat, raised, overlay; avoid stacking cards inside cards.
- Motion: short fade/transition durations and reduced-motion behavior.
- Layout: sidebar width, readable chat width, panel width, composer height, responsive thresholds.

### State And Data Recommendation

- Do not add Redux, Zustand, or a server-state library only for the redesign.
- Keep feature-local UI state close to each feature.
- Extract API loading and mutation orchestration into feature hooks or controllers after presentational components are stable.
- Wrap existing singleton subscriptions (`voiceInput`, `voiceOutput`, `audioCapture`, `eventBus`) in focused hooks; preserve the singleton implementations.
- Use a reducer only where multiple UI fields form one transition model, such as workspace navigation or a settings form.
- Avoid a single global Context containing all current `App` state; that would move the monolith rather than remove it.
- Keep normal workspace navigation state-based for now. A router is not required unless deep-linking becomes a product requirement.

## 8. Redesign Risk Analysis

### Risk Matrix

| Area | Risk | Why | Required protection |
| --- | --- | --- | --- |
| Chat send flow | High | One function coordinates Voice stop, input source, event emission, placeholder timing, segmented replies, TTS, Overlay, Memory notices, refresh, and errors | Characterization tests; extract visual children before orchestration |
| Voice capture and Direct Conversation | High | MediaRecorder timing, deferred stop, transcript guards, auto-send, interruption, and playback are state-sensitive | Preserve controller modules and state labels; targeted Voice tests |
| Settings persistence | High | UI updates normalize settings, update refs, change Debug visibility, emit events, and refresh backend state | Keep mutation adapter stable; test save, fallback, and busy/error states |
| Backend communication | Medium to high | `refreshStatus` currently serially loads many endpoints and populates shared state | Do not alter endpoints during visual work; split reads only with equivalent error semantics |
| IPC / Overlay | High | Native runtime status, file picker, Overlay lifecycle, and separate renderer depend on Electron bridge contracts | Preserve `window.reilinkRuntime`; packaged smoke for later implementation |
| Event Stream and Prompt Preview | High privacy impact | Safe metadata and omitted raw content are explicit product guarantees | Reuse sanitizers and event types; never render hidden raw payloads |
| Memory actions | Medium to high | Accept, ignore, delete, reset, archive, and candidate scans have durable effects | Preserve confirmation and busy states; mutation tests before layout changes |
| Workspace shell | Medium | Draft preservation, focus, panel tabs, scrolling, Escape, and responsive stacking are regression-sensitive | Keep existing behavior tests and add focused shell tests |
| Global CSS | High visual blast radius | Main app and Overlay share one stylesheet and broad selectors | Introduce tokens first; migrate in bounded component slices |
| Renderer tests | Medium | `App.test.tsx` is 7,282 lines and exercises most behavior through root renders | Preserve roles/labels; add focused component tests as ownership moves |

### Safe To Replace First

The following are primarily presentational and can be replaced if their accessible names, callbacks, and state props remain stable:

- Sidebar and workspace navigation visuals.
- Header composition and player-facing status presentation.
- Workspace panel frame, tabs, and scroll container.
- Card/surface wrappers and section headings.
- Button, icon-button, badge, field-row, and empty-state presentation.
- Message bubble markup after message data and send orchestration remain in the parent.
- Static Future / Avatar placeholders.
- Avatar visuals and passive presence indicators.

### Requires Caution

Do not combine these changes with initial visual extraction:

- `submitChatMessage` and its TTS, Overlay, Memory, Voice, and event side effects.
- `refreshStatus` and backend connectivity/error semantics.
- Voice controller, capture, transcript-quality, and TTS strategy implementations.
- App settings normalization and persistence.
- `window.reilinkRuntime` IPC calls and Overlay subscriptions.
- Event Stream privacy summaries and Prompt Preview omission rules.
- Memory/archive destructive actions.
- Semantic extraction or game-state derivation.

### Future Verification Strategy

For implementation phases, use four layers:

1. Existing renderer unit/integration tests as behavior characterization.
2. Focused component and hook tests for newly extracted ownership.
3. Screenshot-driven desktop and narrow-width visual review for every redesigned surface.
4. Packaged `.app` smoke whenever Electron main process, IPC, Overlay, native file selection, or packaged behavior is touched.

## 9. Proposed Future Component Tree

This is a target direction, not a required one-commit move.

```text
apps/desktop/src/renderer/
├── app/
│   ├── App.tsx
│   ├── AppShell.tsx
│   ├── PlayerNavigation.tsx
│   ├── DeveloperNavigation.tsx
│   ├── WorkspacePanel.tsx
│   ├── navigation.ts
│   └── useWorkspaceNavigation.ts
├── components/
│   ├── ui/
│   │   ├── Surface.tsx
│   │   ├── SoftButton.tsx
│   │   ├── IconButton.tsx
│   │   ├── Tabs.tsx
│   │   ├── SegmentedControl.tsx
│   │   ├── StatusIndicator.tsx
│   │   ├── FieldRow.tsx
│   │   ├── Disclosure.tsx
│   │   ├── EmptyState.tsx
│   │   └── ConfirmDialog.tsx
│   └── rei/
│       ├── ReiAvatar.tsx
│       ├── ReiPresence.tsx
│       ├── ReiMessage.tsx
│       └── UserMessage.tsx
├── features/
│   ├── chat/
│   │   ├── ChatWorkspace.tsx
│   │   ├── MessageList.tsx
│   │   ├── ChatComposer.tsx
│   │   ├── ChatNotices.tsx
│   │   └── useChatController.ts
│   ├── journey/
│   │   ├── JourneyWorkspace.tsx
│   │   ├── CurrentJourney.tsx
│   │   ├── JourneyTimeline.tsx
│   │   └── GameContextControl.tsx
│   ├── memory/
│   │   ├── MemoryWorkspace.tsx
│   │   ├── PendingMemories.tsx
│   │   ├── ConfirmedMemories.tsx
│   │   └── SessionArchive.tsx
│   ├── voice/
│   │   ├── VoiceWorkspace.tsx
│   │   ├── VoiceConversation.tsx
│   │   ├── VoiceInputSettings.tsx
│   │   ├── VoiceOutputSettings.tsx
│   │   ├── VoiceProfileSettings.tsx
│   │   └── useVoiceStatus.ts
│   ├── settings/
│   │   ├── SettingsWorkspace.tsx
│   │   ├── PlayerSettings.tsx
│   │   └── AdvancedSettings.tsx
│   ├── developer/
│   │   ├── DeveloperWorkspace.tsx
│   │   ├── EventStreamPanel.tsx
│   │   ├── PromptPreviewPanel.tsx
│   │   ├── RuntimePanel.tsx
│   │   └── ExtractionTracePanel.tsx
│   └── overlay/
│       ├── OverlaySettingsWorkspace.tsx
│       └── OverlayApp.tsx
├── hooks/
│   ├── useAppSettings.ts
│   ├── useBackendStatus.ts
│   └── useRuntimeBridge.ts
├── state/
│   └── workspaceReducer.ts
├── styles/
│   ├── tokens.css
│   ├── themes.css
│   ├── base.css
│   └── utilities.css
├── audioCapture.ts
├── eventBus.ts
├── sessionTimeline.ts
├── ttsProviderRegistry.ts
├── ttsStrategy.ts
├── voiceInput.ts
├── voiceOutput.ts
├── voiceProfile.ts
├── voiceState.ts
└── voiceTranscriptQuality.ts
```

### Tree Principles

- `app/` composes navigation and feature workspaces; it should not own feature-specific rendering.
- `components/ui/` stays domain-neutral and small.
- `components/rei/` expresses companion identity.
- `features/` owns product language, feature views, and feature-level adapters.
- Existing behavior modules can remain at their current paths initially; moving files is lower priority than establishing ownership.
- `OverlayApp` remains a separate renderer surface even if its source moves under `features/overlay/`.
- A decorative Voice orb is not required. A calm state indicator and explicit record/stop controls better match ReiLink's low-pressure interaction goal.

## 10. Recommended Redesign Route

### Phase 0: Contract Freeze

- Record current shell, chat, settings, Voice, and Developer behavior scenarios.
- Identify accessible labels and roles that tests and users depend on.
- Capture baseline screenshots for desktop and narrow layouts without committing them unless explicitly requested.
- Treat Voice, IPC, privacy, and persistence behavior as frozen during shell work.

### Phase 1: Shell Prototype v0

- Introduce semantic tokens and one representative theme direction.
- Build `AppShell`, navigation groups, workspace panel, and shared surface/button/tab primitives.
- Default to Player Mode and hide Developer navigation until explicitly enabled.
- Keep chat mounted and preserve draft, panel tab, close, Escape, and responsive behavior.
- Remove provider/runtime diagnostics from the default player header; retain concise availability/error feedback.
- Validate at common Electron desktop sizes and the current narrow breakpoint.

The prototype should use real current state and callbacks where practical, but it must not move chat, Voice, settings, or IPC orchestration yet. Its purpose is to approve hierarchy, density, language, and responsive behavior.

### Phase 2: Chat Presentation

- Extract message list, Rei/user messages, notices, and composer.
- Keep `submitChatMessage` in the existing behavior container.
- Establish the final conversation typography, readable width, presence treatment, and error hierarchy.

### Phase 3: Voice And Journey

- Wrap existing Voice controller state in focused hooks and views.
- Build Voice UI around explicit states and interruption controls, without changing state-machine rules.
- Reframe player-facing Game Context as 旅程 and move diagnostic detail to Developer Mode.

### Phase 4: Memory And Settings

- Separate companion-facing memories from archive/data administration.
- Reuse Voice and Overlay feature components rather than duplicating their settings markup.
- Keep advanced provider/runtime setup outside ordinary player flow.

### Phase 5: Developer Consolidation

- Move all remaining engineering surfaces behind Developer Mode.
- Preserve Event Stream, Prompt Preview, runtime, provider, knowledge, and extraction diagnostics.
- Keep safe summaries and privacy omissions exactly intact.

## 11. Shell Prototype Acceptance Gates

The next Shell prototype is recommended only if it satisfies these gates:

- Default first view reads as a calm companion conversation, not a dashboard.
- Primary player navigation uses Chinese-first terms: 聊天、旅程、回忆、声音、设置.
- Developer tools are not present in default player navigation.
- Chat history and unsent input survive workspace switching.
- Workspace header, tabs, close button, and body scrolling preserve current regressions.
- Voice availability and backend errors remain understandable without exposing implementation details.
- No runtime, API, IPC, Voice, Memory, extraction, or settings-persistence behavior changes.
- Desktop and narrow screenshots show no overlap, clipped text, or unusable controls.
- Automated renderer tests remain green; visual smoke is additional, not a replacement.

## 12. Final Recommendation

Proceed with a **Shell Prototype v0** next.

The prototype should be narrow: semantic tokens, shared primitives, Player / Developer navigation separation, and the shell/chat frame. Do not begin by restyling every existing card or by moving all state out of `App.tsx`. Once the shell direction is accepted, extract feature presentation in the P1-P6 order while preserving the existing behavior modules and integration contracts.

The target architecture is not a larger framework. It is a smaller, clearer React composition where ReiLink's calm companion identity is expressed through shared tokens and components, and where high-risk behavior remains independently testable.
