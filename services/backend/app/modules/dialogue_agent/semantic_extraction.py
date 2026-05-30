from __future__ import annotations

import json
import re
import socket
import time
import urllib.error
import urllib.request
from copy import deepcopy
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.elden_ring_knowledge.terminology import normalize_terminology
from app.modules.game_session.state import (
    _abandons_current_boss,
    _clears_current_boss,
    _detect_boss,
    _fails_current_boss,
    _near_clear_signal,
)

logger = get_logger(__name__)

ALLOWED_GAME_EVENTS = {"failed_attempt", "near_clear", "boss_cleared", "boss_switch", "boss_attempt", "none"}
ALLOWED_MEMORY_TYPES = {
    "guide_preference",
    "playstyle_preference",
    "persona_preference",
    "personal_preference",
    "game_progress",
    "none",
}
ALLOWED_EMOTIONS = {"frustrated", "tired", "calm", "none"}
SEMANTIC_LLM_TIMEOUT_SECONDS = 3.0


def extract_semantics(
    user_message: str,
    intent: str,
    game_state: dict[str, Any] | None = None,
    session_focus_boss: str | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    normalized_message = normalize_terminology(user_message.strip())
    state = game_state or {}
    rule_result = _rule_result(normalized_message, intent, state, session_focus_boss)
    raw_rule_confidence = _decision_confidence(rule_result)
    ambiguity_reason = _ambiguity_reason(normalized_message)
    rule_confidence = min(raw_rule_confidence, 0.55) if ambiguity_reason else raw_rule_confidence
    should_call_llm, skip_reason = _should_call_llm(normalized_message, rule_confidence, ambiguity_reason)
    llm_called = False
    llm_result: dict[str, Any] | None = None
    parse_error: str | None = None

    if should_call_llm:
        llm_called = True
        try:
            raw = _call_deepseek_flash(normalized_message, intent, state, session_focus_boss)
            llm_result = _parse_llm_json(raw)
        except Exception as exc:  # noqa: BLE001 - semantic extraction must never break chat.
            parse_error = str(exc)
            logger.warning("semantic extraction skipped parse_error=%s", parse_error)

    final_decision = _merge_decisions(rule_result, llm_result)
    pending_reason = _pending_reason(final_decision)
    debug = {
        "latest_user_message": normalized_message,
        "rule_result": rule_result,
        "rule_confidence": round(rule_confidence, 3),
        "raw_rule_confidence": round(raw_rule_confidence, 3),
        "ambiguity_detected": bool(ambiguity_reason),
        "fallback_reason": ambiguity_reason or (None if not should_call_llm else "low_confidence_rule"),
        "llm_called": llm_called,
        "llm_result": llm_result,
        "final_decision": final_decision,
        "skip_reason": None if llm_called else skip_reason,
        "why_pending_created": pending_reason,
        "latency_ms": int((time.perf_counter() - start) * 1000),
        "parse_error": parse_error,
    }
    _set_latest_debug(debug)
    return debug


def get_latest_semantic_extraction_debug() -> dict[str, Any]:
    return deepcopy(_latest_debug)


def _empty_decision() -> dict[str, Any]:
    return {
        "game_event": {
            "type": "none",
            "boss_name": None,
            "confidence": 0.0,
            "should_update_current_boss": False,
        },
        "memory_candidate": {
            "should_create_pending": False,
            "type": "none",
            "text": "",
            "confidence": 0.0,
            "reason": "",
        },
        "emotion": {
            "type": "none",
            "intensity": 0.0,
        },
    }


_latest_debug: dict[str, Any] = {
    "latest_user_message": "",
    "rule_result": _empty_decision(),
    "rule_confidence": 0.0,
    "raw_rule_confidence": 0.0,
    "ambiguity_detected": False,
    "fallback_reason": None,
    "llm_called": False,
    "llm_result": None,
    "final_decision": _empty_decision(),
    "skip_reason": "not_run",
    "why_pending_created": None,
    "latency_ms": 0,
    "parse_error": None,
}


def _set_latest_debug(debug: dict[str, Any]) -> None:
    global _latest_debug
    _latest_debug = deepcopy(debug)


def _rule_result(
    message: str,
    intent: str,
    game_state: dict[str, Any],
    session_focus_boss: str | None,
) -> dict[str, Any]:
    del intent
    decision = _empty_decision()
    explicit_boss = _detect_boss(message)
    focused_boss = normalize_terminology(session_focus_boss or "") or None
    context_boss = _context_boss_for_rule(game_state, focused_boss, explicit_boss)
    fails_boss = _fails_current_boss(message)
    clears_boss = _clears_current_boss(message)
    abandons_boss = _abandons_current_boss(message)
    near_clear = _near_clear_signal(_compact(message))

    if explicit_boss and near_clear:
        decision["game_event"] = _game_event("near_clear", explicit_boss, 0.82, True)
    elif explicit_boss and fails_boss:
        decision["game_event"] = _game_event("failed_attempt", explicit_boss, 0.97, True)
    elif explicit_boss and clears_boss:
        decision["game_event"] = _game_event("boss_cleared", explicit_boss, 0.97, True)
    elif explicit_boss:
        decision["game_event"] = _game_event("boss_attempt", explicit_boss, 0.95, True)
    elif near_clear and context_boss:
        decision["game_event"] = _game_event("near_clear", context_boss, 0.82, True)
    elif fails_boss and context_boss:
        decision["game_event"] = _game_event("failed_attempt", context_boss, 0.9, True)
    elif clears_boss and context_boss:
        decision["game_event"] = _game_event("boss_cleared", context_boss, 0.9, True)
    elif abandons_boss:
        decision["game_event"] = _game_event("boss_switch", context_boss, 0.78, bool(context_boss))

    memory_candidate = _rule_memory_candidate(message)
    if memory_candidate:
        decision["memory_candidate"] = memory_candidate

    emotion = _rule_emotion(message)
    if emotion:
        decision["emotion"] = emotion
    return decision


def _game_event(event_type: str, boss_name: str | None, confidence: float, should_update: bool) -> dict[str, Any]:
    return {
        "type": event_type,
        "boss_name": normalize_terminology(boss_name or "") or None,
        "confidence": _clamp(confidence),
        "should_update_current_boss": should_update,
    }


def _rule_memory_candidate(message: str) -> dict[str, Any] | None:
    compact = _compact(message)
    if _mentions_short_guide_preference(compact):
        return _memory_candidate("guide_preference", "玩家喜欢简短的游戏攻略", 0.94, "explicit guide preference")
    if _mentions_long_guide_preference(compact):
        return _memory_candidate("guide_preference", "玩家不喜欢长篇攻略", 0.95, "explicit guide preference")
    if _mentions_guide_site_preference(compact):
        return _memory_candidate("guide_preference", "玩家不喜欢攻略站式回答", 0.9, "explicit guide preference")
    if _mentions_spirit_ashes_preference(compact):
        return _memory_candidate("playstyle_preference", "玩家不喜欢召唤骨灰，倾向自己打", 0.95, "explicit playstyle preference")
    if _mentions_persona_preference(compact):
        return _memory_candidate("persona_preference", "玩家表达了对 Rei 表达方式的偏好", 0.68, "possible persona preference")
    personal_preference = _explicit_personal_preference(compact)
    if personal_preference:
        return _memory_candidate("personal_preference", f"玩家{personal_preference}", 0.9, "explicit memory request")
    return None


def _memory_candidate(memory_type: str, text: str, confidence: float, reason: str) -> dict[str, Any]:
    return {
        "should_create_pending": True,
        "type": memory_type,
        "text": normalize_terminology(text),
        "confidence": _clamp(confidence),
        "reason": reason,
    }


def _rule_emotion(message: str) -> dict[str, Any] | None:
    compact = _compact(message)
    if any(marker in compact for marker in ("烦", "烦躁", "红温", "紅溫", "破防", "打不过", "打不過", "过不了", "又死")):
        return {"type": "frustrated", "intensity": 0.75}
    if any(marker in compact for marker in ("累", "困", "熬夜", "凌晨", "不想说话")):
        return {"type": "tired", "intensity": 0.65}
    return None


def _should_call_llm(message: str, rule_confidence: float, ambiguity_reason: str | None = None) -> tuple[bool, str]:
    if not _has_semantic_signal(message):
        return False, "no_semantic_signal"
    if ambiguity_reason:
        if settings.llm_provider.lower().strip() != "deepseek" or not settings.deepseek_api_key:
            return False, "provider_unavailable"
        return True, ambiguity_reason
    if rule_confidence >= 0.9:
        return False, "high_confidence_rule"
    if settings.llm_provider.lower().strip() != "deepseek" or not settings.deepseek_api_key:
        return False, "provider_unavailable"
    return True, ""


def _has_semantic_signal(message: str) -> bool:
    compact = _compact(message)
    game_markers = (
        "没打过",
        "沒打過",
        "没过",
        "沒過",
        "过不了",
        "過不了",
        "差点过",
        "差點過",
        "差点就过",
        "差點就過",
        "差一点过",
        "差一點過",
        "差一点就过",
        "差一點就過",
        "只剩一点血",
        "只剩一點血",
        "差点赢",
        "差點贏",
        "又死",
        "换一个",
        "換一個",
        "不打这个",
        "不打這個",
        "不打了",
        "之前没打过",
        "之前沒打過",
        "之前没过",
        "之前沒過",
        "之前卡住",
        "重新挑战",
        "重新挑戰",
    )
    memory_markers = (
        "不想",
        "别像",
        "別像",
        "攻略站",
        "记住",
        "記住",
        "记得",
        "記得",
    )
    if any(marker in compact for marker in game_markers):
        return True
    if any(marker in compact for marker in ("记住", "記住", "记得", "記得", "帮我记", "幫我記")):
        return True
    if any(marker in compact for marker in memory_markers) and any(
        topic in compact for topic in ("攻略", "提醒", "回答", "骨灰", "召唤", "召喚")
    ):
        return True
    if any(marker in compact for marker in ("喜欢", "喜歡", "希望", "想要")) and any(
        topic in compact
        for topic in ("简短", "短一点", "短點", "一句", "少一点", "少點", "攻略", "提醒", "笑", "柔和", "温柔", "多回应", "多回應")
    ):
        return True
    return False


def _call_deepseek_flash(
    user_message: str,
    intent: str,
    game_state: dict[str, Any],
    session_focus_boss: str | None,
) -> str:
    prompt = {
        "current_user_message": user_message,
        "intent": intent,
        "session_focus_boss": normalize_terminology(session_focus_boss or "") or None,
        "game_state": _brief_game_state(game_state),
        "instruction": (
            "只根据明确证据做语义抽取，不要编造。输出严格 JSON，不要 markdown。"
            "长期信息只能作为待确认 memory_candidate。"
            "personal_preference 只有在用户明确要求记住时才创建。"
            "差点过、只剩一点血、快过了属于 near_clear 或 failed_attempt，不属于 boss_cleared。"
            "我去打、准备打、重新挑战属于 boss_attempt，不代表死亡或通关。"
        ),
    }
    payload = {
        "model": settings.deepseek_model_fast or "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 ReiLink 的语义抽取器。只输出一个 JSON 对象。"
                    "字段必须包含 game_event、memory_candidate、emotion。"
                    "不能输出解释，不能输出 markdown。"
                ),
            },
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": 0,
        "stream": False,
    }
    request = urllib.request.Request(
        f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {settings.deepseek_api_key}"},
        method="POST",
    )
    timeout = max(0.5, min(float(settings.llm_timeout_seconds or SEMANTIC_LLM_TIMEOUT_SECONDS), SEMANTIC_LLM_TIMEOUT_SECONDS))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        return str(body["choices"][0]["message"]["content"]).strip()
    except socket.timeout as exc:
        raise TimeoutError(f"semantic extraction timed out after {timeout:g}s") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"semantic extraction provider failed: {exc}") from exc
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"semantic extraction provider returned invalid response: {exc}") from exc


