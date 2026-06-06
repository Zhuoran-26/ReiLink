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
    manifest_path: str = ""
    knowledge_path: str = ""
    knowledge_game_id: str | None = None
    knowledge_available: bool = False
    support_status: str = "unsupported"
    enabled: bool = True


@dataclass(frozen=True)
class KnowledgePackManifest:
    manifest_path: str | None = None
    manifest_status: str = "unknown"
    knowledge_pack_version: str = "unknown"
    knowledge_pack_language: str = "unknown"
    knowledge_pack_status: str = "unknown"
    coverage: list[str] = field(default_factory=list)
    last_updated: str = "unknown"
    knowledge_files: list[str] = field(default_factory=list)

    def as_debug_dict(self) -> dict[str, Any]:
        return {
            "manifest_path": self.manifest_path,
            "manifest_status": self.manifest_status,
            "knowledge_pack_version": self.knowledge_pack_version,
            "knowledge_pack_language": self.knowledge_pack_language,
            "knowledge_pack_status": self.knowledge_pack_status,
            "coverage": self.coverage,
            "last_updated": self.last_updated,
        }


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
    support_status: str | None = None
    knowledge_available: bool = False


@dataclass(frozen=True)
class GameSwitchDetection:
    game: GameCatalogEntry | None
    display_name: str | None
    confidence: float = 0.9


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
            manifest_path = str(item.get("manifest_path") or "").strip()
            knowledge_path = str(item.get("knowledge_path") or "").strip()
            if not game_id or not display_name:
                continue
            support_status = str(item.get("support_status") or "").strip() or _default_support_status(item)
            if support_status not in {"supported", "detected_only", "planned", "unsupported"}:
                support_status = "unsupported"
            knowledge_game_id = str(item.get("knowledge_game_id") or game_id).strip() or game_id
            knowledge_available = _declared_knowledge_available(item, support_status, knowledge_path)
            aliases = [str(alias).strip() for alias in item.get("aliases") or [] if str(alias).strip()]
            entries.append(
                GameCatalogEntry(
                    game_id=game_id,
                    display_name=display_name,
                    aliases=aliases,
                    manifest_path=manifest_path,
                    knowledge_path=knowledge_path,
                    knowledge_game_id=knowledge_game_id,
                    knowledge_available=knowledge_available,
                    support_status=support_status,
                    enabled=item.get("enabled") is not False,
                )
            )
        return entries

    def supported_games_count(self) -> int:
        return sum(1 for game in self.games() if self.is_knowledge_available(game))

    def enabled_games(self) -> list[GameCatalogEntry]:
        return [game for game in self.games() if game.enabled]

    def get_game(self, game_id: str | None) -> GameCatalogEntry | None:
        if not game_id:
            return None
        return next(
            (
                game
                for game in self.games()
                if game.game_id == game_id or game.knowledge_game_id == game_id
            ),
            None,
        )

    def is_knowledge_available(self, game: GameCatalogEntry | None) -> bool:
        return bool(
            game
            and game.enabled
            and game.support_status == "supported"
            and game.knowledge_available
            and game.knowledge_path
            and self.resolve_knowledge_path(game.knowledge_path).is_file()
        )

    def resolve_knowledge_path(self, knowledge_path: str) -> Path:
        return _resolve_knowledge_resource_path(knowledge_path)

    def resolve_manifest_path(self, manifest_path: str) -> Path:
        return _resolve_knowledge_resource_path(manifest_path)

    def load_manifest(self, game: GameCatalogEntry | None) -> KnowledgePackManifest:
        if not game or not game.manifest_path:
            return KnowledgePackManifest(
                manifest_path=game.manifest_path if game else None,
                manifest_status="manifest_missing",
            )
        path = self.resolve_manifest_path(game.manifest_path)
        if not path.is_file():
            return KnowledgePackManifest(
                manifest_path=game.manifest_path,
                manifest_status="manifest_missing",
            )
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return KnowledgePackManifest(
                manifest_path=game.manifest_path,
                manifest_status="manifest_invalid",
            )
        if not isinstance(raw, dict):
            return KnowledgePackManifest(
                manifest_path=game.manifest_path,
                manifest_status="manifest_invalid",
            )
        coverage = [str(item).strip() for item in raw.get("coverage") or [] if str(item).strip()]
        knowledge_files = [str(item).strip() for item in raw.get("knowledge_files") or [] if str(item).strip()]
        return KnowledgePackManifest(
            manifest_path=game.manifest_path,
            manifest_status="loaded",
            knowledge_pack_version=str(raw.get("version") or "unknown"),
            knowledge_pack_language=str(raw.get("language") or "unknown"),
            knowledge_pack_status=str(raw.get("status") or "unknown"),
            coverage=coverage,
            last_updated=str(raw.get("last_updated") or "unknown"),
            knowledge_files=knowledge_files,
        )

    def load_manifest_for_game_id(self, game_id: str | None) -> KnowledgePackManifest:
        if not game_id:
            return KnowledgePackManifest()
        return self.load_manifest(self.get_game(game_id))

    def match_game(
        self,
        *,
        current_game: str | None,
        user_message: str,
        game_session_state: dict[str, Any] | None = None,
        detected_game: dict[str, Any] | None = None,
        manual_override: dict[str, Any] | None = None,
    ) -> GameMatchResult:
        games = self.games()
        supported_count = sum(1 for game in games if self.is_knowledge_available(game))
        manual_match = self._match_manual_override(manual_override, games, supported_count)
        if manual_match:
            return manual_match
        switch_match = self.detect_explicit_game_switch(user_message)
        if switch_match:
            if switch_match.game:
                return _match_result(switch_match.game, "user_switch", switch_match.confidence, supported_count)
            return _unknown_game_match(switch_match.display_name, "user_switch", supported_count)
        explicit_query_match = self._match_explicit_user_game_query(user_message, games)
        if explicit_query_match:
            return _match_result(explicit_query_match, "user_message", 0.9, supported_count)
        detector_match = self._match_detected_game(detected_game, games, supported_count)
        if detector_match:
            return detector_match

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
            return _unknown_game_match(current_game_text, "current_game", supported_count)

        content_match = self._match_by_content_alias(_content_hint_text(user_message, game_session_state), games)
        if content_match:
            return _match_result(content_match, "alias", 0.72, supported_count)

        return _empty_match(supported_count, "no_game_detected")

    def detect_explicit_game_switch(self, user_message: str) -> GameSwitchDetection | None:
        target = _extract_explicit_switch_target(user_message)
        if not target:
            return None
        game = self._match_by_any_catalog_name(target, self.games())
        if game:
            return GameSwitchDetection(game=game, display_name=game.display_name)
        return GameSwitchDetection(game=None, display_name=target, confidence=0.75)

    @staticmethod
    def _match_manual_override(
        manual_override: dict[str, Any] | None,
        games: list[GameCatalogEntry],
        supported_count: int,
    ) -> GameMatchResult | None:
        if not isinstance(manual_override, dict) or not manual_override.get("enabled"):
            return None
        game_id = str(manual_override.get("game_id") or "").strip()
        if not game_id:
            return None
        entry = next((game for game in games if game.game_id == game_id), None)
        if not entry:
            return GameMatchResult(
                matched_game_id=None,
                matched_game_display_name=str(manual_override.get("display_name") or game_id),
                match_source="manual",
                confidence=0.0,
                knowledge_path=None,
                enabled=False,
                supported_games_count=supported_count,
                fallback_reason="no_supported_knowledge",
                support_status="unsupported",
                knowledge_available=False,
            )
        return _match_result(entry, "manual", 1.0, supported_count)

    @staticmethod
    def _match_detected_game(
        detected_game: dict[str, Any] | None,
        games: list[GameCatalogEntry],
        supported_count: int,
    ) -> GameMatchResult | None:
        if not isinstance(detected_game, dict) or detected_game.get("status") != "running":
            return None
        knowledge_game_id = str(detected_game.get("knowledge_game_id") or "").strip()
        source = str(detected_game.get("match_source") or "process")
        confidence = float(detected_game.get("match_confidence") or 0)
        if not knowledge_game_id:
            detected_game_id = str(detected_game.get("detected_game_id") or "").strip()
            entry = next((game for game in games if game.game_id == detected_game_id), None)
            if entry:
                return _match_result(entry, source, confidence or 0.95, supported_count)
            return _unsupported_detected_match(detected_game, source, supported_count)
        entry = next((game for game in games if game.game_id == knowledge_game_id or game.knowledge_game_id == knowledge_game_id), None)
        if not entry:
            detected_game_id = str(detected_game.get("detected_game_id") or "").strip()
            entry = next((game for game in games if game.game_id == detected_game_id), None)
        if not entry:
            return _unsupported_detected_match(detected_game, source, supported_count)
        return _match_result(entry, source, confidence or 0.95, supported_count)

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

    def _match_explicit_user_game_query(self, text: str, games: list[GameCatalogEntry]) -> GameCatalogEntry | None:
        if not text.strip():
            return None
        for game in games:
            for name in _catalog_names(game):
                if _value_in_text(text, name) and _is_explicit_game_query(text, name):
                    return game
        return None

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
    fallback_reason = _entry_fallback_reason(entry)
    knowledge_available = _entry_declares_supported_knowledge(entry)
    return GameMatchResult(
        matched_game_id=entry.game_id,
        matched_game_display_name=entry.display_name,
        match_source=source,
        confidence=confidence if knowledge_available else 0.0,
        knowledge_path=entry.knowledge_path if knowledge_available else None,
        enabled=entry.enabled,
        supported_games_count=supported_games_count,
        fallback_reason=fallback_reason,
        support_status=entry.support_status,
        knowledge_available=knowledge_available,
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
        support_status=None,
        knowledge_available=False,
    )


