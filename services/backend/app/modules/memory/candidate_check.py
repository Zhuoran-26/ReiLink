from __future__ import annotations

import json
import re
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.elden_ring_knowledge.terminology import normalize_terminology

logger = get_logger(__name__)

MemoryCheckAction = Literal["auto_save", "pending", "reject", "none"]

MEMORY_CHECK_TYPES = {
    "gameplay_preference",
    "interaction_preference",
    "emotional_pattern",
    "accessibility_preference",
    "unknown",
    "none",
}
TYPE_ALIASES = {
    "guide_preference": "interaction_preference",
    "playstyle_preference": "gameplay_preference",
    "game_preference": "gameplay_preference",
    "persona_preference": "interaction_preference",
    "personal_preference": "unknown",
    "preference": "unknown",
}
ACTION_ALIASES = {
    "explicit_auto_save": "auto_save",
    "autosave": "auto_save",
    "save": "auto_save",
    "candidate": "pending",
    "confirm": "pending",
    "requires_confirmation": "pending",
    "block": "reject",
    "ignore": "none",
    "no_op": "none",
}
SENSITIVE_PATTERN = re.compile(
    r"(api[_ -]?key|openai[_ -]?api[_ -]?key|deepseek|authorization|bearer|token|密钥|密碼|密码|ak-[a-z0-9]|sk-[a-z0-9])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MemoryCandidateCheck:
    should_create: bool = False
    suggested_action: MemoryCheckAction = "none"
    memory_type: str = "none"
    safe_summary: str = ""
    confidence: float = 0.0
    reason: str = "no_memory_signal"
    source: str = "prefilter"
    explicit_request: bool = False
    provider_status: str = "not_run"

    def as_evidence(self) -> dict[str, str]:
        return {
            "memory_check_source": self.source,
            "memory_check_reason": self.reason,
            "memory_check_status": self.provider_status,
        }


def check_memory_candidate(
    user_message: str,
    *,
    input_source: str = "text",
    game_state_summary: dict[str, Any] | None = None,
) -> MemoryCandidateCheck:
    message = normalize_terminology(user_message.strip())
    if not message:
        return MemoryCandidateCheck(reason="empty_input")
    compact = _compact(message)
    explicit = _explicit_memory_request(compact)
    if _negative_memory_request(compact):
        return MemoryCandidateCheck(
            suggested_action="reject",
            reason="do_not_remember",
            source="guard_prefilter",
            explicit_request=explicit,
            provider_status="blocked_before_llm",
        )
    if _contains_sensitive_text(message):
        return MemoryCandidateCheck(
            suggested_action="reject",
            reason="sensitive_secret_blocked",
            source="guard_prefilter",
            explicit_request=explicit,
            provider_status="blocked_before_llm",
        )
    if _persona_drift_request(compact):
        return MemoryCandidateCheck(
            suggested_action="reject",
            reason="persona_drift_blocked",
            source="guard_prefilter",
            explicit_request=explicit,
            provider_status="blocked_before_llm",
        )
    if not _should_run_memory_check(compact):
        return MemoryCandidateCheck(reason="prefilter_no_memory_signal", explicit_request=explicit)

    provider = _provider_config()
    if provider is None:
        return _deterministic_memory_check(message, input_source=input_source, explicit_request=explicit)

    started = time.perf_counter()
    try:
        raw = _call_memory_check_provider(provider, message, input_source=input_source, game_state_summary=game_state_summary or {})
        result = _parse_memory_check_response(raw, explicit_request=explicit)
        return MemoryCandidateCheck(
            should_create=result.should_create,
            suggested_action=result.suggested_action,
            memory_type=result.memory_type,
            safe_summary=result.safe_summary,
            confidence=result.confidence,
            reason=result.reason,
            source="llm_primary",
            explicit_request=explicit or result.explicit_request,
            provider_status="succeeded",
        )
    except Exception as exc:
        logger.warning(
            "memory candidate check fallback reason=%s latency_ms=%s",
            exc.__class__.__name__,
            int((time.perf_counter() - started) * 1000),
        )
        fallback = _deterministic_memory_check(message, input_source=input_source, explicit_request=explicit)
        return MemoryCandidateCheck(
            should_create=fallback.should_create,
            suggested_action=fallback.suggested_action,
            memory_type=fallback.memory_type,
            safe_summary=fallback.safe_summary,
            confidence=fallback.confidence,
            reason=f"llm_unavailable:{fallback.reason}",
            source="deterministic_fallback",
            explicit_request=fallback.explicit_request,
            provider_status="provider_error",
        )


def _provider_config() -> dict[str, str] | None:
    provider = settings.llm_provider.lower().strip()
    if provider == "deepseek" and settings.deepseek_api_key.strip():
        return {
            "provider": "deepseek",
            "api_key": settings.deepseek_api_key.strip(),
            "base_url": settings.deepseek_base_url,
            "model": settings.deepseek_model_fast or settings.deepseek_model or "deepseek-chat",
        }
    if provider in {"openai", "openai-compatible"} and settings.openai_api_key.strip():
        return {
            "provider": "openai",
            "api_key": settings.openai_api_key.strip(),
            "base_url": settings.openai_base_url,
            "model": settings.openai_model or "gpt-4o-mini",
        }
    return None


def _call_memory_check_provider(
    provider: dict[str, str],
    user_message: str,
    *,
    input_source: str,
    game_state_summary: dict[str, Any],
) -> str:
    prompt = {
        "task": "reilink_memory_candidate_check_v1_1",
        "input_source": input_source,
        "user_message": user_message,
        "game_state_summary": _safe_game_state_summary(game_state_summary),
        "allowed_types": sorted(MEMORY_CHECK_TYPES - {"none"}),
        "allowed_actions": ["auto_save", "pending", "reject", "none"],
        "format": {
            "should_create": False,
            "suggested_action": "none",
            "type": "none",
            "safe_summary": "",
            "confidence": 0.0,
            "explicit_request": False,
            "reason": "short_safe_reason",
        },
        "rules": [
            "Return only a JSON object.",
            "Decide if the user expressed a durable memory candidate.",
            "Explicit remember requests may suggest auto_save; implicit preferences must suggest pending.",
            "Session-only game events, one-off deaths, guide questions, and casual facts should be none.",
            "Do not save secrets, API keys, .env content, full local paths, raw prompts, raw JSON, or provider diagnostics.",
            "Do not turn persona-changing requests into memory.",
            "safe_summary must be short, user-visible Chinese, and should start with 玩家.",
        ],
    }
    payload = {
        "model": provider["model"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 ReiLink 的长期记忆候选判断器。只判断用户特定、长期有用、可撤销的记忆候选。"
                    "你不写入状态，只输出 JSON。"
                ),
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, separators=(",", ":"))},
        ],
        "temperature": 0.0,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{provider['base_url'].rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {provider['api_key']}"},
        method="POST",
    )
    timeout = max(4.0, min(float(settings.llm_timeout_seconds or 12.0), 12.0))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return str(body["choices"][0]["message"]["content"]).strip()
    except socket.timeout as exc:
        raise RuntimeError("memory check provider timeout") from exc
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"memory check provider http_{exc.code}") from exc
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError("memory check provider failed") from exc


