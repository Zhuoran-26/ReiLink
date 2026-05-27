from __future__ import annotations

import re

_FALLBACKS = {
    "identity_question": "我是 Rei。会在旁边陪你。",
    "elden_ring_boss_strategy": "别急。少打一刀，先活下来。",
    "elden_ring_location": "在通往史东薇尔城的路上。你到城门前，基本就会遇见他。",
    "elden_ring_build": "先别贪伤害。血量、武器强化和顺手，比数字好看更重要。",
    "unclear": "说清楚一点。你想问 Boss，路线，还是装备？",
    "casual_chat": "嗯，我听着。",
    "elden_ring_general_help": "别硬撑。先确认路线和装备，再往前走。",
}

_BLOCKED_LANGUAGE = (
    "屏幕的光藏不住",
    "夜色",
    "孤独的旅途",
    "像……一样",
    "路还长",
    "旅途还在",
    "风景还在",
    "喜欢的定义",
    "因人而异",
    "作为一个陪伴者",
    "我会尽力理解你",
    "你的感受是合理的",
    "我希望我的陪伴",
    "根据记忆",
)


def validate_or_repair(reply: str, intent: str) -> str:
    cleaned = _clean(reply)
    if not _is_valid(cleaned):
        return _FALLBACKS.get(intent, _FALLBACKS["casual_chat"])
    return cleaned


def _clean(reply: str) -> str:
    text = reply.strip()
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n+ *", "\n", text).strip()
    sentences = re.findall(r".+?[。！？!?](?:[ \t]*\n?|$)|.+$", text, flags=re.DOTALL)
    compact = "".join(sentence for sentence in sentences[:3] if sentence).strip()
    return compact or text


def _is_valid(reply: str) -> bool:
    if not reply:
        return False
    if "##" in reply or reply.startswith("#"):
        return False
    if _looks_like_raw_knowledge(reply):
        return False
    if len(re.findall(r"[\u4e00-\u9fff]", reply)) < 2:
        return False
    if len(re.findall(r"[。！？!?]", reply)) > 3:
        return False
    if len(reply) > 180:
        return False
    if any(phrase in reply for phrase in _BLOCKED_LANGUAGE):
        return False
    return True


def _looks_like_raw_knowledge(reply: str) -> bool:
    lowered = reply.lower()
    blocked = ("overview", "exploration", "beginner tips", "elden ring faq", "markdown", "json", "source:")
    return any(token in lowered for token in blocked)
