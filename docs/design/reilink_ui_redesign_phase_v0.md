# ReiLink UI Redesign Phase v0

- Date: 2026-07-16
- Status: Consolidation v0 design-system contract, frozen for incremental reuse
- Phase 1 input baseline: `c7867b88a302b3d70bc1626598fa34c2fe0378d8`
- Scope: Desktop renderer visual system, shell, and the redesigned Home, Chat, Journey, and Voice experiences

## 0. Purpose And Source Of Truth

This document is the implementation contract for ReiLink's first UI Redesign phase. It records what is present in the renderer after the Shell Foundation, Chat, Journey, Voice, and Home work, so later pages can extend one coherent system instead of creating a second one.

Use these sources together:

1. `AGENTS.md` for product, safety, verification, and Git boundaries.
2. `docs/design/reilink_ui_guidelines.md` for the durable product and visual direction.
3. This document for the current implemented design-system contract.
4. Renderer code and Git history when implementation details change.

`docs/design/ui_architecture_audit_v0.md` remains useful as a pre-redesign architecture snapshot. Its statements that tokens, themes, and component folders do not exist are historical; the implemented foundation described here supersedes those specific findings. The audit's cautions around `App.tsx`, legacy CSS, IPC, Voice, Memory, and persistence remain valid.

## 1. Product Design Position

ReiLink is a **Cozy Fantasy Companion Interface**: a quiet personal space that accompanies a player's game journey without competing with the game or demanding attention.

The core qualities are:

- **Calm**: low information pressure, gentle hierarchy, and no urgent visual rhythm by default.
- **Personal**: the interface frames facts as the user's journey, conversation, and remembered moments.
- **Quiet companion**: Rei is present through restrained copy, an avatar, and state feedback, but is not a mascot or visual centerpiece.
- **Soft fantasy**: journal-like typography, warm paper and night colors, fine lines, and small gold details suggest a travel diary rather than a fantasy HUD.
- **Minimal but refined**: few layers, deliberate spacing, and subtle detail are preferred over dense cards and decoration.

The interface must not drift toward:

- dashboard UI or a grid of status widgets;
- SaaS administration patterns as the main player experience;
- cyberpunk or neon AI styling;
- game HUD styling, meters, or achievement-driven decoration;
- a generic chatbot, customer-service console, or game guide site.

## 2. Experience Map

```text
Home
└── Returning Space

Chat
└── Conversation Surface

Journey
└── Personal Journey Log

Voice
└── Listening Space

Settings
└── Legacy / pending redesign

Developer Console
└── Developer-oriented surface

Overlay
└── Pending redesign
```

| Surface | Current responsibility | Boundary |
| --- | --- | --- |
| **Home / Returning Space** | Default returning view. Gives Rei a quiet presence, summarizes the current journey from existing safe data, shows at most one recent fragment, and offers restrained routes into Chat, Voice, and Journey. | It does not create journey data, invent missing locations, or become a feature dashboard. `HomeExperience` receives a presentation model built from existing Game Context, Game Session, archive, and timeline snapshots. |
| **Chat / Conversation Surface** | Primary text conversation with Rei. Owns message hierarchy, Rei/user presentation, empty conversation, composer, and the visual Voice entry. | It does not own LLM, streaming, Memory, TTS, ASR, or send orchestration. Those callbacks and state remain in `App.tsx` and existing controllers. |
| **Journey / Personal Journey Log** | Player-facing framing of the current game, current challenge, recent footsteps, journey timeline, available reference, and existing game selection controls. | It consumes current Game Context and Session Timeline fields. It must not expose extraction, canonical, schema, provider, or guard vocabulary, and must not change those data models. |
| **Voice / Listening Space** | Visual representation of listening, transcription, confirmation, thinking, speaking, interruption, and errors. Includes Voice mode choice, calm VoiceOrb presence, editable transcript draft, and record/send/stop controls. | It maps existing state to player-facing copy only. Audio capture, ASR, TTS, Direct Conversation guard, thresholds, and the Voice state machine stay unchanged. |
| **Settings** | Existing preferences, provider setup, privacy/local data, and advanced controls. | Visual redesign is pending. Settings persistence and normalization are not part of the frozen redesigned surface and must remain behavior-compatible. |
| **Developer Console** | Event Stream, Prompt Preview, runtime/provider facts, extraction and knowledge traces, and future diagnostic surfaces. | It is intentionally developer-oriented, collapsed behind **开发者工具** in ordinary navigation, and must preserve privacy-safe summaries. It is not a visual reference for player pages. |
| **Overlay** | Existing separate Electron renderer and its configuration entry. | Visual redesign is pending. Native lifecycle, IPC, safe content, and settings remain isolated from the ordinary shell. |

