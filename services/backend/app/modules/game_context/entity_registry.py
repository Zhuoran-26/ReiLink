from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


BossMatchType = Literal["canonical_id", "exact_alias", "near_alias", "none", "ambiguous"]


@dataclass(frozen=True)
class BossEntity:
    canonical_id: str
    display_name: str
    game_id: str
    game_display_name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class BossGrounding:
    entity: BossEntity | None
    match_type: BossMatchType
    confidence: float
    auto_apply: bool

    @property
    def canonical_id(self) -> str | None:
        return self.entity.canonical_id if self.entity else None

    @property
    def display_name(self) -> str | None:
        return self.entity.display_name if self.entity else None


BOSS_ENTITIES: tuple[BossEntity, ...] = (
    BossEntity(
        canonical_id="margit",
        display_name="恶兆妖鬼 Margit",
        game_id="elden_ring",
        game_display_name="Elden Ring",
        aliases=(
            "Margit",
            "Margit, the Fell Omen",
            "恶兆妖鬼",
            "惡兆妖鬼",
            "恶兆",
            "惡兆",
            "玛尔基特",
            "瑪爾基特",
            "玛尔吉特",
            "瑪爾吉特",
            "马尔吉特",
            "馬爾吉特",
        ),
    ),
    BossEntity(
        canonical_id="godrick",
        display_name="接肢葛瑞克",
        game_id="elden_ring",
        game_display_name="Elden Ring",
        aliases=(
            "Godrick",
            "Godrick the Grafted",
            "葛瑞克",
            "接肢葛瑞克",
            "接肢的葛瑞克",
        ),
    ),
    BossEntity(
        canonical_id="malenia",
        display_name="女武神",
        game_id="elden_ring",
        game_display_name="Elden Ring",
        aliases=(
            "Malenia",
            "Malenia, Blade of Miquella",
            "女武神",
            "玛莲妮亚",
            "瑪蓮妮亞",
            "米凯拉的锋刃",
            "米凱拉的鋒刃",
            "米凯拉",
            "米凱拉",
        ),
    ),
    BossEntity(
        canonical_id="tree_sentinel",
        display_name="大树守卫",
        game_id="elden_ring",
        game_display_name="Elden Ring",
        aliases=("Tree Sentinel", "大树守卫", "大樹守衛"),
    ),
    BossEntity(
        canonical_id="radahn",
        display_name="拉塔恩",
        game_id="elden_ring",
        game_display_name="Elden Ring",
        aliases=("Radahn", "Starscourge Radahn", "拉塔恩", "碎星", "拉塔恩将军", "拉塔恩將軍"),
    ),
    BossEntity(
        canonical_id="commander_oneil",
        display_name="老将欧尼尔",
        game_id="elden_ring",
        game_display_name="Elden Ring",
        aliases=(
            "Commander O'Neil",
            "Commander O’Neil",
            "O'Neil",
            "O’Neil",
            "老将欧尼尔",
            "老將歐尼爾",
            "欧尼尔",
            "歐尼爾",
            "老将",
            "老將",
        ),
    ),
    BossEntity(
        canonical_id="false_knight",
        display_name="False Knight",
        game_id="hollow_knight",
        game_display_name="空洞骑士",
        aliases=("False Knight", "假骑士", "假騎士"),
    ),
)


def _normalize_lookup(value: str) -> str:
    return re.sub(r"[\s_\-:：·•.,。?？!！'\"“”‘’()（）]+", "", value.casefold())


_BOSS_BY_ID = {_normalize_lookup(entity.canonical_id): entity for entity in BOSS_ENTITIES}
_EXACT_ALIASES = {
    _normalize_lookup(alias): entity
    for entity in BOSS_ENTITIES
    for alias in (entity.canonical_id, entity.display_name, *entity.aliases)
}


def boss_entity_ids() -> tuple[str, ...]:
    return tuple(entity.canonical_id for entity in BOSS_ENTITIES)


def boss_aliases() -> tuple[str, ...]:
    return tuple(alias for entity in BOSS_ENTITIES for alias in entity.aliases)


def boss_display_name(value: str | None) -> str | None:
    grounding = ground_boss_entity(value)
    return grounding.display_name


def boss_game_display_name(value: str | None) -> str | None:
    grounding = ground_boss_entity(value)
    return grounding.entity.game_display_name if grounding.entity else None


def ground_boss_entity(value: str | None, *, allow_near_match: bool = False) -> BossGrounding:
    normalized = _normalize_lookup(value or "")
    if not normalized:
        return BossGrounding(None, "none", 0.0, False)
    canonical = _BOSS_BY_ID.get(normalized)
    if canonical:
        return BossGrounding(canonical, "canonical_id", 1.0, True)
    exact = _EXACT_ALIASES.get(normalized)
    if exact:
        return BossGrounding(exact, "exact_alias", 0.95, True)
    if not allow_near_match or len(normalized) < 4:
        return BossGrounding(None, "none", 0.0, False)

    matches = {
        entity.canonical_id: entity
        for alias, entity in _EXACT_ALIASES.items()
        if len(alias) >= 4 and abs(len(alias) - len(normalized)) <= 1 and _edit_distance_at_most_one(normalized, alias)
    }
    if len(matches) == 1:
        return BossGrounding(next(iter(matches.values())), "near_alias", 0.72, False)
    if len(matches) > 1:
        return BossGrounding(None, "ambiguous", 0.0, False)
    return BossGrounding(None, "none", 0.0, False)


def find_boss_mentions(message: str) -> list[BossGrounding]:
    normalized = _normalize_lookup(message)
    found: list[tuple[int, int, BossEntity]] = []
    for entity in BOSS_ENTITIES:
        aliases = (entity.canonical_id, entity.display_name, *entity.aliases)
        positions = [
            (normalized.find(alias_key), len(alias_key))
            for alias in aliases
            if (alias_key := _normalize_lookup(alias)) and alias_key in normalized
        ]
        if positions:
            start, length = min(positions, key=lambda item: (item[0], -item[1]))
            found.append((start, -length, entity))
    found.sort(key=lambda item: (item[0], item[1]))
    return [BossGrounding(entity, "exact_alias", 0.95, True) for _, _, entity in found]


def detect_boss_mention(message: str) -> BossGrounding:
    mentions = find_boss_mentions(message)
    return mentions[0] if mentions else BossGrounding(None, "none", 0.0, False)


def _edit_distance_at_most_one(left: str, right: str) -> bool:
    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right, strict=True)) <= 1
    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    short_index = 0
    long_index = 0
    skipped = False
    while short_index < len(shorter) and long_index < len(longer):
        if shorter[short_index] == longer[long_index]:
            short_index += 1
            long_index += 1
            continue
        if skipped:
            return False
        skipped = True
        long_index += 1
    return True