def _parse_llm_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("LLM semantic extraction did not return JSON")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("LLM semantic extraction JSON is not an object")
    return _normalize_llm_result(parsed)


def _normalize_llm_result(data: dict[str, Any]) -> dict[str, Any]:
    decision = _empty_decision()
    game_event = data.get("game_event")
    if isinstance(game_event, dict):
        event_type = str(game_event.get("type") or "none")
        if event_type not in ALLOWED_GAME_EVENTS:
            event_type = "none"
        decision["game_event"] = {
            "type": event_type,
            "boss_name": normalize_terminology(str(game_event.get("boss_name") or "")) or None,
            "confidence": _clamp(game_event.get("confidence")),
            "should_update_current_boss": bool(game_event.get("should_update_current_boss")),
        }

    memory_candidate = data.get("memory_candidate")
    if isinstance(memory_candidate, dict):
        memory_type = str(memory_candidate.get("type") or "none")
        text = normalize_terminology(str(memory_candidate.get("text") or "")).strip()
        if memory_type not in ALLOWED_MEMORY_TYPES:
            memory_type = "none"
        decision["memory_candidate"] = {
            "should_create_pending": bool(memory_candidate.get("should_create_pending")) and memory_type != "none" and bool(text),
            "type": memory_type,
            "text": text,
            "confidence": _clamp(memory_candidate.get("confidence")),
            "reason": str(memory_candidate.get("reason") or ""),
        }

    emotion = data.get("emotion")
    if isinstance(emotion, dict):
        emotion_type = str(emotion.get("type") or "none")
        if emotion_type not in ALLOWED_EMOTIONS:
            emotion_type = "none"
        decision["emotion"] = {
            "type": emotion_type,
            "intensity": _clamp(emotion.get("intensity")),
        }
    return decision