### Shell Contract

`AppShell` composes one sidebar, one companion header, and the active content area. The normal workspace does not use a router; `WorkspaceId` state remains the navigation contract.

- Home is the default workspace.
- Chat remains mounted while secondary workspaces open, preserving history and the unsent draft.
- Home hides the Chat surface visually without destroying its state.
- Secondary workspaces use the shared panel frame and close to Chat.
- Escape closes an open secondary workspace.
- The native Overlay remains a separate renderer route.

These are behavior contracts, not styling conveniences.

## 3. Design Token Contract

### 3.1 Ownership And Load Order

The token system is intentionally custom CSS with no UI framework:

```text
styles/tokens.css
→ styles/themes.css
→ styles.css
→ styles/base.css
→ components/ui/ui.css
→ components/rei/rei.css
→ app/shell.css
→ components/chat/chat.css
→ components/journey/journey.css
→ components/voice/voice.css
→ components/home/home.css
```

This is the current import order in `main.tsx`. `styles.css` remains early as the legacy compatibility layer; later shell and feature files override migrated selectors. New redesigned components must consume semantic tokens and live in their owner file. Do not create a parallel page-specific palette. Direct numeric values are acceptable for geometry that has no reusable semantic meaning, but repeated design decisions belong in tokens.

### 3.2 Colors

Colors are semantic. Component CSS should refer to the token name, not to the palette nickname or a literal hex value.

#### Light — Morning Paper / Journey Journal

| Role | Token | Value | Intent |
| --- | --- | --- | --- |
| Warm ivory canvas | `--color-canvas` | `#f5efe6` | Main window background |
| Soft canvas | `--color-canvas-soft` | `#f1e8dc` | Quiet background variation |
| Latte sidebar | `--color-sidebar` | `#eee2d3` | Navigation plane |
| Base surface | `--color-surface` | `#faf5ed` | Main content surfaces |
| Raised surface | `--color-surface-raised` | `#fffaf3` | Cards, inputs, composers |
| Soft surface | `--color-surface-soft` | `#eadfda` | Low-emphasis fills |
| Muted surface | `--color-surface-muted` | `#e7d8c8` | Selected or secondary areas |
| Soft brown text | `--color-text` | `#4a3b32` | Body text |
| Strong text | `--color-text-strong` | `#342821` | Titles and primary labels |
| Muted text | `--color-text-muted` | `#76675d` | Supporting copy |
| Subtle text | `--color-text-subtle` | `#97877b` | Captions and timestamps |
| Muted purple | `--color-accent` | `#a98fb8` | Calm accent |
| Strong accent | `--color-accent-strong` | `#765f8d` | Primary action and selected text |
| Soft accent | `--color-accent-soft` | `#e8deea` | Selected/hover fill |
| Warm gold | `--color-highlight` | `#c9a45c` | Journey lines and small details |

#### Dark — Coffee Night / Deep Plum

| Role | Token | Value | Intent |
| --- | --- | --- | --- |
| Coffee black canvas | `--color-canvas` | `#211b18` | Main night background; never pure black |
| Soft canvas | `--color-canvas-soft` | `#251e21` | Quiet night variation |
| Night sidebar | `--color-sidebar` | `#241e22` | Navigation plane |
| Deep plum surface | `--color-surface` | `#28202f` | Main content surfaces |
| Raised plum | `--color-surface-raised` | `#302739` | Cards, inputs, composers |
| Soft plum | `--color-surface-soft` | `#352b3d` | Low-emphasis fills |
| Muted plum | `--color-surface-muted` | `#3a303e` | Selected or secondary areas |
| Warm text | `--color-text` | `#eee4d8` | Body text |
| Strong warm text | `--color-text-strong` | `#fff6ea` | Titles and primary labels |
| Muted warm text | `--color-text-muted` | `#b9aa9e` | Supporting copy |
| Subtle warm text | `--color-text-subtle` | `#91837b` | Captions and timestamps |
| Soft lavender | `--color-accent` | `#b69bc7` | Calm night accent |
| Strong lavender | `--color-accent-strong` | `#ccb1dc` | Selected text and actions |
| Translucent lavender | `--color-accent-soft` | `rgba(182, 155, 199, 0.18)` | Selected/hover fill |
| Warm light | `--color-highlight` | `#d2aa5c` | Journey lines and small details |

Both themes also define semantic border, focus, scrollbar, success, warning, and danger tokens with matching soft variants. `--color-text-on-accent` keeps emphasized button copy legible, while `--color-sheen` supplies the small neutral highlight used by the shell and ReiAvatar. Use status colors only for actual status meaning, not decoration.

