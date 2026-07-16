# ReiLink UI Design Guidelines v1

> Current implementation contract: `docs/design/reilink_ui_redesign_phase_v0.md`.

## Overview

ReiLink is not an AI dashboard.

ReiLink is a calm AI companion for single-player game players.

The UI should make users feel:

- relaxed
- accompanied
- remembered
- not pressured

The product feeling should be:

"Opening ReiLink feels like returning to a quiet personal space."

Not:

- developer console
- productivity tool
- generic chatbot
- game HUD


---

# 1. Design Philosophy

## Core Keywords

- Cozy
- Calm
- Minimal
- Refined
- Companion
- Personal journey
- Soft fantasy


## Avoid

Do not create:

- cyberpunk AI aesthetics
- excessive gradients
- aggressive neon colors
- dashboard-heavy layouts
- game HUD style
- mascot-like overwhelming character presentation


Rei should feel present, but never dominate the user's attention.


---

# 2. Rei Personality → UI Translation

Rei personality:

- quiet
- restrained
- warm but distant
- minimal emotional expression
- slowly builds connection
- caring without being intrusive


UI implications:

Prefer:

- whitespace
- subtle transitions
- calm colors
- gentle feedback
- low information pressure


Avoid:

- excessive animations
- cheerful stickers
- loud notifications
- playful assistant style


---

# 3. Visual Identity

## Overall Style

"Cozy fantasy journal"

The visual inspiration comes from:

- personal journal
- travel diary
- JRPG menu design
- quiet night companion space


Not:

- anime character showcase
- fantasy game interface


---

# 4. Color System

## Light Mode

Primary background:

Warm Ivory

Example:

#F5EFE6


Surface:

Latte Beige

Example:

#E8D8C3


Accent:

Muted Purple

Example:

#A98FB8


Highlight:

Warm Gold

Example:

#C9A45C


Text:

Soft Brown

Example:

#4A3B32


---

## Dark Mode

Dark mode is not pure black.

It represents:

"Rei accompanying the user at night."


Background:

Coffee Black

Example:

#211B18


Surface:

Deep Plum

Example:

#28202F


Accent:

Soft Lavender


Highlight:

Warm Light


---

# 5. Layout Principles

## Information Density

Default user mode should only show information useful to players.

Hide:

- provider details
- extraction details
- schema information
- debug states


Developer information belongs in Developer Mode.


---

# 6. Components

## Cards

Cards should:

- have soft rounded corners
- use layered surfaces
- avoid strong borders
- use subtle shadows


Avoid:

- sharp rectangles
- dense tables
- admin dashboard style


---

## Buttons

Buttons should feel calm.

Prefer:

- soft colors
- clear hierarchy
- comfortable spacing


Avoid:

- aggressive CTA colors


---

# 7. Rei Avatar

Avatar is allowed.

Avatar should:

- provide personality
- support state feedback
- remain secondary to conversation


Supported states:

- idle
- listening
- thinking
- speaking


Avoid:

- full-screen character illustrations
- background character artwork
- excessive anime presentation


Anime influence should appear through:

- illustration style
- avatar
- icons
- small decorative elements


---

# 8. User Identity

Do not assign fixed identities such as:

- 冒险者
- 勇者
- 玩家


Users should define themselves.

Future support:

- nickname
- preferred addressing style


Default:

Use neutral addressing.


---

# 9. Navigation Language

User-facing UI should avoid engineering terms.

Prefer:

聊天
旅程
回忆
声音
设置


Avoid:

Game Context
Memory System
Extraction
Provider
Schema
Guard


---

# 10. Developer Mode

Developer tools remain valuable.

However:

They should not dominate the normal experience.


Default:

Player mode.


Developer mode:

- Event Stream
- Extraction Trace
- Memory Debug
- Provider Debug


---

# 11. Animation

Animations should be subtle.

Allowed:

- fade
- gentle transitions
- breathing effects
- small state changes


Avoid:

- flashy effects
- constant movement
- distracting animations


---

# 12. Future Extension

The current Rei design is the baseline persona.

Future possibilities:

- selectable personas
- user-defined personas
- Live2D
- custom companions


However:

Current UI should optimize for Rei first.
