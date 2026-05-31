from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.modules.elden_ring_knowledge.terminology import normalize_terminology


@dataclass(frozen=True)
class GameCatalogEntry:
    game_id: str
    display_name: str
    aliases: list[str] = field(default_factory=list)
    knowledge_path: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class GameMatchResult:
    matched_game_id: str | None
    matched_game_display_name: str | None
    match_source: str
    confidence: float
    knowledge_path: str | None
    enabled: bool
    supported_games_count: int
    fallback_reason: str | None = None


class GameCatalog:
    def __init__(self, catalog_path: Path | None = None) -> None:
        self.catalog_path = catalog_path or (settings.knowledge_games_dir / "catalog.json")

    def games(self) -> list[GameCatalogEntry]:
        try:
            raw = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(raw, dict):
            return []
        games = raw.get("games")
        if not isinstance(games, list):
            return []
        entries: list[GameCatalogEntry] = []
        for item in games:
            if not isinstance(item, dict):
                continue
            game_id = str(item.get("game_id") or "").strip()
            display_name = str(item.get("display_name") or "").strip()
            knowledge_path = str(item.get("knowledge_path") or "").strip()
            if not game_id or not display_name or not knowledge_path:
                continue
            aliases = [str(alias).strip() for alias in item.get("aliases") or [] if str(alias).strip()]
            entries.append(
                GameCatalogEntry(
                    game_id=game_id,
                    display_name=display_name,
                    aliases=aliases,
                    knowledge_path=knowledge_path,
                    enabled=item.get("enabled") is not False,
                )
            )
        return entries

    def supported_games_count(self) -> int:
        return sum(1 for game in self.games() if game.enabled)

    def resolve_knowledge_path(self, knowledge_path: str) -> Path:
        path = Path(knowledge_path)
        if path.is_absolute():
            return path
        return settings.repo_root / path

    def match_game(
        self,
        *,
        current_game: str | None,
        user_message: str,
        game_session_state: dict[str, Any] | None = None,
    ) -> GameMatchResult:
        games = self.games()
        supported_count = sum(1 for game in games if game.enabled)
        current_game_text = _first_text(current_game, _state_value(game_session_state, "current_game"))
        current_game_unsupported = False

        if current_game_text:
            current_match = self._match_by_any_catalog_name(current_game_text, games)
            if current_match:
                return _match_result(current_match, "current_game", 0.95, supported_count)
            current_game_unsupported = True

        primary_match = self._match_by_primary_name(user_message, games)
        if primary_match:
            return _match_result(primary_match, "user_message", 0.9, supported_count)

        alias_match = self._match_by_catalog_alias(user_message, games)
        if alias_match:
            return _match_result(alias_match, "alias", 0.85, supported_count)

        if current_game_unsupported:
            return _empty_match(supported_count, "unsupported_game")

        content_match = self._match_by_content_alias(_content_hint_text(user_message, game_session_state), games)
        if content_match:
            return _match_result(content_match, "alias", 0.72, supported_count)

        return _empty_match(supported_count, "no_knowledge_match")

    @staticmethod
    def _match_by_primary_name(text: str, games: list[GameCatalogEntry]) -> GameCatalogEntry | None:
        for game in games:
            if _value_in_text(text, game.game_id) or _value_in_text(text, game.display_name):
                return game
        return None

    @staticmethod
    def _match_by_catalog_alias(text: str, games: list[GameCatalogEntry]) -> GameCatalogEntry | None:
        for game in games:
            if any(_value_in_text(text, alias) for alias in game.aliases):
                return game
        return None

    def _match_by_any_catalog_name(self, text: str, games: list[GameCatalogEntry]) -> GameCatalogEntry | None:
        return self._match_by_primary_name(text, games) or self._match_by_catalog_alias(text, games)

    def _match_by_content_alias(self, text: str, games: list[GameCatalogEntry]) -> GameCatalogEntry | None:
        if not text.strip():
            return None
        for game in games:
            for alias in self._snippet_aliases(game):
                if _is_strong_content_hint(alias) and _value_in_text(text, alias):
                    return game
        return None

    def _snippet_aliases(self, game: GameCatalogEntry) -> list[str]:
        path = self.resolve_knowledge_path(game.knowledge_path)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(raw, list):
            return []
        aliases: list[str] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            aliases.extend(str(alias).strip() for alias in item.get("aliases") or [] if str(alias).strip())
        return _dedupe(aliases)


def _match_result(
    entry: GameCatalogEntry,
    source: str,
    confidence: float,
    supported_games_count: int,
) -> GameMatchResult:
    return GameMatchResult(
        matched_game_id=entry.game_id,
        matched_game_display_name=entry.display_name,
        match_source=source,
        confidence=confidence if entry.enabled else 0.0,
        knowledge_path=entry.knowledge_path,
        enabled=entry.enabled,
        supported_games_count=supported_games_count,
        fallback_reason=None if entry.enabled else "knowledge_disabled",
    )


def _empty_match(supported_games_count: int, fallback_reason: str) -> GameMatchResult:
    return GameMatchResult(
        matched_game_id=None,
        matched_game_display_name=None,
        match_source="none",
        confidence=0.0,
        knowledge_path=None,
        enabled=False,
        supported_games_count=supported_games_count,
        fallback_reason=fallback_reason,
    )


def _content_hint_text(user_message: str, game_session_state: dict[str, Any] | None) -> str:
    parts = [user_message]
    state = game_session_state or {}
    current_boss = state.get("current_boss")
    if isinstance(current_boss, dict):
        parts.append(str(current_boss.get("name") or ""))
    elif current_boss:
        parts.append(str(current_boss))
    for key in ("last_boss", "last_attempted_boss", "last_cleared_boss"):
        value = state.get(key)
        if value:
            parts.append(str(value))
    for topic in state.get("recent_game_topics") or []:
        parts.append(str(topic))
    return " ".join(part for part in parts if part)


def _state_value(state: dict[str, Any] | None, key: str) -> str | None:
    if not isinstance(state, dict):
        return None
    value = state.get(key)
    return str(value) if value else None


def _first_text(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def _value_in_text(text: str | None, value: str | None) -> bool:
    if not text or not value:
        return False
    normalized_text = _normalize(text)
    normalized_value = _normalize(value)
    compact_value = _compact(normalized_value)
    if len(compact_value) < 2:
        return False
    return normalized_value in normalized_text or compact_value in _compact(normalized_text)


def _normalize(text: str) -> str:
    return normalize_terminology(str(text)).lower().strip()


def _compact(text: str) -> str:
    return re.sub(r"[\s_\-:：·•.。?？!！'\"“”‘’]+", "", text)


_GENERIC_CONTENT_HINTS = {
    "boss",
    "boss战",
    "boss戰",
    "攻略",
    "打法",
    "位置",
    "地点",
    "地點",
    "战斗节奏",
    "戰鬥節奏",
    "翻滚",
    "翻滾",
    "精力",
    "贪刀",
    "貪刀",
    "召唤",
    "召喚",
    "躲避",
    "dodge",
    "roll",
    "stamina",
    "location",
    "preparation",
    "summon",
}
_GENERIC_CONTENT_HINTS = {_compact(_normalize(item)) for item in _GENERIC_CONTENT_HINTS}


def _is_strong_content_hint(alias: str) -> bool:
    compact = _compact(_normalize(alias))
    if compact in _GENERIC_CONTENT_HINTS:
        return False
    if re.fullmatch(r"[a-z0-9]+", compact) and len(compact) < 4:
        return False
    return len(compact) >= 2


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
