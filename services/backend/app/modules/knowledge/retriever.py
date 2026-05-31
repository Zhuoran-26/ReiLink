from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.modules.elden_ring_knowledge.terminology import normalize_terminology


@dataclass(frozen=True)
class KnowledgeSnippet:
    source: str
    title: str
    content: str
    kind: str = "general"
    source_id: str | None = None
    topics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class KnowledgeRetrievalResult:
    matched: bool
    game_id: str | None
    topics: list[str]
    snippets: list[KnowledgeSnippet]
    confidence: float

    def as_debug_dict(self) -> dict[str, Any]:
        return {
            "knowledge_matched": self.matched,
            "game_id": self.game_id,
            "matched_topics": self.topics,
            "snippets_count": len(self.snippets),
            "snippet_titles": [snippet.title for snippet in self.snippets],
            "knowledge_used_in_prompt": self.matched and bool(self.snippets),
            "confidence": self.confidence,
        }


class GameKnowledgeRetriever:
    def __init__(self, games_dir: Path | None = None) -> None:
        self.games_dir = games_dir or settings.knowledge_games_dir

    def retrieve(
        self,
        *,
        current_game: str | None,
        user_message: str,
        current_boss: str | None = None,
        game_session_state: dict[str, Any] | None = None,
        intent: str = "casual_chat",
        limit: int = 3,
    ) -> KnowledgeRetrievalResult:
        game_id = self._resolve_game_id(current_game, intent)
        if not game_id:
            return self._empty()

        snippets_path = self.games_dir / game_id / "snippets.json"
        if not snippets_path.is_file():
            return self._empty(game_id=game_id)

        entries = self._load_entries(snippets_path)
        terms = self._terms(user_message, current_boss, game_session_state)
        if not terms and not intent.startswith(f"{game_id}_"):
            return self._empty(game_id=game_id)

        scored: list[tuple[int, KnowledgeSnippet]] = []
        for entry in entries:
            score = self._score_entry(entry, terms, intent)
            if score <= 0:
                continue
            scored.append((score, self._snippet(entry, snippets_path, game_id)))

        scored.sort(key=lambda item: item[0], reverse=True)
        snippets = [snippet for _, snippet in scored[: max(1, min(limit, 3))]]
        topics = _dedupe(topic for snippet in snippets for topic in snippet.topics)
        confidence = min(1.0, round((scored[0][0] / 12), 2)) if scored else 0.0
        return KnowledgeRetrievalResult(
            matched=bool(snippets),
            game_id=game_id if snippets else None,
            topics=topics,
            snippets=snippets,
            confidence=confidence if snippets else 0.0,
        )

    def search(self, query: str, intent: str = "elden_ring_general_help", limit: int = 3) -> list[KnowledgeSnippet]:
        result = self.retrieve(
            current_game=None,
            user_message=query,
            current_boss=None,
            game_session_state=None,
            intent=intent,
            limit=limit,
        )
        return result.snippets

    def empty_result(self) -> KnowledgeRetrievalResult:
        return self._empty()

    @staticmethod
    def _resolve_game_id(current_game: str | None, intent: str) -> str | None:
        if current_game:
            normalized = current_game.strip().lower().replace(" ", "_").replace("-", "_")
            if normalized in {"elden_ring", "艾尔登法环", "艾爾登法環"}:
                return "elden_ring"
            return None
        if intent.startswith("elden_ring_"):
            return "elden_ring"
        return None

    @staticmethod
    def _load_entries(path: Path) -> list[dict[str, Any]]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(raw, list):
            return []
        return [item for item in raw if isinstance(item, dict)]

    def _terms(
        self,
        user_message: str,
        current_boss: str | None,
        game_session_state: dict[str, Any] | None,
    ) -> set[str]:
        text_parts = [user_message, current_boss or ""]
        session_boss = (game_session_state or {}).get("current_boss")
        if isinstance(session_boss, dict):
            text_parts.append(str(session_boss.get("name") or ""))
        elif session_boss:
            text_parts.append(str(session_boss))
        text = " ".join(text_parts)
        lower = text.lower()
        terms: set[str] = set()
        aliases = {
            "margit": ["margit", "玛尔基特", "瑪爾基特", "恶兆妖鬼", "惡兆妖鬼", "恶兆", "惡兆"],
            "malenia": ["malenia", "玛莲妮亚", "瑪蓮妮亞", "女武神", "米凯拉"],
            "waterfowl": ["waterfowl", "waterfowl dance", "水鸟乱舞", "水鳥亂舞"],
            "dodge": ["躲", "闪", "閃", "翻滚", "翻滾", "roll", "dodge"],
            "strategy": ["攻略", "打法", "怎么打", "怎麼打", "打不过", "打不過", "怎么躲", "怎麼躲"],
        }
        for canonical, values in aliases.items():
            if any(value in lower for value in values):
                terms.add(canonical)
                terms.update(values)
        english_stop = {"the", "and", "how", "should", "what", "with", "beat", "for", "about", "where", "is"}
        terms.update(term for term in re.findall(r"[a-zA-Z][a-zA-Z0-9'-]+", lower) if term not in english_stop)
        terms.update(token for token in re.findall(r"[\u4e00-\u9fff]{2,}", text) if token not in {"怎么", "怎么办", "哪里", "在哪", "什么"})
        return terms

    @staticmethod
    def _score_entry(entry: dict[str, Any], terms: set[str], intent: str) -> int:
        searchable = " ".join(
            str(part)
            for part in (
                entry.get("id"),
                entry.get("title"),
                entry.get("kind"),
                entry.get("summary"),
                " ".join(str(item) for item in entry.get("topics") or []),
                " ".join(str(item) for item in entry.get("aliases") or []),
            )
        ).lower()
        aliases = [str(item).lower() for item in entry.get("aliases") or []]
        score = sum(1 for term in terms if term.lower() in searchable)
        score += sum(5 for alias in aliases if alias and alias in " ".join(terms).lower())
        intent_tags = {str(item) for item in entry.get("intent_tags") or []}
        if intent in intent_tags:
            score += 3
        if intent.startswith("elden_ring_") and any(str(topic).startswith("boss") for topic in entry.get("topics") or []):
            score += 1
        return score

    @staticmethod
    def _snippet(entry: dict[str, Any], path: Path, game_id: str) -> KnowledgeSnippet:
        source_id = str(entry.get("id") or entry.get("title") or "knowledge")
        content = _truncate(normalize_terminology(str(entry.get("summary") or entry.get("content") or "")), 220)
        return KnowledgeSnippet(
            source=_source_label(path),
            source_id=source_id,
            title=normalize_terminology(str(entry.get("title") or source_id)),
            content=content,
            kind=str(entry.get("kind") or "general"),
            topics=[str(topic) for topic in entry.get("topics") or [game_id]],
        )

    @staticmethod
    def _empty(game_id: str | None = None) -> KnowledgeRetrievalResult:
        return KnowledgeRetrievalResult(False, game_id, [], [], 0.0)


def _source_label(path: Path) -> str:
    try:
        return str(path.relative_to(settings.repo_root))
    except ValueError:
        return str(path)


def _truncate(text: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _dedupe(items: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = str(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
