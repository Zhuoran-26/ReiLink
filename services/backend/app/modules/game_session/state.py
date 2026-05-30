from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.modules.dialogue_agent.emotion import detect_user_emotion
from app.modules.dialogue_agent.session_focus import detect_boss_focus, is_elliptical_boss_reference
from app.modules.elden_ring_knowledge.terminology import normalize_mapping_values, normalize_terminology

FRESH_WINDOW = timedelta(hours=24)
WEAK_WINDOW = timedelta(hours=72)


@dataclass
class CurrentBoss:
    name: str
    updated_at: str
    confidence: float
    source: str
    mention_count: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "updated_at": self.updated_at,
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "mention_count": self.mention_count,
        }


@dataclass
class BossHistoryEntry:
    name: str
    status: str
    updated_at: str
    confidence: float
    source: str
    mention_count: int = 1
    last_activity: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "updated_at": self.updated_at,
            "confidence": round(self.confidence, 3),
            "source": self.source,
            "mention_count": self.mention_count,
            "last_activity": self.last_activity,
        }


@dataclass
class GameSessionState:
    current_game: str | None = None
    current_boss: CurrentBoss | None = None
    last_boss: str | None = None
    last_attempted_boss: str | None = None
    last_cleared_boss: str | None = None
    current_activity: str | None = None
    recent_game_topics: list[str] = field(default_factory=list)
    boss_history: list[BossHistoryEntry] = field(default_factory=list)
    frustration_count: int = 0
    death_count: int = 0
    last_user_intent: str | None = None
    last_game_intent: str | None = None
    last_updated_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "current_game": self.current_game,
            "current_boss": self.current_boss.as_dict() if self.current_boss else None,
            "last_boss": self.last_boss,
            "last_attempted_boss": self.last_attempted_boss,
            "last_cleared_boss": self.last_cleared_boss,
            "current_activity": self.current_activity,
            "recent_game_topics": self.recent_game_topics,
            "boss_history": [entry.as_dict() for entry in self.boss_history],
            "frustration_count": self.frustration_count,
            "death_count": self.death_count,
            "last_user_intent": self.last_user_intent,
            "last_game_intent": self.last_game_intent,
            "last_updated_at": self.last_updated_at,
        }


@dataclass(frozen=True)
class BossFreshness:
    age_hours: float | None
    freshness: str
    is_fresh: bool


