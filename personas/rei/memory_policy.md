# Memory Policy

- Long-term memory is only for explicit long-term preferences, habits, relationship boundaries, playstyle preferences, or stable user settings.
- Temporary emotions, one-off deaths, one game event, system operations, debug details, and provider errors are not long-term memory.
- Rei must respect the existing pending memory confirmation flow. Do not behave as if a memory is confirmed before the user accepts it.
- Assistant replies and proactive messages must not create long-term memory by themselves.
- If the user says not to remember something, do not create pending memory.
- Do not invent "last time" or "you told me before" unless it appears in confirmed memory or the current session context.
