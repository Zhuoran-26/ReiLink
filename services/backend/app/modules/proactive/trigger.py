from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.modules.app_settings.store import AppSettingsStore
from app.modules.game_session.state import GameSessionStore
from app.modules.memory.store import ConversationStore
from app.schemas.api import AppSettingsUpdate

TRIGGER_TYPES = ("idle_silence", "repeated_death", "late_night", "frustration_loop")
PRIORITY = ("repeated_death", "frustration_loop", "late_night", "idle_silence")
LATE_NIGHT_START = time(hour=23, minute=30)
ACTIVE_CHAT_WINDOW = timedelta(minutes=15)

MESSAGE_POOL = {
    "idle_silence": [
        "……还在？",
        "不说也可以。",
        "今天话少了。",
        "我没催你。",
        "安静一会儿也行。",
    ],
    "repeated_death": [
        "你开始急了。",
        "先停一下。",
        "这轮别想着赢。",
        "少打一刀。",
        "先活下来。",
    ],
    "late_night": [
        "已经很晚了。",
        "别硬撑。",
        "再打一会儿就停。",
        "眼睛该休息了。",
        "别把今晚耗干。",
    ],
    "frustration_loop": [
        "你已经烦了。",
        "先放一下。",
        "别和自己较劲。",
        "停一下，不算输。",
        "别硬撞了。",
    ],
}

DEATH_MARKERS = ("又死", "一直死", "死太多", "还是没过", "還是沒過", "没过", "沒過", "打不过", "打不過", "过不了", "過不了")
FRUSTRATION_MARKERS = ("烦", "煩", "红温", "紅溫", "破防", "崩溃", "崩潰", "气死", "氣死", "不想打", "受不了", "还是不行", "還是不行", "卡住")


@dataclass
class ProactiveState:
    enabled: bool = False
    sensitivity: str = "low"
    enabled_at: str | None = None
    last_triggered_at: str | None = None
    last_triggered_type: str | None = None
    trigger_cooldowns: dict[str, str] = field(default_factory=dict)
    recent_proactive_messages: list[dict[str, str]] = field(default_factory=list)
    last_trigger_reason: str | None = None
    last_observed_death_count: int = 0
    last_observed_frustration_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "sensitivity": self.sensitivity,
            "enabled_at": self.enabled_at,
            "last_triggered_at": self.last_triggered_at,
            "last_triggered_type": self.last_triggered_type,
            "trigger_cooldowns": self.trigger_cooldowns,
            "recent_proactive_messages": self.recent_proactive_messages[-12:],
            "last_trigger_reason": self.last_trigger_reason,
            "last_observed_death_count": self.last_observed_death_count,
            "last_observed_frustration_count": self.last_observed_frustration_count,
        }


@dataclass(frozen=True)
class TriggerCandidate:
    trigger_type: str
    reason: str
    score: int = 1


@dataclass(frozen=True)
class ConversationSnapshot:
    entries: list[Any]
    last_entry: Any | None
    last_user_entry: Any | None
    recent_user_messages: list[str]


