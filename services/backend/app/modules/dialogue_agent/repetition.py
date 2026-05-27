from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
import re

OVERUSED_CORE_PHRASES = (
    "我在这里",
    "我还在这里",
    "我还在",
    "我听见了",
    "别想太多",
    "习惯你在",
    "看着你",
    "你问得太认真",
    "你问得太直接",
    "不知道怎么接",
    "不知该怎么接",
)

RELATIONSHIP_FOLLOWUP_MARKERS = (
    "喜欢",
    "不喜欢",
    "情感",
    "关心",
    "在意",
    "为什么不说",
    "為什麼不說",
    "逃避",
    "烦",
    "煩",
)


def build_repetition_guard(recent_replies: list[str]) -> str:
    repeated = repeated_core_phrases(recent_replies)
    duplicate_risk = has_exact_duplicate(recent_replies)
    similar_pair = most_similar_reply_pair(recent_replies)
    similar_risk = bool(similar_pair and similar_pair[2] >= 0.82)
    parts: list[str] = []
    if duplicate_risk or similar_risk:
        parts.append("不要重复刚才的回答。用户是在追问，需要推进关系，而不是复述。")
    if repeated:
        phrases = "、".join(repeated)
        parts.append(
            "最近 5 轮已经出现过这些核心表达，除非用户明确引用，否则不要继续复用："
            f"{phrases}。可以改用观察用户状态来回应。"
        )
    if not parts:
        return (
            "重复控制：最近回复没有明显高频核心句式。仍然要让追问链自然推进，"
            "不要把不同问题都收束成同一句。"
        )
    return "重复控制：" + " ".join(parts) + " 同一追问链要推进，不要原地重复。"


def build_followup_progression_policy(current_message: str, recent_user_messages: list[str]) -> str:
    if not _is_relationship_followup(current_message):
        return ""
    recent_related = [message for message in recent_user_messages[-5:] if _is_relationship_followup(message)]
    if not recent_related:
        return ""
    return (
        "Follow-up progression policy: 用户正在连续追问关系或情感。不要把每一轮都回避到同一个点。"
        "可以从回避、推进、设边界、反问或收住之间自然推进；不要复述刚才回答。"
        "避免继续使用“你问得太认真/太直接”“不知道怎么接”“我还在”这类安全但原地打转的句式。"
        "每次至少推进一点：回应用户为什么追问、给出关系边界、或把问题交还给用户。"
        "这些只是方向，不是固定台词。"
    )


def repeated_core_phrases(recent_replies: list[str], threshold: int = 1) -> list[str]:
    counts: Counter[str] = Counter()
    for reply in recent_replies[-5:]:
        for phrase in OVERUSED_CORE_PHRASES:
            if phrase in reply:
                counts[phrase] += 1
    return [phrase for phrase in OVERUSED_CORE_PHRASES if counts[phrase] >= threshold]


def has_high_frequency_repetition(recent_replies: list[str], threshold: int = 2) -> bool:
    return bool(repeated_core_phrases(recent_replies, threshold=threshold))


def has_exact_duplicate(recent_replies: list[str]) -> bool:
    normalized = [_core(reply) for reply in recent_replies[-5:] if _core(reply)]
    return len(normalized) != len(set(normalized))


def is_repetitive_reply(reply: str, recent_replies: list[str], threshold: float = 0.82) -> bool:
    core_reply = _core(reply)
    if not core_reply:
        return False
    for previous in recent_replies[-5:]:
        core_previous = _core(previous)
        if not core_previous:
            continue
        if core_reply == core_previous:
            return True
        if _similarity(core_reply, core_previous) >= threshold:
            return True
    return False


def most_similar_reply_pair(recent_replies: list[str]) -> tuple[str, str, float] | None:
    cores = [_core(reply) for reply in recent_replies[-5:] if _core(reply)]
    best: tuple[str, str, float] | None = None
    for index, left in enumerate(cores):
        for right in cores[index + 1 :]:
            score = _similarity(left, right)
            if best is None or score > best[2]:
                best = (left, right, score)
    return best


def build_retry_repetition_guard(reply: str) -> str:
    return (
        "重复修正：上一版回复与最近回复完全相同或高度相似。"
        "不要重复刚才的回答。用户是在追问，需要推进关系，而不是复述。"
        f"不要复用这版回复：{reply}"
    )


def _is_relationship_followup(message: str) -> bool:
    return any(marker in message for marker in RELATIONSHIP_FOLLOWUP_MARKERS)


def _core(text: str) -> str:
    normalized = re.sub(r"\s+", "", text)
    normalized = re.sub(r"[。！？!?，,；;、…\.\"'“”‘’（）()【】\[\]：:—-]", "", normalized)
    return normalized.strip()


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()