def _unknown_game_match(
    display_name: str | None,
    source: str,
    supported_games_count: int,
) -> GameMatchResult:
    return GameMatchResult(
        matched_game_id=None,
        matched_game_display_name=display_name,
        match_source=source,
        confidence=0.0,
        knowledge_path=None,
        enabled=False,
        supported_games_count=supported_games_count,
        fallback_reason="unknown_game",
        support_status="unsupported",
        knowledge_available=False,
    )


def _unsupported_detected_match(
    detected_game: dict[str, Any],
    source: str,
    supported_games_count: int,
) -> GameMatchResult:
    return GameMatchResult(
        matched_game_id=None,
        matched_game_display_name=str(detected_game.get("display_name") or detected_game.get("detected_game_id") or ""),
        match_source=source,
        confidence=0.0,
        knowledge_path=None,
        enabled=False,
        supported_games_count=supported_games_count,
        fallback_reason="no_supported_knowledge",
        support_status="unsupported",
        knowledge_available=False,
    )


def _default_support_status(item: dict[str, Any]) -> str:
    if item.get("enabled") is False:
        return "unsupported"
    if item.get("knowledge_available") is True or str(item.get("knowledge_path") or "").strip():
        return "supported"
    return "unsupported"


def _declared_knowledge_available(item: dict[str, Any], support_status: str, knowledge_path: str) -> bool:
    if "knowledge_available" in item:
        return item.get("knowledge_available") is True
    return support_status == "supported" and bool(knowledge_path)