def _parse_memory_check_response(raw: str, *, explicit_request: bool) -> MemoryCandidateCheck:
    data = _load_json_object(raw)
    action = _safe_action(data.get("suggested_action") or data.get("action"))
    memory_type = _safe_type(data.get("type") or data.get("memory_type"))
    confidence = _confidence(data.get("confidence") or data.get("conf"))
    summary = _safe_summary(data.get("safe_summary") or data.get("summary") or "")
    explicit = explicit_request or bool(data.get("explicit_request") or data.get("explicit"))
    reason = _safe_reason(data.get("reason") or "llm_primary")
    if action == "auto_save" and not explicit:
        action = "pending"
        reason = "implicit_candidate_downgraded_to_pending"
    if (
        action in {"pending", "auto_save"}
        and memory_type != "none"
        and summary
        and confidence >= (0.82 if explicit else 0.72)
        and not _contains_sensitive_text(summary)
        and not _persona_drift_request(_compact(summary))
    ):
        return MemoryCandidateCheck(
            should_create=True,
            suggested_action=action,
            memory_type=memory_type,
            safe_summary=summary,
            confidence=confidence,
            reason=reason,
            source="llm_primary",
            explicit_request=explicit,
            provider_status="succeeded",
        )
    if action == "reject":
        return MemoryCandidateCheck(
            suggested_action="reject",
            reason=reason,
            source="llm_primary",
            explicit_request=explicit,
            provider_status="succeeded",
        )
    return MemoryCandidateCheck(
        suggested_action="none",
        reason=reason or "llm_no_memory_candidate",
        source="llm_primary",
        explicit_request=explicit,
        provider_status="succeeded",
    )


