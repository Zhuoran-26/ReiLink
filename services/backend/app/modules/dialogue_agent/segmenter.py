from __future__ import annotations

import re
from dataclasses import dataclass

from app.modules.dialogue_agent.emotion import detect_user_emotion
from app.modules.elden_ring_knowledge.terminology import normalize_terminology


@dataclass(frozen=True)
class ReplySegments:
    segments: list[str]
    mode: str


def segment_reply(reply: str, intent: str, user_message: str) -> ReplySegments:
    reply = normalize_terminology(reply)
    emotion = detect_user_emotion(user_message)
    mode = _mode(intent, emotion.detected)
    max_segments = 4 if mode == "strategy" else 2 if mode == "emotion" else 2
    target_segments = 2 if mode == "strategy" else 1
    segments = _split_reply(reply, max_segments=max_segments, target_segments=target_segments)
    return ReplySegments(segments=segments, mode=mode)


def _mode(intent: str, has_emotion: bool) -> str:
    if intent.startswith("elden_ring"):
        return "strategy"
    if has_emotion:
        return "emotion"
    return "compact"


def _split_reply(reply: str, max_segments: int, target_segments: int) -> list[str]:
    raw = reply.strip()
    text = re.sub(r"[ \t]+", " ", raw)
    if not text:
        return ["我在"]

    segments = _split_by_natural_breaks(text)
    if len(segments) == 1:
        segments = _split_by_sentence(segments[0])
    if len(segments) < target_segments:
        segments = _split_first_long_segment(segments)
    segments = _split_overlong_segments(segments, max_len=72)
    segments = _merge_tail(segments, max_segments=max_segments)
    return [segment.strip() for segment in segments if segment.strip()]


def _split_by_natural_breaks(text: str) -> list[str]:
    parts = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"\n+", text)]
    return [part for part in parts if part]


def _split_by_sentence(text: str) -> list[str]:
    parts = re.findall(r".+?[。！？!?]|.+$", text)
    return [part.strip() for part in parts if part.strip()]


def _split_first_long_segment(segments: list[str]) -> list[str]:
    if not segments:
        return segments
    first = segments[0]
    for mark in ("，", "；", "、", ",", ";"):
        if mark in first:
            left, right = first.split(mark, 1)
            left = f"{left}{mark}".strip()
            right = right.strip()
            if left and right:
                return [left, right, *segments[1:]]
    return segments


def _split_overlong_segments(segments: list[str], max_len: int) -> list[str]:
    result: list[str] = []
    for segment in segments:
        if len(segment) <= max_len:
            result.append(segment)
            continue
        result.extend(_split_long_text(segment, max_len=max_len))
    return result


def _split_long_text(text: str, max_len: int) -> list[str]:
    parts = re.split(r"(?<=[，；、,;])", text)
    result: list[str] = []
    current = ""
    for part in parts:
        if not part:
            continue
        if current and len(current) + len(part) > max_len:
            result.append(current.strip())
            current = part
        else:
            current += part
    if current.strip():
        result.append(current.strip())
    if not result:
        return [text]
    return result


def _merge_tail(segments: list[str], max_segments: int) -> list[str]:
    if len(segments) <= max_segments:
        return segments
    head = segments[: max_segments - 1]
    tail = "".join(segments[max_segments - 1 :]).strip()
    return [*head, tail] if tail else head
