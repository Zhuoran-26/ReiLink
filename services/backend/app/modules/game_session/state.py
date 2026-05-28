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
class GameSessionState:
    current_game: str | None = None
    current_boss: CurrentBoss | None = None
    current_activity: str | None = None
    recent_game_topics: list[str] = field(default_factory=list)
    frustration_count: int = 0
    death_count: int = 0
    last_user_intent: str | None = None
    last_game_intent: str | None = None
    last_updated_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "current_game": self.current_game,
            "current_boss": self.current_boss.as_dict() if self.current_boss else None,
            "current_activity": self.current_activity,
            "recent_game_topics": self.recent_game_topics,
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
        boss_data = normalized.get("current_boss")
        boss = CurrentBoss(**boss_data) if isinstance(boss_data, dict) and boss_data.get("name") else None
        return GameSessionState(
            current_game=normalized.get("current_game"),
            current_boss=boss,
            current_activity=normalized.get("current_activity"),
            recent_game_topics=list(normalized.get("recent_game_topics") or []),
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
    ) -> GameSessionState:
        state = self.load()
        now = _ensure_aware(timestamp)
        explicit_boss = _detect_boss(user_message)
        focused_boss = normalize_terminology(session_focus_boss or "") or None
        has_elliptical_reference = is_elliptical_boss_reference(user_message)
        clears_boss = _clears_current_boss(user_message)
        game_name = _detect_current_game(game_status, user_message, intent, explicit_boss or focused_boss)

        state.last_user_intent = intent
        state.last_updated_at = now.isoformat()
        if game_name:
            state.current_game = game_name

        if _is_game_related(intent, user_message, explicit_boss or focused_boss):
            state.last_game_intent = intent

        if _has_death_signal(user_message):
            state.death_count += 1
        if _has_frustration_signal(user_message):
            state.frustration_count += 1

        if explicit_boss and clears_boss:
            state.current_boss = None
            state.current_activity = "boss_cleared"
            _append_topic(state, f"{explicit_boss}已过")
        elif explicit_boss:
            state.current_boss = _updated_boss(state.current_boss, explicit_boss, now, "current_message", 0.95)
            state.current_activity = "boss_attempt"
            _append_topic(state, explicit_boss)
        elif clears_boss and state.current_boss:
            _append_topic(state, f"{state.current_boss.name}已结束")
            state.current_boss = None
            state.current_activity = "boss_cleared"
        elif focused_boss and has_elliptical_reference:
            state.current_boss = _updated_boss(state.current_boss, focused_boss, now, "session_focus", 0.85)
            state.current_activity = "boss_attempt"
            _append_topic(state, focused_boss)
        elif has_elliptical_reference and state.current_boss:
            freshness = boss_freshness(state, now)
            if freshness.freshness in {"fresh", "weak"}:
                state.current_boss = _updated_boss(state.current_boss, state.current_boss.name, now, "elliptical_reference", 0.75)
                state.current_activity = "boss_attempt"
                _append_topic(state, state.current_boss.name)
            else:
                state.current_activity = "unclear_boss_reference"
        elif _is_game_related(intent, user_message, explicit_boss or focused_boss):
            state.current_activity = _detect_activity(user_message, intent)

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


def _clears_current_boss(message: str) -> bool:
    compact = re.sub(r"\s+", "", message.lower())
    return any(
        marker in compact
        for marker in (
            "过了",
            "過了",
            "打过了",
            "打過了",
            "不打了",
            "不打这个",
            "不打這個",
            "换boss",
            "換boss",
            "换目标",
            "換目標",
        )
    )


def _has_death_signal(message: str) -> bool:
    return any(word in message for word in ("又死", "死了", "一直死", "死太多", "死亡"))


def _has_frustration_signal(message: str) -> bool:
    emotion = detect_user_emotion(message).label
    return emotion in {"frustrated", "death_loop"} or any(
        word in message for word in ("烦", "紅溫", "红温", "破防", "打不过", "打不過", "还是不行", "還是不行", "过不去", "卡住", "卡在")
    )


def _detect_activity(message: str, intent: str) -> str | None:
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