#### Status And Utility Values

| Token | Light | Dark |
| --- | --- | --- |
| `--color-border` | `rgba(92, 69, 51, 0.14)` | `rgba(239, 225, 210, 0.12)` |
| `--color-border-strong` | `rgba(92, 69, 51, 0.22)` | `rgba(239, 225, 210, 0.2)` |
| `--color-highlight-soft` | `rgba(201, 164, 92, 0.16)` | `rgba(210, 170, 92, 0.14)` |
| `--color-success` | `#5d9b67` | `#75ba82` |
| `--color-success-soft` | `rgba(93, 155, 103, 0.14)` | `rgba(117, 186, 130, 0.15)` |
| `--color-warning` | `#aa7a39` | `#d0a460` |
| `--color-warning-soft` | `rgba(170, 122, 57, 0.14)` | `rgba(208, 164, 96, 0.14)` |
| `--color-danger` | `#b96565` | `#d48282` |
| `--color-danger-soft` | `rgba(185, 101, 101, 0.13)` | `rgba(212, 130, 130, 0.14)` |
| `--color-focus` | `rgba(118, 95, 141, 0.38)` | `rgba(204, 177, 220, 0.4)` |
| `--color-scrollbar` | `rgba(92, 69, 51, 0.2)` | `rgba(239, 225, 210, 0.18)` |
| `--color-text-on-accent` | `#fffaf6` | `#fffaf6` |
| `--color-sheen` | `#ffffff` | `#ffffff` |

### 3.3 Typography

| Role | Token | Current value | Usage |
| --- | --- | --- | --- |
| UI/body family | `--font-family-ui` | Inter, Chinese system sans, system fallback | Controls, body copy, labels |
| Display family | `--font-family-display` | Iowan Old Style, Songti SC, STSong, Georgia | Companion, page, and journal-like headings |
| Caption | `--font-size-caption` | `0.72rem` | Time, quiet metadata, hints |
| Label/state | `--font-size-label` | `0.78rem` | Buttons, compact status, control labels |
| Body | `--font-size-body` | `0.9rem` | Default paragraphs and controls |
| Conversation | `--font-size-conversation` | `0.96rem` | Chat messages and natural-language content |
| Section heading | `--font-size-section` | `1.05rem` | Small section titles |
| Workspace title | `--font-size-title` | `clamp(1.75rem, 2.2vw, 2.2rem)` | Main companion/workspace heading |
| Tight line height | `--line-height-tight` | `1.2` | Short titles |
| Body line height | `--line-height-body` | `1.55` | General reading |
| Conversation line height | `--line-height-conversation` | `1.7` | Calm dialogue rhythm |

Headings use the display family selectively. Developer facts, long settings labels, and ordinary controls remain in the UI family. Do not use display typography as decoration on every label.

### 3.4 Spacing And Layout

The shared spacing scale is:

| Token | Value | Token | Value |
| --- | --- | --- | --- |
| `--space-1` | `0.25rem` | `--space-6` | `1.5rem` |
| `--space-2` | `0.5rem` | `--space-7` | `2rem` |
| `--space-3` | `0.75rem` | `--space-8` | `2.5rem` |
| `--space-4` | `1rem` | `--space-9` | `3rem` |
| `--space-5` | `1.25rem` |  |  |

Current layout contracts:

- Shell page gutter: `--layout-shell-gutter: clamp(1rem, 2.2vw, 2rem)`.
- Sidebar: `--layout-sidebar-width: 232px`, reducing to `208px` at the existing intermediate breakpoint.
- Readable Chat width: `--layout-chat-readable-width: 760px`.
- Secondary panel minimum: `--layout-panel-min-width: 360px`.
- Shell content gap: normally `--space-5`.
- Workspace panel padding: `--space-4`; panel section gaps generally use `--space-3` through `--space-5`.
- Home page padding: `--space-4`, with larger vertical breathing room at narrower stacked layouts.
- Card padding: choose `--space-4` for compact cards and `--space-5`/`--space-6` for primary content; do not introduce a new one-off scale for every page.

There is no separate page-padding or card-padding token at this baseline; these roles intentionally use the shared spacing scale. Whitespace is part of the companion tone. Compress spacing only for genuinely dense developer information.

### 3.5 Radius

| Token | Value | Use |
| --- | --- | --- |
| `--radius-xs` | `0.5rem` | Small compact details |
| `--radius-sm` | `0.75rem` | Compact controls and user message shape |
| `--radius-md` | `1rem` | Buttons, inputs, ordinary controls |
| `--radius-lg` | `1.25rem` | Cards and composers |
| `--radius-xl` | `1.5rem` | Major surfaces and workspace panels |
| `--radius-round` | `999px` | Avatars, status dots, and truly circular/pill controls only |