def _deterministic_memory_check(
    message: str,
    *,
    input_source: str,
    explicit_request: bool,
) -> MemoryCandidateCheck:
    del input_source
    compact = _compact(message)
    action: MemoryCheckAction = "auto_save" if explicit_request else "pending"
    if _mentions_boss_exploration_preference(compact):
        return _candidate(
            action,
            "gameplay_preference",
            "玩家打 Boss 前喜欢先探索地图，不喜欢直接硬打",
            0.92,
            "deterministic_boss_exploration_preference",
            explicit_request,
        )
    if _mentions_long_guide_preference(compact):
        return _candidate(
            action,
            "interaction_preference",
            "玩家不喜欢长篇攻略",
            0.9,
            "deterministic_guide_length_preference",
            explicit_request,
        )
    if _mentions_short_reply_preference(compact):
        return _candidate(
            action,
            "interaction_preference",
            "玩家偏好简短回答和简短游戏提醒",
            0.88,
            "deterministic_short_reply_preference",
            explicit_request,
        )
    if _mentions_spirit_ashes_preference(compact):
        return _candidate(
            action,
            "gameplay_preference",
            "玩家不喜欢召唤骨灰，倾向自己打",
            0.9,
            "deterministic_playstyle_preference",
            explicit_request,
        )
    if _mentions_spoiler_preference(compact):
        return _candidate(
            action,
            "gameplay_preference",
            "玩家偏好避免剧透，除非主动询问",
            0.88,
            "deterministic_spoiler_preference",
            explicit_request,
        )
    if _mentions_accessibility_preference(compact):
        summary = "玩家偏好语音播报更短" if "短" in compact else "玩家偏好语音输出更慢"
        return _candidate(
            action,
            "accessibility_preference",
            summary,
            0.86,
            "deterministic_accessibility_preference",
            explicit_request,
        )
    personal = _explicit_personal_preference(compact)
    if personal:
        return _candidate(
            "auto_save",
            "unknown",
            f"玩家{personal}",
            0.88,
            "deterministic_explicit_personal_preference",
            True,
        )
    return MemoryCandidateCheck(
        suggested_action="none",
        reason="deterministic_no_memory_candidate",
        source="deterministic_fallback",
        explicit_request=explicit_request,
        provider_status="provider_unavailable",
    )


def _candidate(
    action: MemoryCheckAction,
    memory_type: str,
    summary: str,
    confidence: float,
    reason: str,
    explicit_request: bool,
) -> MemoryCandidateCheck:
    if action == "auto_save" and not explicit_request:
        action = "pending"
    return MemoryCandidateCheck(
        should_create=True,
        suggested_action=action,
        memory_type=memory_type,
        safe_summary=normalize_terminology(summary),
        confidence=confidence,
        reason=reason,
        source="deterministic_fallback",
        explicit_request=explicit_request,
        provider_status="provider_unavailable",
    )


