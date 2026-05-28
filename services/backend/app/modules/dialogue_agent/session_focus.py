from __future__ import annotations

import re
from dataclasses import dataclass


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


BOSS_FOCUS_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("女武神", ("女武神", "malenia", "玛莲妮亚", "瑪蓮妮亞", "米凯拉", "米凱拉")),
    ("大树守卫", ("大树守卫", "大樹守衛", "tree sentinel")),
    ("恶兆妖鬼 Margit", ("margit", "恶兆妖鬼", "惡兆妖鬼", "玛尔基特", "瑪爾基特", "恶兆", "惡兆")),
    ("拉塔恩", ("拉塔恩", "radahn", "碎星", "拉塔恩将军", "拉塔恩將軍")),
    ("老将欧尼尔", ("老将欧尼尔", "老將歐尼爾", "欧尼尔", "歐尼爾", "老将", "老將", "commander o'neil", "commander o’neil", "o'neil", "o’neil")),
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
    return SessionFocus()


def detect_boss_focus(message: str) -> str | None:
    normalized = message.lower()
    for canonical, aliases in BOSS_FOCUS_ALIASES:
        for alias in aliases:
            if alias.lower() in normalized and not _is_negated_alias(normalized, alias):
                return canonical
    return None


def is_elliptical_boss_reference(message: str) -> bool:
    compact = re.sub(r"\s+", "", message.lower())
    return any(re.sub(r"\s+", "", marker.lower()) in compact for marker in ELLIPTICAL_BOSS_REFERENCES)


def _is_negated_alias(normalized: str, alias: str) -> bool:
    compact = re.sub(r"\s+", "", normalized.lower())
    alias_compact = re.sub(r"\s+", "", alias.lower())
    return f"不是{alias_compact}" in compact or f"不是{alias_compact}啊" in compact