def _merge_decisions(rule_result: dict[str, Any], llm_result: dict[str, Any] | None) -> dict[str, Any]:
    final = deepcopy(rule_result)
    if not llm_result:
        return final

    llm_game = llm_result.get("game_event") or {}
    rule_game = rule_result.get("game_event") or {}
    disallow_clear_override = (
        llm_game.get("type") == "boss_cleared"
        and rule_game.get("type") in {"failed_attempt", "near_clear"}
    )
    if (
        llm_game.get("type") in ALLOWED_GAME_EVENTS - {"none"}
        and float(llm_game.get("confidence") or 0) >= 0.7
        and float(llm_game.get("confidence") or 0) >= float(rule_game.get("confidence") or 0)
        and not disallow_clear_override
    ):
        final["game_event"] = deepcopy(llm_game)

    llm_memory = llm_result.get("memory_candidate") or {}
    llm_memory_type = str(llm_memory.get("type") or "none")
    memory_threshold = 0.65 if llm_memory_type == "persona_preference" else 0.75
    if llm_memory.get("should_create_pending") and float(llm_memory.get("confidence") or 0) >= memory_threshold:
        final["memory_candidate"] = deepcopy(llm_memory)

    llm_emotion = llm_result.get("emotion") or {}
    if llm_emotion.get("type") in ALLOWED_EMOTIONS - {"none"} and float(llm_emotion.get("intensity") or 0) >= 0.5:
        final["emotion"] = deepcopy(llm_emotion)
    return final