def _entry_declares_supported_knowledge(entry: GameCatalogEntry) -> bool:
    return bool(entry.enabled and entry.support_status == "supported" and entry.knowledge_available and entry.knowledge_path)


def _resolve_knowledge_resource_path(resource_path: str) -> Path:
    path = Path(resource_path)
    if path.is_absolute():
        return path
    parts = path.parts
    for index in range(len(parts) - 2):
        if parts[index : index + 3] == ("data", "knowledge", "games"):
            return settings.knowledge_games_dir.joinpath(*parts[index + 3 :])
        if parts[index : index + 2] == ("knowledge", "games"):
            return settings.knowledge_games_dir.joinpath(*parts[index + 2 :])
    return settings.repo_root / path


def _entry_fallback_reason(entry: GameCatalogEntry) -> str | None:
    if not entry.enabled:
        return "knowledge_disabled"
    if entry.support_status != "supported" or not entry.knowledge_available or not entry.knowledge_path:
        return "no_supported_knowledge"
    return None


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


_SWITCH_TARGET_PATTERNS = (
    re.compile(r"(?:不是|不在|没在|沒有在|没有在)玩[^，,。！？?]+.*?(?:是|改成|换成|換成)(?:在)?玩(?P<game>[^，,。！？?]+)", re.IGNORECASE),
    re.compile(r"(?:换个游戏|換個遊戲|换游戏|換遊戲|不聊[^，,。！？?]*了).*?(?:我)?(?:现在|現在|目前)?(?:在)?玩(?!过|過)(?P<game>[^，,。！？?]+)", re.IGNORECASE),
    re.compile(r"(?:我|俺|咱|现在|現在|目前|今天|今晚|这会儿|這會兒).{0,6}玩(?:一个|一個)?叫(?P<game>[^，,。！？?]+?)的游戏", re.IGNORECASE),
    re.compile(r"(?:我|俺|咱|现在|現在|目前|今天|今晚|这会儿|這會兒).{0,6}(?:在玩|玩(?!过|過)|开了|開了|打开了|打開了|去玩|改玩)(?P<game>[^，,。！？?]+)", re.IGNORECASE),
)


