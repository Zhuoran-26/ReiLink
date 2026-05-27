import json
import re
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.modules.elden_ring_knowledge.terminology import normalize_terminology
from app.schemas.api import MemoryEntry


class ConversationStore:
    def __init__(self, conversations_dir: Path | None = None) -> None:
        self.conversations_dir = conversations_dir or settings.conversations_dir
        self.conversations_dir.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        session_id: str,
        game_id: str | None,
        persona_id: str,
        user_message: str,
        assistant_reply: str,
        timestamp: datetime,
        assistant_reply_segments: list[str] | None = None,
    ) -> None:
        normalized_reply = normalize_terminology(assistant_reply)
        normalized_segments = [normalize_terminology(segment) for segment in (assistant_reply_segments or [normalized_reply])]
        entry = {
            "timestamp": timestamp.isoformat(),
            "session_id": session_id,
            "game_id": game_id,
            "persona_id": persona_id,
            "user_message": user_message,
            "assistant_reply": normalized_reply,
            "assistant_reply_segments": normalized_segments,
        }
        with self._path(session_id).open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def list_sessions(self) -> list[str]:
        return sorted(path.stem for path in self.conversations_dir.glob("*.jsonl"))

    def read_session(self, session_id: str) -> list[MemoryEntry]:
        path = self._path(session_id)
        if not path.exists():
            return []
        return [MemoryEntry(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line]

    def recent_context(self, session_id: str, limit: int = 1) -> list[dict[str, str]]:
        entries = self.read_session(session_id)[-limit:]
        return [
            {
                "source": "current_session",
                "field": "last_exchange",
                "text": (
                    f"当前会话上一轮：用户说「{_truncate(entry.user_message)}」，"
                    f"Rei 回「{_truncate(entry.assistant_reply)}」"
                ),
            }
            for entry in entries
        ]

    def recent_assistant_replies(self, session_id: str, limit: int = 5) -> list[str]:
        return [entry.assistant_reply for entry in self.read_session(session_id)[-limit:]]

    def recent_user_messages(self, session_id: str, limit: int = 8) -> list[str]:
        return [entry.user_message for entry in self.read_session(session_id)[-limit:]]

    def _path(self, session_id: str) -> Path:
        safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", session_id)
        return self.conversations_dir / f"{safe_id}.jsonl"


def _truncate(text: str, limit: int = 80) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."
