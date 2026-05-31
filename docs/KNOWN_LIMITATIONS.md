# Known Limitations

Updated: 2026-06-01

## Game Context Pronoun Resolution

Current Game Context switching is intentionally lightweight and mostly rule-based.

Known limitation:

- If a user first mentions a game name without explicitly saying they are currently playing it, then later says a referential phrase such as "我在玩这个", "我在玩那个", or "刚才说的游戏", ReiLink may not resolve that phrase back to the previously mentioned game.
- In some cases, the temporary current game may be recorded as the literal referential phrase, such as "这个", rather than the intended game name.

Examples:

- User: "空洞骑士也挺好玩"
- User: "我在玩这个"
- Expected future behavior: resolve "这个" to "空洞骑士".
- Current limitation: this may remain unresolved or be treated as an unknown game phrase.

Planned direction:

- Add a Recent Entity Tracker for recently mentioned game entities.
- Add an LLM semantic resolver for ambiguous referential phrases.
- Keep manual override and explicit game switching higher priority than inferred pronoun resolution.

Until then, explicit game names remain the safest way to switch context, such as "我在玩空洞骑士" or "我现在去玩只狼".