def _extract_explicit_switch_target(text: str) -> str | None:
    if not text.strip():
        return None
    for pattern in _SWITCH_TARGET_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        target = _clean_switch_target(match.group("game"))
        if target:
            return target
    return None


def _clean_switch_target(value: str) -> str | None:
    text = re.sub(r"\s+", "", value).strip("「」『』“”\"' ")
    if not text:
        return None
    text = re.split(r"(?:怎么|怎麼|咋|如何|攻略|打法|吗|嗎|么|嘛|呢|吧)", text, maxsplit=1)[0]
    text = re.sub(r"(?:这个|這個)?游戏$", "", text)
    text = re.sub(r"(?:了|啦|啊|呀)$", "", text)
    text = text.strip("「」『』“”\"' ")
    if len(text) < 2:
        return None
    return text


_EXPLICIT_GAME_QUERY_SIGNALS = (
    "怎么打",
    "怎麼打",
    "怎么躲",
    "怎麼躲",
    "打法",
    "攻略",
    "注意",
    "在哪",
    "哪里",
    "哪裡",
    "路线",
    "路線",
    "地图",
    "地圖",
    "护符",
    "護符",
    "回血",
    "装备",
    "裝備",
    "boss",
    "卡在",
    "卡住",
    "打不过",
    "打不過",
    "有什么",
    "有什麼",
)

_GAME_POSSESSIVE_CONNECTORS = (
    "里",
    "裡",
    "裏",
    "里的",
    "裡的",
    "裏的",
    "里面",
    "裡面",
    "裏面",
    "中",
    "的",
)


def _catalog_names(game: GameCatalogEntry) -> list[str]:
    return _dedupe([game.game_id, game.knowledge_game_id or "", game.display_name, *game.aliases])


def _is_explicit_game_query(text: str, game_name: str) -> bool:
    compact_text = _compact(_normalize(text))
    compact_name = _compact(_normalize(game_name))
    if len(compact_name) < 2 or compact_name not in compact_text:
        return False
    suffix = compact_text.split(compact_name, maxsplit=1)[1]
    if any(suffix.startswith(_compact(_normalize(connector))) for connector in _GAME_POSSESSIVE_CONNECTORS):
        return True
    return any(_compact(_normalize(signal)) in compact_text for signal in _EXPLICIT_GAME_QUERY_SIGNALS)


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