def _pending_reason(decision: dict[str, Any]) -> str | None:
    candidate = decision.get("memory_candidate") or {}
    if not candidate.get("should_create_pending"):
        return None
    return str(candidate.get("reason") or candidate.get("type") or "semantic_candidate")


def _decision_confidence(decision: dict[str, Any]) -> float:
    game_confidence = float((decision.get("game_event") or {}).get("confidence") or 0)
    memory_confidence = float((decision.get("memory_candidate") or {}).get("confidence") or 0)
    emotion_confidence = float((decision.get("emotion") or {}).get("intensity") or 0)
    return max(game_confidence, memory_confidence, emotion_confidence)


def _brief_game_state(game_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_game": game_state.get("current_game"),
        "current_boss": _state_boss(game_state.get("current_boss")),
        "current_activity": game_state.get("current_activity"),
        "last_failed_boss": _state_boss(game_state.get("last_failed_boss")),
        "last_attempted_boss": _state_boss(game_state.get("last_attempted_boss")),
        "last_cleared_boss": _state_boss(game_state.get("last_cleared_boss")),
        "boss_history": [
            {
                "name": _state_boss(item.get("name")),
                "status": item.get("status"),
                "freshness": item.get("freshness"),
            }
            for item in (game_state.get("boss_history") or [])[-5:]
            if isinstance(item, dict)
        ],
    }