class ProactiveCompanion:
    persona_id = "rei_like"

    def __init__(
        self,
        state_path: Path | None = None,
        conversation_store: ConversationStore | None = None,
        game_session: GameSessionStore | None = None,
    ) -> None:
        self.state_path = state_path or settings.proactive_state_path
        self.conversation_store = conversation_store or ConversationStore()
        self.game_session = game_session or GameSessionStore()

    def status(self, session_id: str = "default", now: datetime | None = None) -> dict[str, Any]:
        now = _ensure_aware(now or datetime.now().astimezone())
        state = self._load_ready_state(now)
        snapshot = self._conversation_snapshot(session_id)
        game_debug = self.game_session.debug_state(now=now)
        timing = self._idle_timing(state, snapshot, now)
        candidates = self._active_candidates(state, snapshot, game_debug, now, timing)
        cooldown_remaining = self._global_cooldown_remaining(state, now)
        next_possible = _future_iso(now, self._next_possible_remaining(state, candidates, timing, now))
        return {
            "enabled": state.enabled,
            "sensitivity": state.sensitivity,
            **timing,
            "last_triggered_at": state.last_triggered_at,
            "last_triggered_type": state.last_triggered_type or "none",
            "next_possible_trigger_at": next_possible,
            "active_candidate_triggers": [candidate.trigger_type for candidate in candidates],
            "cooldown_remaining_seconds": cooldown_remaining,
            "last_trigger_reason": state.last_trigger_reason,
        }

    def check(
        self,
        session_id: str = "default",
        connected: bool = True,
        is_user_typing: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = _ensure_aware(now or datetime.now().astimezone())
        state = self._load_ready_state(now)
        snapshot = self._conversation_snapshot(session_id)
        game_debug = self.game_session.debug_state(now=now)
        timing = self._idle_timing(state, snapshot, now)
        candidates = self._active_candidates(state, snapshot, game_debug, now, timing)
        response_debug = self._response_debug(state, candidates, timing, now)

        blocked_reason = self._blocked_reason(state, snapshot, connected, is_user_typing, now)
        if blocked_reason:
            return _no_send(blocked_reason, candidates=candidates, debug=response_debug)
        if not candidates:
            return _no_send("no_candidate", candidates=candidates, debug=response_debug)

        candidate = self._select_candidate(candidates)
        cooldown_remaining = self._cooldown_remaining(state, candidate.trigger_type, now)
        if cooldown_remaining > 0:
            return _no_send(
                "cooldown",
                candidate.trigger_type,
                cooldown_remaining,
                candidates,
                debug={**response_debug, "cooldown_remaining_seconds": cooldown_remaining},
            )

        message = self._pick_message(candidate.trigger_type, state)
        state.last_triggered_at = now.isoformat()
        state.last_triggered_type = candidate.trigger_type
        state.last_trigger_reason = candidate.reason
        state.trigger_cooldowns[candidate.trigger_type] = now.isoformat()
        state.last_observed_death_count = int(game_debug.get("death_count") or 0)
        state.last_observed_frustration_count = int(game_debug.get("frustration_count") or 0)
        state.recent_proactive_messages.append(
            {
                "trigger_type": candidate.trigger_type,
                "message": message,
                "timestamp": now.isoformat(),
                "reason": candidate.reason,
            }
        )
        self.save(state)
        self.conversation_store.append_proactive(
            session_id=session_id,
            game_id=game_debug.get("current_game"),
            persona_id=self.persona_id,
            assistant_reply=message,
            timestamp=now,
            trigger_type=candidate.trigger_type,
            reason=candidate.reason,
        )
        return {
            "should_send": True,
            "trigger_type": candidate.trigger_type,
            "message": message,
            "reason": candidate.reason,
            **response_debug,
            "cooldown_remaining_seconds": 0,
        }

    def update_settings(
        self,
        enabled: bool | None = None,
        sensitivity: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = _ensure_aware(now or datetime.now().astimezone())
        store = AppSettingsStore()
        previous = store.load()
        payload: dict[str, str] = {}
        if enabled is not None:
            payload["proactive_companion"] = "on" if enabled else "off"
        if sensitivity in {"low", "normal", "high"}:
            payload["proactive_sensitivity"] = sensitivity
        saved = store.save(AppSettingsUpdate(**payload))
        self.sync_settings(previous, saved, now=now)
        return self.status(now=now)

    def sync_settings(self, previous: Any, saved: Any, now: datetime | None = None) -> None:
        now = _ensure_aware(now or datetime.now().astimezone())
        state = self.load()
        state.enabled = saved.proactive_companion == "on"
        state.sensitivity = saved.proactive_sensitivity
        was_enabled = previous.proactive_companion == "on"
        if state.enabled and (not was_enabled or not state.enabled_at):
            state.enabled_at = now.isoformat()
        if not state.enabled:
            state.enabled_at = None
        self.save(state)

    def load(self) -> ProactiveState:
        raw: dict[str, Any] = {}
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8") or "{}")
                raw = data if isinstance(data, dict) else {}
            except (OSError, json.JSONDecodeError):
                raw = {}
        app_settings = AppSettingsStore().load()
        return ProactiveState(
            enabled=app_settings.proactive_companion == "on",
            sensitivity=app_settings.proactive_sensitivity,
            enabled_at=_optional_str(raw.get("enabled_at") or raw.get("proactive_enabled_at")),
            last_triggered_at=_optional_str(raw.get("last_triggered_at")),
            last_triggered_type=_known_trigger(raw.get("last_triggered_type")),
            trigger_cooldowns=_string_dict(raw.get("trigger_cooldowns")),
            recent_proactive_messages=_recent_messages(raw.get("recent_proactive_messages")),
            last_trigger_reason=_optional_str(raw.get("last_trigger_reason")),
            last_observed_death_count=max(0, int(raw.get("last_observed_death_count") or 0)),
            last_observed_frustration_count=max(0, int(raw.get("last_observed_frustration_count") or 0)),
        )

    def _load_ready_state(self, now: datetime) -> ProactiveState:
        state = self.load()
        if state.enabled and not state.enabled_at:
            state.enabled_at = now.isoformat()
            self.save(state)
        return state

    def save(self, state: ProactiveState) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state.as_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _idle_timing(self, state: ProactiveState, snapshot: ConversationSnapshot, now: datetime) -> dict[str, Any]:
        thresholds = _thresholds(state.sensitivity)
        enabled_at = _parse_timestamp(state.enabled_at)
        last_user_at = _entry_time(snapshot.last_user_entry)
        idle_start = None
        if last_user_at and enabled_at:
            idle_start = max(last_user_at, enabled_at)
        elif last_user_at:
            idle_start = last_user_at

        idle_for_seconds = max(0, int((now - idle_start).total_seconds())) if idle_start else 0
        initial_grace_seconds = _initial_grace_seconds(state.sensitivity)
        initial_grace_remaining = 0
        if state.enabled and enabled_at:
            initial_grace_remaining = _remaining_from_datetime(enabled_at, timedelta(seconds=initial_grace_seconds), now)

        return {
            "enabled_at": state.enabled_at if state.enabled else None,
            "last_user_activity_at": last_user_at.isoformat() if last_user_at else None,
            "idle_for_seconds": idle_for_seconds,
            "idle_threshold_seconds": thresholds["idle_seconds"],
            "initial_grace_remaining_seconds": initial_grace_remaining,
        }

    def _response_debug(
        self,
        state: ProactiveState,
        candidates: list[TriggerCandidate],
        timing: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        cooldown_remaining = self._global_cooldown_remaining(state, now)
        return {
            **timing,
            "next_possible_trigger_at": _future_iso(now, self._next_possible_remaining(state, candidates, timing, now)),
            "active_candidate_triggers": [candidate.trigger_type for candidate in candidates],
            "cooldown_remaining_seconds": cooldown_remaining,
        }

    def _next_possible_remaining(
        self,
        state: ProactiveState,
        candidates: list[TriggerCandidate],
        timing: dict[str, Any],
        now: datetime,
    ) -> int:
        if not state.enabled:
            return 0
        if candidates:
            return self._cooldown_remaining(state, self._select_candidate(candidates).trigger_type, now)
        global_remaining = self._global_cooldown_remaining(state, now)
        grace_remaining = int(timing.get("initial_grace_remaining_seconds") or 0)
        last_user_at = _parse_timestamp(timing.get("last_user_activity_at"))
        if not last_user_at:
            return max(global_remaining, grace_remaining)
        idle_remaining = int(timing.get("idle_threshold_seconds") or 0) - int(timing.get("idle_for_seconds") or 0)
        return max(global_remaining, grace_remaining, idle_remaining, 0)

    def _conversation_snapshot(self, session_id: str) -> ConversationSnapshot:
        entries = self.conversation_store.read_session(session_id)
        user_entries = [
            entry
            for entry in entries
            if entry.assistant_message_type != "proactive" and entry.user_message
        ]
        return ConversationSnapshot(
            entries=entries,
            last_entry=entries[-1] if entries else None,
            last_user_entry=user_entries[-1] if user_entries else None,
            recent_user_messages=[entry.user_message for entry in user_entries[-6:]],
        )

    def _active_candidates(
        self,
        state: ProactiveState,
        snapshot: ConversationSnapshot,
        game_debug: dict[str, Any],
        now: datetime,
        timing: dict[str, Any],
    ) -> list[TriggerCandidate]:
        thresholds = _thresholds(state.sensitivity)
        candidates: list[TriggerCandidate] = []
        last_user_at = _entry_time(snapshot.last_user_entry)
        recent_text = "\n".join(snapshot.recent_user_messages)
        death_mentions = _count_markers(snapshot.recent_user_messages, DEATH_MARKERS)
        frustration_mentions = _count_markers(snapshot.recent_user_messages, FRUSTRATION_MARKERS)
        death_count = int(game_debug.get("death_count") or 0)
        frustration_count = int(game_debug.get("frustration_count") or 0)

        idle_for_seconds = int(timing.get("idle_for_seconds") or 0)
        idle_ready = (
            state.enabled
            and last_user_at
            and int(timing.get("initial_grace_remaining_seconds") or 0) <= 0
            and idle_for_seconds >= thresholds["idle_seconds"]
        )
        if idle_ready:
            candidates.append(TriggerCandidate("idle_silence", f"idle_for_{idle_for_seconds}s"))

        if death_count - state.last_observed_death_count >= thresholds["death_delta"] or death_mentions >= thresholds["recent_signal_count"]:
            candidates.append(
                TriggerCandidate(
                    "repeated_death",
                    f"death_delta={max(death_count - state.last_observed_death_count, 0)} recent_death_mentions={death_mentions}",
                    3,
                )
            )

        if _is_late_night(now) and (_has_active_boss(game_debug) or _active_recently(last_user_at, now)):
            candidates.append(TriggerCandidate("late_night", "late_night_active_session", 2))

        if (
            frustration_count - state.last_observed_frustration_count >= thresholds["frustration_delta"]
            or frustration_mentions >= thresholds["recent_signal_count"]
            or (_has_frustration_loop(recent_text) and frustration_mentions > 0)
        ):
            candidates.append(
                TriggerCandidate(
                    "frustration_loop",
                    (
                        f"frustration_delta={max(frustration_count - state.last_observed_frustration_count, 0)} "
                        f"recent_frustration_mentions={frustration_mentions}"
                    ),
                    3,
                )
            )
        return _dedupe_candidates(candidates)

    def _blocked_reason(
        self,
        state: ProactiveState,
        snapshot: ConversationSnapshot,
        connected: bool,
        is_user_typing: bool,
        now: datetime,
    ) -> str | None:
        if not state.enabled:
            return "disabled"
        if not connected:
            return "not_connected"
        if is_user_typing:
            return "user_typing"
        last_user_at = _entry_time(snapshot.last_user_entry)
        if last_user_at and now - last_user_at < timedelta(seconds=settings.proactive_user_grace_seconds):
            return "recent_user_message"
        if snapshot.last_entry and snapshot.last_entry.assistant_message_type == "proactive":
            return "last_message_proactive"
        return None

    def _select_candidate(self, candidates: list[TriggerCandidate]) -> TriggerCandidate:
        ranked = sorted(candidates, key=lambda item: (PRIORITY.index(item.trigger_type), -item.score))
        return ranked[0]

    def _cooldown_remaining(self, state: ProactiveState, trigger_type: str, now: datetime) -> int:
        global_remaining = self._global_cooldown_remaining(state, now)
        type_remaining = _remaining_seconds(
            state.trigger_cooldowns.get(trigger_type),
            timedelta(seconds=settings.proactive_type_cooldown_seconds),
            now,
        )
        return max(global_remaining, type_remaining)

    def _global_cooldown_remaining(self, state: ProactiveState, now: datetime) -> int:
        return _remaining_seconds(
            state.last_triggered_at,
            timedelta(seconds=settings.proactive_global_cooldown_seconds),
            now,
        )

    def _pick_message(self, trigger_type: str, state: ProactiveState) -> str:
        pool = MESSAGE_POOL[trigger_type]
        recent = [
            item.get("message")
            for item in state.recent_proactive_messages[-5:]
            if item.get("trigger_type") == trigger_type
        ]
        for message in pool:
            if message not in recent:
                return message
        return pool[len(state.recent_proactive_messages) % len(pool)]


def _no_send(
    reason: str,
    trigger_type: str = "none",
    cooldown_remaining_seconds: int = 0,
    candidates: list[TriggerCandidate] | None = None,
    debug: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if trigger_type == "none" and candidates:
        trigger_type = candidates[0].trigger_type
    return {
        "should_send": False,
        "trigger_type": trigger_type,
        "message": "",
        "reason": reason,
        **(debug or {}),
        "cooldown_remaining_seconds": cooldown_remaining_seconds,
    }


def _thresholds(sensitivity: str) -> dict[str, int]:
    idle_seconds = int(settings.proactive_idle_seconds)
    if sensitivity == "high":
        idle_seconds = max(30, idle_seconds // 2)
        return {"idle_seconds": idle_seconds, "death_delta": 1, "frustration_delta": 1, "recent_signal_count": 1}
    if sensitivity == "normal":
        idle_seconds = max(60, int(idle_seconds * 0.75))
        return {"idle_seconds": idle_seconds, "death_delta": 1, "frustration_delta": 1, "recent_signal_count": 2}
    return {"idle_seconds": idle_seconds, "death_delta": 2, "frustration_delta": 2, "recent_signal_count": 2}


def _initial_grace_seconds(sensitivity: str) -> int:
    override = int(settings.proactive_initial_grace_seconds)
    if override > 0:
        return override
    if sensitivity == "high":
        return 120
    if sensitivity == "normal":
        return 300
    return 600


def _remaining_seconds(last_at: str | None, cooldown: timedelta, now: datetime) -> int:
    parsed = _parse_timestamp(last_at)
    if not parsed:
        return 0
    return _remaining_from_datetime(parsed, cooldown, now)


def _remaining_from_datetime(last_at: datetime, cooldown: timedelta, now: datetime) -> int:
    remaining = last_at + cooldown - now
    return max(0, math.ceil(remaining.total_seconds()))


def _future_iso(now: datetime, seconds: int) -> str | None:
    if seconds <= 0:
        return None
    return (now + timedelta(seconds=seconds)).isoformat()


def _entry_time(entry: Any | None) -> datetime | None:
    if not entry:
        return None
    return _parse_timestamp(getattr(entry, "timestamp", None))


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return _ensure_aware(parsed)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.astimezone()
    return value


def _is_late_night(now: datetime) -> bool:
    local_time = now.timetz().replace(tzinfo=None)
    return local_time >= LATE_NIGHT_START or local_time < time(hour=5)


def _has_active_boss(game_debug: dict[str, Any]) -> bool:
    return bool(game_debug.get("current_boss") or game_debug.get("last_attempted_boss"))


def _active_recently(last_user_at: datetime | None, now: datetime) -> bool:
    return bool(last_user_at and now - last_user_at <= ACTIVE_CHAT_WINDOW)


def _count_markers(messages: list[str], markers: tuple[str, ...]) -> int:
    count = 0
    for message in messages:
        compact = _compact(message)
        if any(marker in compact for marker in markers):
            count += 1
    return count


def _has_frustration_loop(text: str) -> bool:
    compact = _compact(text)
    return bool(re.search(r"(烦|煩|红温|紅溫|破防|崩溃|崩潰).{0,20}(又|还是|還是|一直|打不过|打不過)", compact))


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def _dedupe_candidates(candidates: list[TriggerCandidate]) -> list[TriggerCandidate]:
    seen: set[str] = set()
    result = []
    for candidate in candidates:
        if candidate.trigger_type in seen:
            continue
        seen.add(candidate.trigger_type)
        result.append(candidate)
    return result


def _optional_str(value: Any) -> str | None:
    return str(value) if value else None


def _known_trigger(value: Any) -> str | None:
    text = str(value or "")
    return text if text in TRIGGER_TYPES else None


def _string_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if key in TRIGGER_TYPES and item}


def _recent_messages(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    messages = []
    for item in value[-12:]:
        if isinstance(item, dict):
            messages.append({str(key): str(val) for key, val in item.items() if val is not None})
    return messages