def _load_json_object(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip().lstrip("\ufeff")
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("memory check response must be a JSON object")
    return parsed


def _safe_game_state_summary(value: dict[str, Any]) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    keys = ("current_game", "current_activity", "last_failed_boss", "last_attempted_boss", "last_cleared_boss")
    result: dict[str, str] = {}
    for key in keys:
        text = normalize_terminology(str(value.get(key) or "")).strip()
        if text and not _contains_sensitive_text(text):
            result[key] = text[:80]
    boss = value.get("current_boss")
    if isinstance(boss, dict):
        boss = boss.get("name")
    boss_text = normalize_terminology(str(boss or "")).strip()
    if boss_text and not _contains_sensitive_text(boss_text):
        result["current_boss"] = boss_text[:80]
    return result


def _should_run_memory_check(compact: str) -> bool:
    if _explicit_memory_request(compact):
        return True
    if any(marker in compact for marker in ("以后", "之後", "之后", "下次", "以后你", "后面", "後面")) and any(
        marker in compact
        for marker in ("回答", "回复", "回覆", "说话", "說話", "攻略", "提醒", "剧透", "劇透", "语音", "語音", "播报", "播報")
    ):
        return True
    if any(marker in compact for marker in ("不喜欢长篇", "不喜歡長篇", "不太喜欢长篇", "不太喜歡長篇", "别剧透", "不要剧透", "不想召", "不召骨灰")):
        return True
    if "一句重点" in compact or "一句重點" in compact:
        return True
    if any(marker in compact for marker in ("说太长", "說太長", "回答太长", "回答太長", "看不过来", "看不過來")):
        return True
    if ("boss" in compact or "Boss" in compact.lower()) and any(marker in compact for marker in ("喜欢先探索", "先探索", "探索地图", "直接硬打")):
        return True
    return bool(
        re.search(r"我(?:喜欢|喜歡|不喜欢|不喜歡).{0,16}(?:攻略|回答|回复|回覆|说话|說話|boss|骨灰|剧透|劇透|探索|语音|語音|播报|播報)", compact)
    )


def _safe_action(value: Any) -> MemoryCheckAction:
    text = str(value or "none").strip().lower()
    text = ACTION_ALIASES.get(text, text)
    if text in {"auto_save", "pending", "reject", "none"}:
        return text  # type: ignore[return-value]
    return "none"


def _safe_type(value: Any) -> str:
    text = str(value or "none").strip()
    text = TYPE_ALIASES.get(text, text)
    return text if text in MEMORY_CHECK_TYPES else "none"


def _confidence(value: Any) -> float:
    if isinstance(value, int | float):
        return max(0.0, min(float(value), 1.0))
    text = str(value or "").strip().lower()
    if text == "high":
        return 0.9
    if text == "medium":
        return 0.72
    if text == "low":
        return 0.35
    try:
        return max(0.0, min(float(text), 1.0))
    except ValueError:
        return 0.0


def _safe_summary(value: Any) -> str:
    text = normalize_terminology(str(value or "")).strip()
    text = re.sub(r"\s+", " ", text)[:96]
    if not text or _contains_sensitive_text(text):
        return ""
    if not text.startswith("玩家"):
        text = f"玩家{text}"
    return text.rstrip("。.!！")


def _safe_reason(value: Any) -> str:
    text = normalize_terminology(str(value or "")).strip()
    text = re.sub(r"[^A-Za-z0-9_\-\u4e00-\u9fff]", "_", text)
    return text[:80] or "memory_check"


def _contains_sensitive_text(text: str) -> bool:
    return bool(SENSITIVE_PATTERN.search(text))


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
    return any(
        marker in compact
        for marker in (
            "撒娇",
            "撒嬌",
            "每句话都夸",
            "每句話都誇",
            "客服一样",
            "客服一樣",
            "像客服",
            "甜一点",
            "甜一點",
            "可爱一点",
            "可愛一點",
            "卖萌",
            "賣萌",
        )
    )


def _mentions_short_reply_preference(compact: str) -> bool:
    return bool(
        re.search(r"(?:以后|之後|之后|后面|後面)?.{0,4}(?:回答|回复|回覆|说话|說話|攻略|提醒).{0,8}(?:短一点|短點|简短|簡短|少一点|少點)", compact)
        or re.search(r"(?:以后|之後|之后|后面|後面).{0,8}(?:短一点|短點|简短|簡短|少一点|少點).{0,6}(?:回答|回复|回覆|说话|說話|攻略|提醒)", compact)
        or re.search(r"(?:回答|回复|回覆|说话|說話|说|說).{0,6}(?:太长|太長|太多).{0,10}(?:看不过来|看不過來|读不过来|讀不過來)", compact)
    )


def _mentions_long_guide_preference(compact: str) -> bool:
    return any(
        re.search(pattern, compact)
        for pattern in (
            r"不(?:太)?(?:想|要|喜欢|喜歡).{0,8}(?:长篇|長篇|详细|攻略)",
            r"(?:别|不要).{0,8}(?:长篇|長篇|攻略站|详细攻略)",
            r"(?:少|少一点|少點).{0,8}(?:攻略|长篇|長篇)",
            r"不喜欢攻略站",
        )
    )


def _mentions_spirit_ashes_preference(compact: str) -> bool:
    return any(
        re.search(pattern, compact)
        for pattern in (
            r"不(?:想|要|喜欢|喜歡|用|召).{0,8}(?:召唤|召喚|骨灰)",
            r"(?:不用|不召|别召|不要召).{0,4}骨灰",
            r"不想叫骨灰",
        )
    )


def _mentions_boss_exploration_preference(compact: str) -> bool:
    has_boss_context = "boss" in compact or "打boss" in compact
    has_exploration = any(marker in compact for marker in ("先探索", "探索地图", "探索地圖", "先跑图", "先跑圖"))
    has_hard_push_dislike = any(marker in compact for marker in ("不喜欢直接硬打", "不喜歡直接硬打", "不想直接硬打", "不要直接硬打"))
    return has_boss_context and (has_exploration or has_hard_push_dislike)


def _mentions_spoiler_preference(compact: str) -> bool:
    return any(marker in compact for marker in ("别剧透", "別劇透", "不要剧透", "不要劇透", "不想被剧透", "不想被劇透")) or (
        "剧透" in compact and any(marker in compact for marker in ("除非我问", "除非我問", "我主动问", "我主動問"))
    )


def _mentions_accessibility_preference(compact: str) -> bool:
    return any(
        marker in compact
        for marker in (
            "语音短一点",
            "語音短一點",
            "播报短一点",
            "播報短一點",
            "朗读短一点",
            "朗讀短一點",
            "读慢一点",
            "讀慢一點",
            "说慢一点",
            "說慢一點",
        )
    )


def _explicit_personal_preference(compact: str) -> str | None:
    if not _explicit_memory_request(compact):
        return None
    match = re.search(r"我(喜欢|喜歡|不喜欢|不喜歡)([^，。,.!?！？]{1,24})", compact)
    if not match:
        return None
    verb = "喜欢" if match.group(1) in {"喜欢", "喜歡"} else "不喜欢"
    value = normalize_terminology(match.group(2)).strip()
    if not value:
        return None
    return f"{verb}{value}"
