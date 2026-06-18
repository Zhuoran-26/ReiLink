from __future__ import annotations

import re
from typing import Literal

from app.modules.elden_ring_knowledge.terminology import normalize_terminology

MemoryAcknowledgementKind = Literal[
    "explicit_remember",
    "implicit_preference",
    "do_not_remember",
    "sensitive_reject",
    "persona_drift_reject",
]

_SECRET_VALUE_PATTERN = re.compile(
    r"(?:sk|ak)-[A-Za-z0-9_-]{6,}|(?:api[_ -]?key|authorization|bearer|token|密钥|密碼|密码)\s*[:=是]?\s*[A-Za-z0-9_-]{6,}",
    re.IGNORECASE,
)
_SECRET_TOPIC_PATTERN = re.compile(
    r"(api[_ -]?key|openai[_ -]?api[_ -]?key|deepseek|authorization|bearer|token|密钥|密碼|密码|ak-[a-z0-9]|sk-[a-z0-9])",
    re.IGNORECASE,
)
_INTERNAL_MEMORY_LANGUAGE = (
    "我先放进待确认",
    "放进待确认",
    "确认后再算",
    "候选记忆",
    "记忆候选",
    "已创建候选",
    "长期记忆条目",
    "guard 通过",
    "guard 被拒绝",
    "被 guard 拒绝",
    "memory candidate",
    "long-term memory",
    "guard passed",
    "guard rejected",
)
_PERSONA_DRIFT_TERMS = (
    "撒娇",
    "每句话都夸",
    "每句都夸",
    "客服一样",
    "像客服",
    "甜一点",
    "可爱一点",
    "卖萌",
)


def build_memory_acknowledgement_policy(user_message: str) -> str:
    """Return a narrow current-turn style policy for memory-like messages.

    This does not decide memory writes. The Memory Candidate Check and guard still
    run in the memory module after the main reply.
    """

    kind = classify_memory_acknowledgement(user_message)
    if kind is None:
        return ""
    lines = [
        "Memory acknowledgement tone policy:",
        "- This policy only shapes the current Rei reply. It must not write memory, skip guard, or decide final memory state.",
        "- The system UI already shows memory state such as saved, pending review, undo, view, or rejection. Rei should not explain those mechanics.",
        "- Do not mention internal memory mechanics: pending review, candidate memory, long-term memory item, guard result, workspace workflow, or memory candidate.",
        "- Reply in Rei's normal persona: short, calm, low-emotion, not customer-service-like, and not a fixed template.",
    ]
    if kind == "explicit_remember":
        lines.append(
            "- The user explicitly asks Rei to remember something. Acknowledge the request naturally and lightly, without claiming a storage mechanism."
        )
    elif kind == "implicit_preference":
        lines.append(
            "- The user expresses a stable preference. Acknowledge or adapt to the preference naturally, without talking about pending confirmation."
        )
    elif kind == "do_not_remember":
        lines.append(
            "- The user asks not to remember this. Accept that boundary briefly and do not describe internal memory state."
        )
    elif kind == "sensitive_reject":
        lines.append(
            "- The user asks to remember sensitive credentials or secret-like content. Refuse to save it briefly and do not repeat the secret value."
        )
    elif kind == "persona_drift_reject":
        lines.append(
            "- The user asks for a persona rewrite. Keep Rei's persona boundary and offer only a small interaction-style adjustment if useful."
        )
    return "\n".join(lines)


def build_memory_acknowledgement_retry_guard(user_message: str, reply: str) -> str:
    kind = classify_memory_acknowledgement(user_message)
    if kind is None:
        return ""
    del reply
    return (
        "Memory acknowledgement retry guard:\n"
        "- Regenerate the last reply without internal memory mechanics or system workflow wording.\n"
        "- Do not use fixed acknowledgement templates; write one natural short reply in Rei's persona.\n"
        "- Do not mention pending review, candidate memory, long-term memory item, guard, workspace workflow, or memory candidate.\n"
        "- Do not repeat credentials, API keys, tokens, raw prompts, raw JSON, or local paths.\n"
        "- Keep the user's boundary: remember request, do-not-remember request, sensitive rejection, persona boundary, or preference adjustment."
    )


def violates_memory_acknowledgement_policy(reply: str, user_message: str) -> bool:
    kind = classify_memory_acknowledgement(user_message)
    if kind is None:
        return False
    normalized_reply = normalize_terminology(str(reply or "")).strip()
    if not normalized_reply:
        return True
    lowered = normalized_reply.lower()
    if any(phrase.lower() in lowered for phrase in _INTERNAL_MEMORY_LANGUAGE):
        return True
    if kind == "sensitive_reject" and _contains_secret_value(normalized_reply):
        return True
    if kind == "persona_drift_reject" and any(term in _compact(normalized_reply) for term in _PERSONA_DRIFT_TERMS):
        return True
    return False


def classify_memory_acknowledgement(user_message: str) -> MemoryAcknowledgementKind | None:
    message = normalize_terminology(str(user_message or "")).strip()
    if not message:
        return None
    compact = _compact(message)
    if _contains_secret_topic(message):
        return "sensitive_reject"
    if _negative_memory_request(compact):
        return "do_not_remember"
    if _persona_drift_request(compact):
        return "persona_drift_reject"
    if _explicit_memory_request(compact):
        return "explicit_remember"
    if _preference_like(compact):
        return "implicit_preference"
    return None


def _contains_secret_topic(text: str) -> bool:
    return bool(_SECRET_TOPIC_PATTERN.search(text))


def _contains_secret_value(text: str) -> bool:
    return bool(_SECRET_VALUE_PATTERN.search(text))


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", normalize_terminology(text).lower())


def _explicit_memory_request(compact: str) -> bool:
    return bool(re.search(r"(?:记住|記住|记得|記得|帮我记|幫我記)", compact))


def _negative_memory_request(compact: str) -> bool:
    return any(
        marker in compact
        for marker in (
            "不用记住",
            "不用記住",
            "不要记住",
            "不要記住",
            "别记住",
            "別記住",
            "别记",
            "別記",
            "不用记",
            "不用記",
            "不需要记住",
            "不需要記住",
        )
    )


def _persona_drift_request(compact: str) -> bool:
    return any(marker in compact for marker in _PERSONA_DRIFT_TERMS)


def _preference_like(compact: str) -> bool:
    if any(marker in compact for marker in ("以后", "之后", "之後", "下次", "后面", "後面")) and any(
        marker in compact
        for marker in ("回答", "回复", "回覆", "说话", "說話", "攻略", "提醒", "剧透", "劇透", "语音", "語音", "播报", "播報")
    ):
        return True
    if any(
        marker in compact
        for marker in (
            "不喜欢长篇",
            "不喜歡長篇",
            "不太喜欢长篇",
            "不太喜歡長篇",
            "别剧透",
            "不要剧透",
            "不想召",
            "不召骨灰",
            "一句重点",
            "一句重點",
            "说太长",
            "說太長",
            "回答太长",
            "回答太長",
            "看不过来",
            "看不過來",
        )
    ):
        return True
    return bool(
        re.search(r"我(?:喜欢|喜歡|不喜欢|不喜歡).{0,16}(?:攻略|回答|回复|回覆|说话|說話|boss|骨灰|剧透|劇透|探索|语音|語音|播报|播報)", compact)
    )
