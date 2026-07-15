# ReiLink Project Skills

Codex discovers these repository-scoped skills from `.agents/skills`.

| Skill | Source | Revision | Upstream path |
| --- | --- | --- | --- |
| `frontend-app-builder` | `https://github.com/openai/plugins` | `11c74d6ba24d3a6d48f54a194cd00ef3beea18f9` | `plugins/build-web-apps/skills/frontend-app-builder` |
| `frontend-testing-debugging` | `https://github.com/openai/plugins` | `11c74d6ba24d3a6d48f54a194cd00ef3beea18f9` | `plugins/build-web-apps/skills/frontend-testing-debugging` |
| `react-best-practices` | `https://github.com/openai/plugins` | `11c74d6ba24d3a6d48f54a194cd00ef3beea18f9` | `plugins/build-web-apps/skills/react-best-practices` |
| `ui-design` | `https://github.com/hursh-shah/codex-design-skill` | `796166cdbe27b9aac6e069d1825b8c9d3b0b1582` | `ui-design` |

The upstream skill contents are vendored unchanged with Codex's built-in
`skill-installer` in Git mode. Regular-file permissions are normalized to
non-executable. Reinstall from the pinned revisions above when updating them.
The scoped `.gitattributes` entry preserves upstream Markdown hard line breaks
without relaxing whitespace checks for the rest of the repository.

## ReiLink Integration

- Repository instructions in `AGENTS.md` and the product direction in
  `docs/design/reilink_ui_guidelines.md` take precedence over generic skill
  defaults.
- ReiLink uses Electron, React, and Vite. Apply only the React/browser guidance
  from rules that also discuss Next.js or server rendering.
- Use the available Browser capability first for rendered UI checks, with the
  existing Playwright workflow as the fallback.
- A separate `screenshot` skill is not vendored because Browser screenshots,
  `frontend-testing-debugging`, and the existing Playwright setup already cover
  screenshot-driven iteration without duplicating project skills.
