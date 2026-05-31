from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Intent = Literal[
    "casual_chat",
    "identity_question",
    "elden_ring_boss_strategy",
    "elden_ring_location",
    "elden_ring_build",
    "elden_ring_general_help",
    "unclear",
]


@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    should_retrieve_knowledge: bool


_IDENTITY_PATTERNS = (
    "who are you",
    "what are you",
    "你是谁",
    "你叫什么",
    "你是誰",
    "介绍一下你",
)

_BOSS_NAMES = (
    "margit",
    "恶兆妖鬼",
    "惡兆妖鬼",
    "玛尔基特",
    "瑪爾基特",
    "恶兆",
    "惡兆",
    "tree sentinel",
    "大树守卫",
    "大樹守衛",
    "radahn",
    "拉塔恩",
    "malenia",
    "玛莲妮亚",
    "瑪蓮妮亞",
    "水鸟乱舞",
    "水鳥亂舞",
    "waterfowl",
    "waterfowl dance",
)
_LOCATION_WORDS = ("where", "where is", "在哪", "哪里", "哪裡", "位置", "怎么去", "路上", "地点")
_STRATEGY_WORDS = (
    "beat",
    "fight",
    "kill",
    "打不过",
    "打不過",
    "怎么打",
    "怎麼打",
    "怎么躲",
    "怎麼躲",
    "攻略",
    "打法",
    "躲",
    "boss",
    "boss战",
    "boss戰",
)
_BUILD_WORDS = ("build", "加点", "加點", "配装", "配裝", "武器", "装备", "裝備", "流派", "推荐", "推薦")
_GENERAL_HELP_WORDS = ("艾尔登", "艾爾登", "elden ring", "交界地", "史东薇尔", "史東薇爾", "赐福", "賜福", "boss")
_UNCLEAR_SHORT = ("how", "怎么", "怎麼", "怎么办", "怎麼辦", "咋办", "咋辦")


def detect_intent(message: str) -> IntentResult:
    normalized = _normalize(message)
    compact = re.sub(r"\s+", "", normalized)

    if any(pattern in normalized for pattern in _IDENTITY_PATTERNS) or any(pattern in compact for pattern in _IDENTITY_PATTERNS):
        return IntentResult("identity_question", False)

    if normalized in _UNCLEAR_SHORT or compact in _UNCLEAR_SHORT:
        return IntentResult("unclear", False)

    has_boss = any(name in normalized or name in compact for name in _BOSS_NAMES)
    has_location = any(word in normalized or word in compact for word in _LOCATION_WORDS)
    has_strategy = any(word in normalized or word in compact for word in _STRATEGY_WORDS)
    has_build = any(word in normalized or word in compact for word in _BUILD_WORDS)

    if has_boss and has_location:
        return IntentResult("elden_ring_location", True)
    if has_boss and has_strategy:
        return IntentResult("elden_ring_boss_strategy", True)
    if has_build:
        return IntentResult("elden_ring_build", True)
    if any(word in normalized or word in compact for word in _GENERAL_HELP_WORDS):
        return IntentResult("elden_ring_general_help", True)

    return IntentResult("casual_chat", False)


def _normalize(message: str) -> str:
    return message.strip().lower()