class GameSessionStore:
    def __init__(self, state_path: Path | None = None) -> None:
        self.state_path = state_path or settings.game_session_state_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> GameSessionState:
        if not self.state_path.exists():
            return GameSessionState()
        data = json.loads(self.state_path.read_text(encoding="utf-8") or "{}")
        normalized = normalize_mapping_values(data)
        boss = _coerce_current_boss(normalized.get("current_boss"))
        boss_history = [
            entry
            for item in normalized.get("boss_history") or []
            if (entry := _coerce_history_entry(item)) is not None
        ]
        return GameSessionState(
            current_game=normalized.get("current_game"),
            current_boss=boss,
            last_boss=normalized.get("last_boss"),
            last_attempted_boss=normalized.get("last_attempted_boss"),
            last_cleared_boss=normalized.get("last_cleared_boss"),
            current_activity=normalized.get("current_activity"),
            recent_game_topics=list(normalized.get("recent_game_topics") or []),
            boss_history=boss_history[-12:],
            frustration_count=int(normalized.get("frustration_count") or 0),
            death_count=int(normalized.get("death_count") or 0),
            last_user_intent=normalized.get("last_user_intent"),
            last_game_intent=normalized.get("last_game_intent"),
            last_updated_at=normalized.get("last_updated_at"),
        )

    def save(self, state: GameSessionState) -> None:
        self.state_path.write_text(
            json.dumps(normalize_mapping_values(state.as_dict()), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def reset(self) -> GameSessionState:
        state = GameSessionState()
        self.save(state)
        return state

    def update_from_user_message(
        self,
        user_message: str,
        intent: str,
        game_status: dict[str, Any],
        timestamp: datetime,
        session_focus_boss: str | None = None,
        semantic_game_event: dict[str, Any] | None = None,
    ) -> GameSessionState:
        state = self.load()
        now = _ensure_aware(timestamp)
        explicit_boss = _detect_boss(user_message)
        focused_boss = normalize_terminology(session_focus_boss or "") or None
        has_elliptical_reference = is_elliptical_boss_reference(user_message)
        fails_boss = _fails_current_boss(user_message)
        clears_boss = _clears_current_boss(user_message)
        abandons_boss = _abandons_current_boss(user_message)
        semantic_event_type = _semantic_event_type(semantic_game_event)
        semantic_applied = False
        game_name = _detect_current_game(game_status, user_message, intent, explicit_boss or focused_boss)

        state.last_user_intent = intent
        state.last_updated_at = now.isoformat()
        if game_name:
            state.current_game = game_name

        if _has_death_signal(user_message):
            state.death_count += 1
        if _has_frustration_signal(user_message):
            state.frustration_count += 1

        if explicit_boss and fails_boss:
            _mark_boss_failed(state, explicit_boss, now, "current_message")
        elif explicit_boss and clears_boss:
            _clear_boss(state, explicit_boss, now, "current_message")
        elif explicit_boss:
            _set_current_boss(state, explicit_boss, now, "current_message", 0.95)
        elif fails_boss:
            failed_boss = _context_boss_for_failure(state, focused_boss, now)
            if failed_boss:
                source = "session_focus" if focused_boss and failed_boss == focused_boss else "current_context"
                _mark_boss_failed(state, failed_boss, now, source)
            else:
                state.current_activity = "boss_failed"
        elif clears_boss and state.current_boss:
            _clear_boss(state, state.current_boss.name, now, "current_context")
        elif _apply_semantic_game_event(state, semantic_game_event, focused_boss, now):
            semantic_applied = True
        elif abandons_boss and state.current_boss:
            _abandon_current_boss(state, now)
        elif abandons_boss:
            state.current_activity = "boss_switching"
        elif focused_boss and has_elliptical_reference:
            _set_current_boss(state, focused_boss, now, "session_focus", 0.85)
        elif has_elliptical_reference and state.current_boss:
            freshness = boss_freshness(state, now)
            if freshness.freshness in {"fresh", "weak"}:
                _set_current_boss(state, state.current_boss.name, now, "elliptical_reference", 0.75)
            else:
                state.current_activity = "unclear_boss_reference"
        elif _is_game_related(intent, user_message, explicit_boss or focused_boss):
            state.current_activity = _detect_activity(user_message, intent)

        game_intent = _derive_game_intent(
            user_message,
            intent,
            explicit_boss or focused_boss or (state.current_boss.name if state.current_boss else None),
            state.current_activity,
            fails_boss or (semantic_applied and semantic_event_type == "failed_attempt"),
            clears_boss or (semantic_applied and semantic_event_type == "boss_cleared"),
            abandons_boss or (semantic_applied and semantic_event_type == "boss_switch"),
        )
        if game_intent:
            state.last_game_intent = game_intent

        self.save(state)
        return state

    def build_prompt_summary(
        self,
        now: datetime | None = None,
        session_focus_boss: str | None = None,
    ) -> str:
        state = self.load()
        now = _ensure_aware(now or datetime.now(timezone.utc))
        session_focus_boss = normalize_terminology(session_focus_boss or "") or None
        pressure = _pressure_text(state)

        if session_focus_boss:
            if not state.current_boss and state.last_cleared_boss == session_focus_boss:
                return (
                    f"当前游戏状态：刚刚结束的 boss 是 {session_focus_boss}；"
                    "当前没有正在打的 boss。用户如果问刚刚在打什么，可以引用这个已结束状态。不要猜新的 boss。"
                )
            suffix = f"，{pressure}" if pressure else ""
            return f"当前游戏状态：当前会话焦点是 {session_focus_boss}{suffix}。短期会话焦点优先于长期记忆。"

        if state.current_boss:
            freshness = boss_freshness(state, now)
            if freshness.freshness == "fresh":
                suffix = f"，{pressure}" if pressure else ""
                return f"当前游戏状态：玩家最近在打 {state.current_boss.name}{suffix}，状态新鲜。"
            if freshness.freshness == "weak":
                return f"当前游戏状态：玩家 24-72 小时内提过 {state.current_boss.name}，不确定是否仍在打；引用前先确认。"
            return f"当前游戏状态：曾经提到 {state.current_boss.name}，但已超过 72 小时，不要主动当作当前 boss。"

        if state.current_game:
            if state.last_cleared_boss:
                return (
                    f"当前游戏状态：刚刚结束的 boss 是 {state.last_cleared_boss}；"
                    "当前没有正在打的 boss。用户如果问刚刚在打什么，可以引用这个已结束状态。不要猜新的 boss。"
                )
            if state.last_attempted_boss:
                return (
                    f"当前游戏状态：最近尝试过的 boss 是 {state.last_attempted_boss}；"
                    "当前没有明确正在打的 boss。引用前注意是否已经切换或结束。"
                )
            return f"当前游戏状态：最近在聊 {state.current_game}，暂无明确当前 boss。不要猜具体 boss。"
        return ""

    def debug_state(self, now: datetime | None = None) -> dict[str, Any]:
        state = self.load()
        now = _ensure_aware(now or datetime.now(timezone.utc))
        data = state.as_dict()
        freshness = boss_freshness(state, now)
        if data["current_boss"]:
            data["current_boss"] = {
                **data["current_boss"],
                "age_hours": freshness.age_hours,
                "is_fresh": freshness.is_fresh,
                "freshness": freshness.freshness,
            }
        data["boss_history"] = [_history_entry_debug(entry, now) for entry in state.boss_history]
        return data


def boss_freshness(state: GameSessionState, now: datetime | None = None) -> BossFreshness:
    now = _ensure_aware(now or datetime.now(timezone.utc))
    if not state.current_boss:
        return BossFreshness(None, "none", False)
    updated_at = _parse_timestamp(state.current_boss.updated_at)
    if not updated_at:
        return BossFreshness(None, "stale", False)
    age_hours = max((now - updated_at).total_seconds() / 3600, 0)
    if age_hours <= FRESH_WINDOW.total_seconds() / 3600:
        return BossFreshness(round(age_hours, 3), "fresh", True)
    if age_hours <= WEAK_WINDOW.total_seconds() / 3600:
        return BossFreshness(round(age_hours, 3), "weak", False)
    return BossFreshness(round(age_hours, 3), "stale", False)


def _history_entry_debug(entry: BossHistoryEntry, now: datetime) -> dict[str, Any]:
    data = entry.as_dict()
    updated_at = _parse_timestamp(entry.updated_at)
    if not updated_at:
        return {**data, "age_hours": None, "freshness": "stale"}
    age_hours = max((now - updated_at).total_seconds() / 3600, 0)
    if age_hours <= FRESH_WINDOW.total_seconds() / 3600:
        freshness = "fresh"
    elif age_hours <= WEAK_WINDOW.total_seconds() / 3600:
        freshness = "weak"
    else:
        freshness = "stale"
    return {**data, "age_hours": round(age_hours, 3), "freshness": freshness}


def _coerce_current_boss(value: Any) -> CurrentBoss | None:
    if not isinstance(value, dict) or not value.get("name"):
        return None
    return CurrentBoss(
        name=normalize_terminology(str(value["name"])),
        updated_at=str(value.get("updated_at") or ""),
        confidence=float(value.get("confidence") or 0),
        source=str(value.get("source") or "unknown"),
        mention_count=int(value.get("mention_count") or 1),
    )


def _coerce_history_entry(value: Any) -> BossHistoryEntry | None:
    if not isinstance(value, dict) or not value.get("name"):
        return None
    return BossHistoryEntry(
        name=normalize_terminology(str(value["name"])),
        status=str(value.get("status") or "mentioned"),
        updated_at=str(value.get("updated_at") or ""),
        confidence=float(value.get("confidence") or 0),
        source=str(value.get("source") or "unknown"),
        mention_count=int(value.get("mention_count") or 1),
        last_activity=value.get("last_activity"),
    )


def _detect_boss(message: str) -> str | None:
    boss = detect_boss_focus(message)
    return normalize_terminology(boss) if boss else None


def _detect_current_game(
    game_status: dict[str, Any],
    message: str,
    intent: str,
    boss: str | None,
) -> str | None:
    if game_status.get("game_name"):
        return str(game_status["game_name"])
    if game_status.get("game_id") == "elden_ring" or boss or intent.startswith("elden_ring"):
        return "Elden Ring"
    if any(word in message.lower() for word in ("艾尔登", "艾爾登", "elden ring", "交界地")):
        return "Elden Ring"
    return None


def _is_game_related(intent: str, message: str, boss: str | None) -> bool:
    return bool(
        boss
        or intent.startswith("elden_ring")
        or any(word in message.lower() for word in ("boss", "艾尔登", "艾爾登", "elden ring", "打不过", "打不過", "又死"))
    )


def _updated_boss(
    current: CurrentBoss | None,
    boss_name: str,
    timestamp: datetime,
    source: str,
    confidence: float,
) -> CurrentBoss:
    boss_name = normalize_terminology(boss_name)
    if current and current.name == boss_name:
        return CurrentBoss(
            name=boss_name,
            updated_at=timestamp.isoformat(),
            confidence=min(1.0, max(current.confidence, confidence) + 0.05),
            source=source,
            mention_count=current.mention_count + 1,
        )
    return CurrentBoss(
        name=boss_name,
        updated_at=timestamp.isoformat(),
        confidence=confidence,
        source=source,
        mention_count=1,
    )


def _set_current_boss(
    state: GameSessionState,
    boss_name: str,
    timestamp: datetime,
    source: str,
    confidence: float,
) -> None:
    boss_name = normalize_terminology(boss_name)
    if state.current_boss and state.current_boss.name != boss_name:
        _touch_history(
            state,
            state.current_boss.name,
            "attempted",
            timestamp,
            "previous_current",
            state.current_boss.confidence,
            "boss_attempt",
        )
    state.current_boss = _updated_boss(state.current_boss, boss_name, timestamp, source, confidence)
    state.current_activity = "boss_attempt"
    state.last_boss = boss_name
    state.last_attempted_boss = boss_name
    _append_topic(state, boss_name)
    _touch_history(state, boss_name, "current", timestamp, source, confidence, "boss_attempt")


def _clear_boss(state: GameSessionState, boss_name: str, timestamp: datetime, source: str) -> None:
    boss_name = normalize_terminology(boss_name)
    state.last_boss = boss_name
    state.last_attempted_boss = boss_name
    state.last_cleared_boss = boss_name
    state.current_boss = None
    state.current_activity = "boss_cleared"
    _append_topic(state, boss_name)
    _append_topic(state, f"{boss_name}已结束")
    _touch_history(state, boss_name, "cleared", timestamp, source, 1.0, "boss_cleared")


def _mark_boss_failed(
    state: GameSessionState,
    boss_name: str,
    timestamp: datetime,
    source: str,
    confidence: float = 0.85,
) -> None:
    boss_name = normalize_terminology(boss_name)
    if state.current_boss and state.current_boss.name != boss_name:
        _touch_history(
            state,
            state.current_boss.name,
            "attempted",
            timestamp,
            "previous_current",
            state.current_boss.confidence,
            "boss_attempt",
        )
    state.current_boss = _updated_boss(state.current_boss, boss_name, timestamp, source, confidence)
    state.current_activity = "boss_failed"
    state.last_boss = boss_name
    state.last_attempted_boss = boss_name
    if state.last_cleared_boss == boss_name:
        state.last_cleared_boss = None
    _append_topic(state, boss_name)
    _touch_history(state, boss_name, "failed", timestamp, source, confidence, "boss_failed")


def _abandon_current_boss(state: GameSessionState, timestamp: datetime) -> None:
    if not state.current_boss:
        return
    boss_name = state.current_boss.name
    state.last_boss = boss_name
    state.last_attempted_boss = boss_name
    state.current_boss = None
    state.current_activity = "boss_switching"
    _touch_history(state, boss_name, "abandoned", timestamp, "current_context", 0.6, "boss_switching")


def _touch_history(
    state: GameSessionState,
    boss_name: str,
    status: str,
    timestamp: datetime,
    source: str,
    confidence: float,
    activity: str | None,
) -> None:
    boss_name = normalize_terminology(boss_name)
    if not boss_name:
        return
    existing = next((entry for entry in state.boss_history if entry.name == boss_name), None)
    state.boss_history = [entry for entry in state.boss_history if entry.name != boss_name]
    mention_count = (existing.mention_count + 1) if existing else 1
    state.boss_history.append(
        BossHistoryEntry(
            name=boss_name,
            status=status,
            updated_at=timestamp.isoformat(),
            confidence=min(1.0, max(confidence, existing.confidence if existing else 0)),
            source=source,
            mention_count=mention_count,
            last_activity=activity,
        )
    )
    state.boss_history = state.boss_history[-12:]


def _context_boss_for_failure(
    state: GameSessionState,
    focused_boss: str | None,
    timestamp: datetime,
) -> str | None:
    if state.current_boss:
        return state.current_boss.name
    if focused_boss:
        return focused_boss
    for boss_name in (state.last_boss, state.last_attempted_boss, state.last_cleared_boss):
        if boss_name and _history_is_recent(state, boss_name, timestamp):
            return boss_name
    return None


def _semantic_event_type(event: dict[str, Any] | None) -> str | None:
    if not isinstance(event, dict):
        return None
    event_type = str(event.get("type") or "")
    return event_type if event_type in {"failed_attempt", "boss_cleared", "boss_switch", "boss_attempt"} else None


def _apply_semantic_game_event(
    state: GameSessionState,
    event: dict[str, Any] | None,
    focused_boss: str | None,
    timestamp: datetime,
) -> bool:
    event_type = _semantic_event_type(event)
    if not event_type or not isinstance(event, dict):
        return False
    confidence = float(event.get("confidence") or 0)
    if confidence < 0.7 or event.get("should_update_current_boss") is False:
        return False

    boss_name = normalize_terminology(str(event.get("boss_name") or focused_boss or "")).strip()
    if not boss_name and state.current_boss and event_type in {"failed_attempt", "boss_cleared", "boss_attempt"}:
        boss_name = state.current_boss.name
    if not state.current_game and boss_name:
        state.current_game = "Elden Ring"

    if event_type == "failed_attempt":
        if boss_name:
            _mark_boss_failed(state, boss_name, timestamp, "semantic_extraction", confidence)
        else:
            state.current_activity = "boss_failed"
        return True
    if event_type == "boss_cleared":
        if not boss_name:
            return False
        _clear_boss(state, boss_name, timestamp, "semantic_extraction")
        return True
    if event_type == "boss_switch":
        if boss_name:
            _set_current_boss(state, boss_name, timestamp, "semantic_extraction", confidence)
        elif state.current_boss:
            _abandon_current_boss(state, timestamp)
        else:
            state.current_activity = "boss_switching"
        return True
    if event_type == "boss_attempt":
        if boss_name:
            _set_current_boss(state, boss_name, timestamp, "semantic_extraction", confidence)
        else:
            state.current_activity = "boss_attempt"
        return True
    return False


def _history_is_recent(state: GameSessionState, boss_name: str, timestamp: datetime) -> bool:
    entry = next((item for item in reversed(state.boss_history) if item.name == boss_name), None)
    if not entry:
        return False
    updated_at = _parse_timestamp(entry.updated_at)
    if not updated_at:
        return False
    return timestamp - updated_at <= FRESH_WINDOW


def _clears_current_boss(message: str) -> bool:
    compact = re.sub(r"\s+", "", message.lower())
    if _fails_current_boss(message):
        return False
    if _has_negated_failure_correction(compact):
        return True
    return any(
        marker in compact
        for marker in (
            "过了",
            "過了",
            "终于过了",
            "終於過了",
            "通关了",
            "通關了",
            "过掉了",
            "過掉了",
            "打过了",
            "打過了",
            "打过",
            "打過",
            "打完",
            "打完了",
            "打掉了",
            "打掉",
            "赢了",
            "贏了",
            "打赢了",
            "打贏了",
            "击败了",
            "擊敗了",
            "干掉了",
            "幹掉了",
            "杀了",
            "殺了",
        )
    )


def _fails_current_boss(message: str) -> bool:
    compact = re.sub(r"\s+", "", message.lower())
    if _has_negated_failure_correction(compact) and not _has_later_failure_after_correction(compact):
        return False
    return any(
        marker in compact
        for marker in (
            "没打过",
            "沒打過",
            "没有打过",
            "沒有打過",
            "还没打过",
            "還沒打過",
            "还是没打过",
            "還是沒打過",
            "又没打过",
            "又沒打過",
            "没过",
            "沒過",
            "没有过",
            "沒有過",
            "还没过",
            "還沒過",
            "还是没过",
            "還是沒過",
            "又没过",
            "又沒過",
            "打不过",
            "打不過",
            "一直打不过",
            "一直打不過",
            "过不了",
            "過不了",
            "过不去",
            "過不去",
            "没赢",
            "沒贏",
            "没有赢",
            "沒有贏",
            "又死",
            "还是死",
            "還是死",
            "死了",
            "失败",
            "失敗",
            "输了",
            "輸了",
        )
    )


def _has_negated_failure_correction(compact: str) -> bool:
    return any(
        marker in compact
        for marker in (
            "不是没打过",
            "不是沒打過",
            "不是没有打过",
            "不是沒有打過",
            "不是没过",
            "不是沒過",
            "不是没有过",
            "不是沒有過",
            "不是打不过",
            "不是打不過",
            "不是没赢",
            "不是沒贏",
        )
    )


def _has_later_failure_after_correction(compact: str) -> bool:
    correction_ends = [
        compact.find(marker) + len(marker)
        for marker in (
            "不是没打过",
            "不是沒打過",
            "不是没有打过",
            "不是沒有打過",
            "不是没过",
            "不是沒過",
            "不是没有过",
            "不是沒有過",
            "不是打不过",
            "不是打不過",
            "不是没赢",
            "不是沒贏",
        )
        if marker in compact
    ]
    if not correction_ends:
        return False
    last_correction_end = max(correction_ends)
    return any(
        compact.find(marker, last_correction_end) >= 0
        for marker in (
            "没打过",
            "沒打過",
            "没有打过",
            "沒有打過",
            "还没打过",
            "還沒打過",
            "还是没打过",
            "還是沒打過",
            "又没打过",
            "又沒打過",
            "没过",
            "沒過",
            "没有过",
            "沒有過",
            "还没过",
            "還沒過",
            "还是没过",
            "還是沒過",
            "又没过",
            "又沒過",
            "打不过",
            "打不過",
            "过不了",
            "過不了",
            "过不去",
            "過不去",
            "没赢",
            "沒贏",
            "没有赢",
            "沒有贏",
        )
    )


def _abandons_current_boss(message: str) -> bool:
    compact = re.sub(r"\s+", "", message.lower())
    return any(
        marker in compact
        for marker in (
            "不打了",
            "不打这个",
            "不打這個",
            "先不打",
            "换boss",
            "換boss",
            "换个boss",
            "換個boss",
            "换一个boss",
            "換一個boss",
            "换目标",
            "換目標",
            "别的boss",
            "別的boss",
            "其他boss",
            "别的目标",
            "別的目標",
        )
    )


def _has_death_signal(message: str) -> bool:
    return any(word in message for word in ("又死", "死了", "一直死", "死太多", "死亡"))


def _has_frustration_signal(message: str) -> bool:
    emotion = detect_user_emotion(message).label
    return emotion in {"frustrated", "death_loop"} or _fails_current_boss(message) or any(
        word in message
        for word in ("烦", "紅溫", "红温", "破防", "打不过", "打不過", "还是不行", "還是不行", "过不去", "卡住", "卡在")
    )


def _has_attempt_signal(message: str) -> bool:
    return any(word in message for word in ("卡在", "卡住", "打", "试", "試", "再来", "再來", "重试", "重試"))


def _has_boss_history_query(message: str) -> bool:
    compact = re.sub(r"\s+", "", message.lower())
    return "boss" in compact and any(marker in compact for marker in ("刚刚", "剛剛", "刚才", "剛才", "刚", "之前", "前面"))


def _derive_game_intent(
    message: str,
    intent: str,
    boss: str | None,
    activity: str | None,
    fails_boss: bool,
    clears_boss: bool,
    abandons_boss: bool,
) -> str | None:
    if fails_boss:
        return "boss_failed"
    if clears_boss:
        return "boss_cleared"
    if abandons_boss:
        return "boss_switching"
    if boss and (_has_death_signal(message) or _has_frustration_signal(message) or _has_attempt_signal(message)):
        return "boss_attempt"
    if _has_boss_history_query(message):
        return "boss_history_query"
    if activity in {"boss_attempt", "unclear_boss_reference"}:
        return activity
    if intent.startswith("elden_ring"):
        return intent
    if boss:
        return "boss_discussion"
    if _is_game_related(intent, message, boss):
        return "game_discussion"
    return None


def _detect_activity(message: str, intent: str) -> str | None:
    if _has_boss_history_query(message):
        return "boss_history_query"
    if _fails_current_boss(message):
        return "boss_failed"
    if intent == "elden_ring_location":
        return "route_or_location"
    if intent == "elden_ring_build":
        return "build_or_equipment"
    if intent.startswith("elden_ring"):
        return "game_discussion"
    if _has_death_signal(message) or _has_frustration_signal(message):
        return "boss_attempt"
    return None


def _append_topic(state: GameSessionState, topic: str) -> None:
    topic = normalize_terminology(topic)
    if not topic:
        return
    state.recent_game_topics = [item for item in state.recent_game_topics if item != topic]
    state.recent_game_topics.append(topic)
    state.recent_game_topics = state.recent_game_topics[-8:]


def _pressure_text(state: GameSessionState) -> str:
    parts = []
    if state.death_count:
        parts.append(f"最近死亡提及 {state.death_count} 次")
    if state.frustration_count:
        parts.append(f"挫败提及 {state.frustration_count} 次")
    return "，".join(parts)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return _ensure_aware(datetime.fromisoformat(value))
    except ValueError:
        return None


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