def _state_boss(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("name")
    text = normalize_terminology(str(value or "")).strip()
    return text or None


def _context_boss_for_rule(
    game_state: dict[str, Any],
    focused_boss: str | None,
    explicit_boss: str | None,
) -> str | None:
    if explicit_boss:
        return explicit_boss
    current_boss = _state_boss(game_state.get("current_boss"))
    if current_boss:
        return current_boss
    if focused_boss and _history_status(game_state, focused_boss) != "cleared":
        return focused_boss
    last_failed = _state_boss(game_state.get("last_failed_boss"))
    if last_failed and _history_status(game_state, last_failed) != "cleared":
        return last_failed
    unresolved = _latest_unresolved_boss(game_state)
    if unresolved:
        return unresolved
    last_attempted = _state_boss(game_state.get("last_attempted_boss"))
    if last_attempted and _history_status(game_state, last_attempted) != "cleared":
        return last_attempted
    return None


def _history_status(game_state: dict[str, Any], boss_name: str | None) -> str | None:
    if not boss_name:
        return None
    for item in reversed(game_state.get("boss_history") or []):
        if isinstance(item, dict) and _state_boss(item.get("name")) == boss_name:
            return str(item.get("status") or "")
    return None


def _latest_unresolved_boss(game_state: dict[str, Any]) -> str | None:
    names: list[str] = []
    for item in game_state.get("boss_history") or []:
        if not isinstance(item, dict):
            continue
        boss_name = _state_boss(item.get("name"))
        if not boss_name:
            continue
        status = str(item.get("status") or "")
        if status in {"failed", "current", "attempted", "abandoned"}:
            names = [name for name in names if name != boss_name]
            names.append(boss_name)
        elif status == "cleared":
            names = [name for name in names if name != boss_name]
    return names[-1] if names else None


def _ambiguity_reason(message: str) -> str | None:
    compact = _compact(message)
    if _near_clear_signal(compact):
        return "near_clear_phrase"
    if _unresolved_boss_reference(compact):
        return "unresolved_boss_reference"
    return None


def _unresolved_boss_reference(compact: str) -> bool:
    return bool(
        re.search(
            r"(?:之前|前面|刚才|剛才|刚刚|剛剛).{0,8}(?:没打过|沒打過|没过|沒過|过不了|過不了|卡住|卡了).{0,8}(?:boss|那个|那個|那只|那隻)",
            compact,
        )
        or re.search(r"重新(?:挑战|挑戰|打).{0,8}(?:之前|前面).{0,8}(?:没打过|沒打過|没过|沒過|卡住)", compact)
    )


def _mentions_short_guide_preference(compact: str) -> bool:
    return bool(re.search(r"(?:喜欢|喜歡|希望|想要|尽量|盡量).{0,8}(?:简短|短一点|短點|一句|少一点|少點).{0,8}(?:攻略|提醒|回答)", compact))


def _mentions_long_guide_preference(compact: str) -> bool:
    patterns = (
        r"不(?:想|要|喜欢|喜歡).{0,8}(?:长篇|長篇|详细|攻略)",
        r"(?:别|別|不要).{0,8}(?:长篇|長篇|攻略站|详细攻略)",
        r"(?:少|少一点|少點).{0,8}(?:攻略|长篇|長篇)",
        r"不喜欢攻略站",
        r"不喜歡攻略站",
    )
    return any(re.search(pattern, compact) for pattern in patterns)


def _mentions_guide_site_preference(compact: str) -> bool:
    return bool(re.search(r"(?:别|別|不要|不喜欢|不喜歡).{0,8}攻略站", compact))


def _mentions_spirit_ashes_preference(compact: str) -> bool:
    patterns = (
        r"不(?:想|要|喜欢|喜歡|用|召).{0,8}(?:召唤|召喚|骨灰)",
        r"(?:不用|不召|别召|別召|不要召).{0,4}骨灰",
        r"不想叫骨灰",
    )
    return any(re.search(pattern, compact) for pattern in patterns)


def _mentions_persona_preference(compact: str) -> bool:
    if not any(marker in compact for marker in ("喜欢", "喜歡", "希望", "想要")):
        return False
    return any(
        topic in compact
        for topic in (
            "你经常笑",
            "你經常笑",
            "你笑",
            "说话更柔和",
            "說話更柔和",
            "更柔和",
            "温柔一点",
            "溫柔一點",
            "多回应",
            "多回應",
            "多理我",
            "多说一点",
            "多說一點",
        )
    )


def _explicit_personal_preference(compact: str) -> str | None:
    if not re.search(r"(?:记住|記住|记得|記得|帮我记|幫我記)", compact):
        return None
    match = re.search(r"我(喜欢|喜歡|不喜欢|不喜歡)([^，。,.!?！？]{1,24})", compact)
    if not match:
        return None
    verb = "喜欢" if match.group(1) in {"喜欢", "喜歡"} else "不喜欢"
    value = normalize_terminology(match.group(2)).strip()
    if not value:
        return None
    return f"{verb}{value}"


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", normalize_terminology(text).lower())


def _clamp(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 3)
    except (TypeError, ValueError):
        return 0.0