Rounded corners should soften the interface, not turn every label into a pill.

### 3.6 Shadow And Depth

| Level | Light | Dark | Use |
| --- | --- | --- | --- |
| `--shadow-surface` | `0 18px 44px rgba(82, 61, 44, 0.08)` | `0 18px 48px rgba(9, 7, 8, 0.18)` | Ordinary raised surfaces |
| `--shadow-raised` | `0 22px 54px rgba(82, 61, 44, 0.12)` | `0 24px 62px rgba(9, 7, 8, 0.28)` | Primary cards and composers |
| `--shadow-overlay` | `0 30px 80px rgba(82, 61, 44, 0.17)` | `0 34px 90px rgba(9, 7, 8, 0.4)` | Overlay-level UI surfaces, not ordinary card stacks |

Dark mode uses depth rather than brighter borders. Avoid stacking multiple elevated cards inside one another.

## 4. Theme Contract

`useTheme` owns the renderer theme mode:

- modes: `light | dark`;
- default: Light when no valid stored value exists;
- persistence key: `reilink-ui-theme` in `localStorage`;
- application: `data-theme` is set on `document.documentElement` and on `AppShell`;
- theme values: only `styles/themes.css` defines palette and theme shadow values;
- failure behavior: storage failures keep the in-memory theme usable.

Theme switching must not change component structure, product copy, or behavior. New components must be checked in both themes and must not assume a black Dark canvas or a white Light surface.

## 5. Component Contract

### 5.1 Foundation Components

| Component | Use | Do not use |
| --- | --- | --- |
| `Surface` | Establish semantic canvas, base, raised, or overlay level and an appropriate HTML element. | Do not use it solely to add a class or to create unnecessary nested layers. |
| `Card` | A small, cohesive group that needs a raised surface, border, radius, and calm shadow. | Do not wrap every paragraph, list row, action, or already-contained section in a Card. |
| `Button` | Shared primary, secondary, quiet, ghost, and danger hierarchy with stable sizing and disabled behavior. | Do not create feature-specific colors or use `primary` for multiple competing actions. Icon-only buttons still require an accessible label. |
| `Input` | Single-line text input with shared focus, typography, surface, and radius treatment. | Do not use it for multiline text; native `textarea` remains feature-owned until a real shared contract exists. |
| `StatusIndicator` | Concise neutral/success/warning/danger/active state with a dot and readable label. | Do not use it as decoration or expose raw engineering states in player surfaces. |
| `ReiAvatar` | Small identity and state presence in `idle`, `listening`, `thinking`, or `speaking`, with small/medium/large sizes. | Do not make it a full-screen illustration, page background, substitute for status copy, or fixed external-IP character image. |

### 5.2 Feature Components

- **Home**: `HomeExperience`, `HomeHero`, `CurrentJourneyCard`, `RecentJourneyFragment`, and `HomeQuickActions` own the Returning Space composition.
- **Chat**: `ChatMessage`, `ChatComposer`, and `EmptyConversation` own conversation presentation while callbacks remain external.
- **Journey**: `JourneyOverview`, `JourneyCard`, `CurrentChallenge`, `JourneyTimeline`, `JourneyReference`, `JourneyGameSelector`, and `EmptyJourney` own player-facing journey language.
- **Voice**: `VoiceConversation`, `VoiceState`, `VoiceOrb`, `VoiceModeCard`, and `TranscriptDraft` own the Listening Space presentation.

There is deliberately no generic `SectionTitle` or `EmptyState` primitive at this baseline. Existing empty and heading treatments carry different Chat, Journey, Home, and Voice semantics. Extract a shared component only after at least two uses need the same semantic and accessibility contract—not merely similar markup.

### 5.3 Composition Rules

- Prefer a small `Surface` base plus domain composition over a large Card with many boolean props.
- Keep player language inside feature components and engineering facts inside Developer surfaces.
- Preserve semantic roles, accessible labels, focus behavior, and button types when restyling.
- Reuse `ReiAvatar` for identity; do not duplicate avatar containers unless a domain component such as `VoiceOrb` owns additional state meaning.
- A section may use whitespace, a ruled line, or typography instead of a Card. The absence of a Card is an intentional hierarchy tool.

## 6. Navigation Contract

Navigation definitions live in `app/navigation.ts`:

