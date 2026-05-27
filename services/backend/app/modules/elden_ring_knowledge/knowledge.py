import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.modules.elden_ring_knowledge.terminology import normalize_terminology


@dataclass
class KnowledgeSnippet:
    source: str
    title: str
    content: str
    kind: str = "general"


class KnowledgeError(RuntimeError):
    pass


class EldenRingKnowledge:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or settings.elden_ring_dir

    def search(self, query: str, intent: str = "elden_ring_general_help", limit: int = 4) -> list[KnowledgeSnippet]:
        if not self.data_dir.exists():
            raise KnowledgeError(f"Knowledge directory missing: {self.data_dir}")
        terms = self._terms(query)
        if not terms:
            return []
        results: list[tuple[int, KnowledgeSnippet]] = []
        results.extend(self._search_bosses(terms, intent))
        if intent in {"elden_ring_build", "elden_ring_general_help"}:
            for filename in ("overview.md", "beginner_tips.md", "faq.md"):
                results.extend(self._search_markdown(filename, terms))
        results.sort(key=lambda item: item[0], reverse=True)
        return [_normalize_snippet(snippet) for _, snippet in results[:limit]]

    def _search_bosses(self, terms: set[str], intent: str) -> list[tuple[int, KnowledgeSnippet]]:
        path = self.data_dir / "bosses.json"
        if not path.exists():
            raise KnowledgeError(f"Knowledge file missing: {path}")
        bosses = json.loads(path.read_text(encoding="utf-8"))
        results: list[tuple[int, KnowledgeSnippet]] = []
        for boss in bosses:
            names = [boss.get("name", ""), *boss.get("aliases", [])]
            haystack = " ".join([*names, boss.get("type", ""), boss.get("location", ""), " ".join(boss.get("tips", []))]).lower()
            score = sum(1 for term in terms if term in haystack)
            if not score:
                continue
            if intent == "elden_ring_location":
                content = boss.get("location", "")
                kind = "location"
            else:
                content = "；".join(boss.get("tips", []))
                kind = "boss_strategy"
            results.append((score + 4, KnowledgeSnippet(str(path), boss.get("name", "Boss"), content, kind)))
        return results

    def _search_markdown(self, filename: str, terms: set[str]) -> list[tuple[int, KnowledgeSnippet]]:
        path = self.data_dir / filename
        if not path.exists():
            raise KnowledgeError(f"Knowledge file missing: {path}")
        text = path.read_text(encoding="utf-8")
        chunks = [chunk.strip() for chunk in re.split(r"\n(?=##? )", text) if chunk.strip()]
        results: list[tuple[int, KnowledgeSnippet]] = []
        for chunk in chunks:
            lower = chunk.lower()
            score = sum(1 for term in terms if term in lower)
            if score:
                title = chunk.splitlines()[0].lstrip("# ").strip()
                clean = re.sub(r"^#{1,6}\s*", "", chunk, flags=re.MULTILINE)
                results.append((score, KnowledgeSnippet(str(path), title, clean[:700], "general")))
        return results

    @staticmethod
    def _terms(query: str) -> set[str]:
        lower = query.lower()
        aliases = {
            "margit": ["margit", "玛尔基特", "瑪爾基特", "恶兆妖鬼", "惡兆妖鬼", "恶兆", "惡兆"],
            "史东薇尔": ["stormveil", "史东薇尔", "史東薇爾"],
            "build": ["build", "加点", "加點", "武器", "装备", "裝備", "配装", "配裝"],
        }
        terms: set[str] = set()
        for canonical, values in aliases.items():
            if any(value in lower for value in values):
                terms.add(canonical)
                terms.update(values)
        english_stop = {"the", "and", "how", "should", "what", "with", "beat", "for", "about", "where", "is"}
        terms.update(term for term in re.findall(r"[a-zA-Z][a-zA-Z0-9'-]+", lower) if term not in english_stop)
        terms.update(token for token in re.findall(r"[\u4e00-\u9fff]{2,}", query) if token not in {"怎么", "怎么办", "哪里", "在哪", "什么"})
        return terms


def _normalize_snippet(snippet: KnowledgeSnippet) -> KnowledgeSnippet:
    return KnowledgeSnippet(
        source=snippet.source,
        title=normalize_terminology(snippet.title),
        content=normalize_terminology(snippet.content),
        kind=snippet.kind,
    )
