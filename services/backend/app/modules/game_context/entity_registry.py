from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


BossMatchType = Literal["canonical_id", "exact_alias", "near_alias", "noisy_surface", "none", "ambiguous"]


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


def ground_boss_surface(value: str | None, *, canonical_hint: str | None = None) -> BossGrounding:
    """Validate a bounded noisy surface against the finite registry.

    This is candidate evidence only. It never grants auto-apply by itself; callers
    must also validate semantic role, game ownership, and state-transition intent.
    """

    normalized = _normalize_lookup(value or "")
    if not normalized:
        return BossGrounding(None, "none", 0.0, False)

    hint = ground_boss_entity(canonical_hint)
    exact = ground_boss_entity(value)
    if exact.entity:
        if hint.entity and exact.canonical_id != hint.canonical_id:
            return BossGrounding(None, "ambiguous", 0.0, False)
        return BossGrounding(exact.entity, exact.match_type, exact.confidence, False)
    if len(normalized) < 4:
        return BossGrounding(None, "none", 0.0, False)

    best_by_entity: dict[str, tuple[float, BossEntity]] = {}
    for entity in BOSS_ENTITIES:
        for alias in (entity.display_name, *entity.aliases):
            alias_key = _normalize_lookup(alias)
            if len(alias_key) < 4 or abs(len(alias_key) - len(normalized)) > 2:
                continue
            distance = _edit_distance(normalized, alias_key, limit=2)
            if distance is None:
                continue
            similarity = 1.0 - (distance / max(len(normalized), len(alias_key)))
            if similarity < 0.6:
                continue
            previous = best_by_entity.get(entity.canonical_id)
            if previous is None or similarity > previous[0]:
                best_by_entity[entity.canonical_id] = (similarity, entity)

    if not best_by_entity:
        return BossGrounding(None, "none", 0.0, False)
    best_score = max(score for score, _ in best_by_entity.values())
    winners = [entity for score, entity in best_by_entity.values() if score == best_score]
    if len(winners) != 1:
        return BossGrounding(None, "ambiguous", 0.0, False)
    winner = winners[0]
    if hint.entity and winner.canonical_id != hint.canonical_id:
        return BossGrounding(None, "ambiguous", 0.0, False)
    return BossGrounding(winner, "noisy_surface", min(0.78, 0.62 + best_score * 0.2), False)


def is_boss_negated(message: str, value: str | None) -> bool:
    grounding = ground_boss_entity(value)
    if not grounding.entity:
        return False
    compact = _normalize_lookup(message)
    before_markers = ("不打", "先不打", "暂时不打", "暫時不打", "不想打", "不是", "别再说", "別再說")
    after_markers = ("不打了", "先不打", "不打", "算了")
    for alias in (grounding.entity.canonical_id, grounding.entity.display_name, *grounding.entity.aliases):
        alias_key = _normalize_lookup(alias)
        start = compact.find(alias_key)
        while start >= 0:
            before = compact[max(0, start - 10) : start]
            after = compact[start + len(alias_key) : start + len(alias_key) + 5]
            if any(before.endswith(marker) for marker in before_markers) or any(
                after.startswith(marker) for marker in after_markers
            ):
                return True
            start = compact.find(alias_key, start + 1)
    return False


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


def _edit_distance(left: str, right: str, *, limit: int) -> int | None:
    if abs(len(left) - len(right)) > limit:
        return None
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                )
            )
        if min(current) > limit:
            return None
        previous = current
    return previous[-1] if previous[-1] <= limit else None