- `WorkspaceId` is the stable state-level identifier.
- `WORKSPACE_LABELS` owns panel titles.
- `WORKSPACE_NAV_LABELS` owns visible navigation labels while preserving intentional context differences such as navigation **调试** versus panel title **开发者工具**.
- `WORKSPACE_SUBTITLES` owns panel descriptions.
- `AppNavigation.tsx` owns ordering, grouping, and icons, not duplicate user-facing strings.

Player navigation currently appears in this order:

```text
首页 → 聊天 → 声音 → 旅程 → 回忆 → 悬浮层 → 设置
```

Developer navigation is collapsed behind **开发者工具** and currently contains **调试** and **未来展示**. Do not remove existing entries or introduce a router merely to reorganize labels.

## 7. CSS Ownership

- `styles/tokens.css`: global non-theme tokens only.
- `styles/themes.css`: all theme-dependent colors, borders, focus colors, and depth.
- `styles/base.css`: document-level defaults and accessibility behavior.
- `components/ui/ui.css`: only domain-neutral primitive styles.
- `components/rei/rei.css`: Rei identity and presence states.
- `app/shell.css`: shell, navigation, workspace frame, responsive shell behavior, and temporary compatibility styling for unmigrated pages.
- `components/home/home.css`, `chat/chat.css`, `journey/journey.css`, and `voice/voice.css`: feature-owned presentation.
- `styles.css`: legacy compatibility and current Overlay presentation. Do not add new redesigned feature styles here; shrink it incrementally as later pages migrate.

Selectors may remain global during this migration, but feature prefixes and ownership boundaries are required. A full CSS-module migration or full deletion of `styles.css` is not part of this phase.

## 8. Animation And Motion

Motion follows three rules: **low frequency, subtle, and meaningful**.

Allowed examples:

- ReiAvatar's slow idle breathing;
- VoiceOrb's restrained listening, thinking, and speaking state changes;
- short hover, focus, theme, and workspace transitions;
- small fades or position changes that clarify state.

Do not add:

- flashy or celebratory animation;
- gamification, rewards, streaks, or achievement motion;
- constant decorative motion across multiple regions;
- neon audio visualizers, Siri-like waves, or game-HUD effects;
- motion that is the only way state is communicated.

Shared motion tokens are:

- `--motion-fast: 140ms` for direct control feedback;
- `--motion-base: 220ms` for ordinary UI state changes;
- `--motion-slow: 420ms` for calm surface/theme changes;
- `--ease-calm: cubic-bezier(0.22, 1, 0.36, 1)`.

`styles/base.css` must continue to honor `prefers-reduced-motion: reduce` by collapsing animation and transition duration. Feature CSS may add an explicit reduced-motion rule when an animation needs a readable static state.

## 9. Frozen Behavior Boundaries

This design system does not own or authorize changes to:

- backend processes, endpoints, or API schemas;
- Electron IPC and native runtime contracts;
- LLM routing, generation, prompts, or Chat streaming;
- Game Context, Extraction, Knowledge, or Session Timeline data models;
- Memory writes, confirmation, archive, or deletion behavior;
- audio capture, Local ASR, transcript quality, Voice state transitions, Direct Conversation guard, or TTS;
- Overlay lifecycle, safe content, or Settings persistence.

Renderer components should accept current view data and callbacks. A visual migration must not silently absorb these behaviors.

## 10. Current Consolidation Status

The implementation and durable guideline are aligned on the core companion direction, Light/Dark palettes, Chinese-first player navigation, reduced-motion support, quiet Rei presence, and Player/Developer information separation.

The Phase 1 foundation is frozen as:

- semantic CSS variables and two theme value sets;
- one shared AppShell and state-based navigation;
- small UI primitives plus ReiAvatar;
- feature-owned Home, Chat, Journey, and Voice presentation;
- a collapsed Developer group without deleting diagnostic entry points;
- incremental coexistence with the legacy renderer and stylesheet.

## 11. Known Limitations And Next-Phase Guidance

- `App.tsx` remains a large behavior container. Future work should continue extracting presentation before moving orchestration.
- `styles.css` remains a large legacy compatibility layer and still owns the separate Overlay visual language.
- Memory, Settings, Developer Console, future presentation, and Overlay are not redesigned and must not be used as player-facing visual references.
- Some feature geometry remains intentionally local because it is not yet a repeated design decision.
- The current theme defaults to Light rather than following an operating-system preference.
- Normal workspace navigation remains state-based and has no deep links.
- Generic `SectionTitle`, `EmptyState`, Tabs, textarea, dialog, and field-row primitives should be added only when a later migration establishes a shared semantic need.

Recommended next work is one bounded page migration at a time using this contract. Memory, Settings, and Overlay must each be separate tasks with their existing behavior and data boundaries preserved.
