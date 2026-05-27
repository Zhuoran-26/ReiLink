# ReiLink Phase 1 Design

Phase 1 implements a runnable MVP for an original Rei-like Elden Ring companion.

Core requirements:

- Detect `eldenring.exe` on Windows with psutil.
- Return idle mock-safe status on non-Windows.
- Load `data/personas/rei_like.json`.
- Retrieve local Elden Ring markdown and JSON snippets.
- Generate replies through a replaceable LLM provider.
- Save conversations to `data/conversations/{session_id}.jsonl`.
- Provide a React desktop UI for status and chat.
- Keep voice as explicit push-to-talk-ready mock endpoints.

No official character names, protected lines, voices, or visual assets are used.

