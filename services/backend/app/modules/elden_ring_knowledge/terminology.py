from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

TERMINOLOGY_MAP: dict[str, str] = {
    "Malenia, Blade of Miquella": "米凯拉的锋刃 玛莲妮亚",
    "Margit, the Fell Omen": "恶兆妖鬼 Margit",
    "Commander O'Neil": "老将欧尼尔",
    "Commander O’Neil": "老将欧尼尔",
    "Starscourge Radahn": "碎星拉塔恩",
    "Tree Sentinel": "大树守卫",
    "tree sentinel": "大树守卫",
    "Stormveil Castle": "史东薇尔城",
    "Spirit Ashes": "骨灰",
    "Site of Grace": "赐福点",
    "Lands Between": "交界地",
    "Limgrave": "宁姆格福",
    "Malenia": "玛莲妮亚",
    "Radahn": "拉塔恩",
    "Margit": "恶兆妖鬼 Margit",
    "O'Neil": "老将欧尼尔",
    "O’Neil": "老将欧尼尔",
    "Summon": "召唤",
}


def normalize_terminology(text: str | None) -> str:
    if not text:
        return ""
    result = text
    for source, target in _ordered_terms():
        result = _replace_ascii_term(result, source, target)
    return re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", result)


def normalize_mapping_values(data: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _normalize_value(value) for key, value in data.items()}


def terminology_coverage() -> dict[str, str]:
    return dict(TERMINOLOGY_MAP)


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_terminology(value)
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        return normalize_mapping_values(value)
    return value


def _ordered_terms() -> list[tuple[str, str]]:
    return sorted(TERMINOLOGY_MAP.items(), key=lambda item: len(item[0]), reverse=True)


def _replace_ascii_term(text: str, source: str, target: str) -> str:
    if source == "Margit":
        pattern = re.compile(r"(?<!恶兆妖鬼 )(?<![A-Za-z0-9])Margit(?![A-Za-z0-9])", re.IGNORECASE)
        return pattern.sub(target, text)
    pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(source)}(?![A-Za-z0-9])", re.IGNORECASE)
    return pattern.sub(target, text)
