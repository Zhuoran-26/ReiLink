from __future__ import annotations

import re
from dataclasses import dataclass

from app.modules.game_context.entity_registry import BossEntity, find_boss_mentions, is_boss_negated


@dataclass(frozen=True)
class SessionFocus:
    boss: str | None = None
    source: str = "none"

    @property
    def has_boss(self) -> bool:
        return self.boss is not None

    def as_prompt_line(self) -> str:
        if not self.boss:
            return ""
        return (
            f"当前会话焦点 boss：{self.boss}。"
            "如果用户说一直打不过、还是不行、又死了、重新试一下、它、那个、刚才那个或这个 boss，"
            "默认指向这个 boss；除非用户明确切换话题，不要再问“哪个 boss”。"
        )


ELLIPTICAL_BOSS_REFERENCES = (
    "一直打不过",
    "一直打不過",
    "还是不行",
    "還是不行",
    "又死",
    "重新试一下",
    "重新試一下",
    "再试",
    "再試",
    "它",
    "那个",
    "那個",
    "刚才那个",
    "剛才那個",
    "这个boss",
    "這個boss",
    "这个 boss",
    "這個 boss",
    "这个",
    "這個",
    "打不过啊",
    "打不過啊",
)


def resolve_session_focus(current_message: str, recent_user_messages: list[str]) -> SessionFocus:
    current_boss = detect_boss_focus(current_message)
    if current_boss:
        return SessionFocus(current_boss, "current_message")
    if not is_elliptical_boss_reference(current_message):
        return SessionFocus()
    for message in reversed(recent_user_messages[-8:]):
        boss = detect_boss_focus(message)
        if boss:
            return SessionFocus(boss, "recent_session")
        if _has_explicit_negated_boss(message):
            return SessionFocus(source="explicit_focus_boundary")
    return SessionFocus()


def detect_boss_focus(message: str) -> str | None:
    normalized = message.lower()
    for grounding in find_boss_mentions(message):
        entity = grounding.entity
        if entity and not _is_negated_entity(normalized, entity):
            return entity.display_name
    return None


def is_elliptical_boss_reference(message: str) -> bool:
    compact = re.sub(r"\s+", "", message.lower())
    return any(re.sub(r"\s+", "", marker.lower()) in compact for marker in ELLIPTICAL_BOSS_REFERENCES)


def _is_negated_entity(normalized: str, entity: BossEntity) -> bool:
    return is_boss_negated(normalized, entity.canonical_id)


def _has_explicit_negated_boss(message: str) -> bool:
    return any(
        grounding.entity and is_boss_negated(message, grounding.entity.canonical_id)
        for grounding in find_boss_mentions(message)
    )
