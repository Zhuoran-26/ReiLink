from __future__ import annotations

import re

FORBIDDEN_PHRASES = (
    "请问",
    "有什么可以帮助你",
    "有什麽可以帮助你",
    "作为 AI",
    "作为AI",
    "根据你的问题",
    "建议你",
)

def apply_rei_style(reply: str, seed: str = "") -> str:
    text = reply.strip()
    text = _normalize_ellipsis(text)
    text = _dedupe_sentence_punctuation(text)
    return text.strip() or "我在"


def _normalize_ellipsis(text: str) -> str:
    text = re.sub(r"\.{3,}", "……", text)
    text = re.sub(r"(?:…{2,})+", "……", text)
    return text


def _dedupe_sentence_punctuation(text: str) -> str:
    text = re.sub(r"。{2,}", "。", text)
    text = re.sub(r"？{2,}", "？", text)
    text = re.sub(r"！{2,}", "！", text)
    text = re.sub(r"，{2,}", "，", text)
    return text
