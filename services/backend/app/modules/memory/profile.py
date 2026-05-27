from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.modules.dialogue_agent.emotion import detect_user_emotion
from app.modules.elden_ring_knowledge.terminology import normalize_mapping_values, normalize_terminology

BOSS_FRESHNESS = timedelta(hours=48)
EMOTION_FRESHNESS = timedelta(hours=24)
BOSS_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("恶兆妖鬼 Margit", ("margit", "玛尔基特", "瑪爾基特", "恶兆妖鬼", "惡兆妖鬼", "恶兆", "惡兆")),
    ("大树守卫", ("tree sentinel", "大树守卫", "大樹守衛")),
    ("拉塔恩", ("radahn", "拉塔恩", "碎星", "拉塔恩将军", "拉塔恩將軍")),
    ("玛莲妮亚", ("malenia", "玛莲妮亚", "瑪蓮妮亞", "米凯拉", "米凱拉")),
)


@dataclass(frozen=True)
class MemoryPromptLine:
    source: str
    field: str
    text: str
    timestamp: str | None = None

    def as_dict(self) -> dict[str, str]:
        item = {"source": self.source, "field": self.field, "text": self.text}
        if self.timestamp:
            item["timestamp"] = self.timestamp
        return item


@dataclass(frozen=True)
class MemoryPromptContext:
    lines: list[MemoryPromptLine]

    def as_prompt_text(self) -> str:
        return "\n".join(f"- {line.text}" for line in self.lines)

    def as_debug_items(self) -> list[dict[str, str]]:
        return [line.as_dict() for line in self.lines]


@dataclass
class UserProfile:
    user_name: str | None = None
    favorite_game: str | None = None
    preferred_tone: str | None = None
    likes_teasing: bool | None = None
    skill_level: str | None = None
    current_boss: str | None = None
    repeated_struggles: list[str] = field(default_factory=list)
    emotional_notes: list[str] = field(default_factory=list)
    last_seen_at: str | None = None
    memory_updated_at: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "user_name": self.user_name,
            "favorite_game": self.favorite_game,
            "preferred_tone": self.preferred_tone,
            "likes_teasing": self.likes_teasing,
            "skill_level": self.skill_level,
            "current_boss": self.current_boss,
            "repeated_struggles": self.repeated_struggles,
            "emotional_notes": self.emotional_notes,
            "last_seen_at": self.last_seen_at,
            "memory_updated_at": self.memory_updated_at,
        }


class PlayerMemory:
    def __init__(self, profile_path: Path | None = None, episodes_path: Path | None = None) -> None:
        self.profile_path = profile_path or settings.user_profile_path
        self.episodes_path = episodes_path or settings.episodes_path
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        self.episodes_path.parent.mkdir(parents=True, exist_ok=True)

    def load_profile(self) -> UserProfile:
        if not self.profile_path.exists():
            return UserProfile()
        data = json.loads(self.profile_path.read_text(encoding="utf-8") or "{}")
        return UserProfile(**{**UserProfile().as_dict(), **_normalize_profile_data(data)})

    def save_profile(self, profile: UserProfile) -> None:
        data = _normalize_profile_data(profile.as_dict())
        self.profile_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def recent_episodes(self, limit: int = 5) -> list[dict[str, Any]]:
        if not self.episodes_path.exists():
            return []
        lines = [line for line in self.episodes_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return [_normalize_episode(json.loads(line)) for line in lines[-limit:]]

    def reset(self) -> None:
        self.save_profile(UserProfile())
        self.episodes_path.write_text("", encoding="utf-8")

    def build_prompt_context(self, now: datetime | None = None) -> str:
        return self.build_prompt_context_with_provenance(now=now).as_prompt_text()

    def build_prompt_context_with_provenance(self, now: datetime | None = None) -> MemoryPromptContext:
        now = _ensure_aware(now or datetime.now(timezone.utc))
        profile = self.load_profile()
        lines: list[MemoryPromptLine] = []
        active_boss = self._active_current_boss(profile, now)

        if active_boss:
            lines.append(active_boss)
        elif profile.preferred_tone:
            lines.append(
                MemoryPromptLine(
                    "profile",
                    "preferred_tone",
                    f"玩家偏好的语气：{profile.preferred_tone}",
                    profile.memory_updated_at.get("preferred_tone"),
                )
            )
        elif profile.favorite_game:
            lines.append(
                MemoryPromptLine(
                    "profile",
                    "favorite_game",
                    f"玩家最近在玩：{profile.favorite_game}",
                    profile.memory_updated_at.get("favorite_game"),
                )
            )
        elif profile.user_name:
            lines.append(
                MemoryPromptLine("profile", "user_name", f"玩家名字：{profile.user_name}", profile.memory_updated_at.get("user_name"))
            )

        latest_episode = next(
            (
                episode
                for episode in reversed(self.recent_episodes(limit=5))
                if episode.get("summary") and _is_fresh(episode.get("timestamp"), now, BOSS_FRESHNESS)
            ),
            None,
        )
        if latest_episode:
            lines.append(MemoryPromptLine("episode", "summary", latest_episode["summary"], latest_episode.get("timestamp")))

        if profile.emotional_notes and _is_fresh(profile.memory_updated_at.get("emotional_notes"), now, EMOTION_FRESHNESS):
            lines.append(
                MemoryPromptLine(
                    "profile",
                    "emotional_notes",
                    f"最近情绪：{profile.emotional_notes[-1]}",
                    profile.memory_updated_at.get("emotional_notes"),
                )
            )

        deduped: list[MemoryPromptLine] = []
        seen = set()
        for line in lines:
            if line.text in seen:
                continue
            seen.add(line.text)
            deduped.append(line)
            if len(deduped) == 3:
                break
        return MemoryPromptContext(deduped)

    def active_memory_state(self, now: datetime | None = None) -> dict[str, Any]:
        now = _ensure_aware(now or datetime.now(timezone.utc))
        profile = self.load_profile()
        boss_line = self._active_current_boss(profile, now)
        emotional_note = None
        if profile.emotional_notes and _is_fresh(profile.memory_updated_at.get("emotional_notes"), now, EMOTION_FRESHNESS):
            emotional_note = profile.emotional_notes[-1]
        return {
            "memory_written": self._has_any_memory(profile),
            "current_boss": _extract_value_from_line(boss_line.text) if boss_line else None,
            "emotional_note": emotional_note,
            "recent_episode_count": len(self.recent_episodes(limit=50)),
        }

    def _active_current_boss(self, profile: UserProfile, now: datetime) -> MemoryPromptLine | None:
        profile_time = _parse_timestamp(profile.memory_updated_at.get("current_boss"))
        latest_boss_episode = self._latest_boss_episode()
        episode_time = _parse_timestamp(latest_boss_episode.get("timestamp") if latest_boss_episode else None)
        profile_boss_negated_at = self._latest_negation_time_for_boss(profile.current_boss)

        if latest_boss_episode and episode_time and _is_within(episode_time, now, BOSS_FRESHNESS):
            if not profile_time or episode_time >= profile_time or latest_boss_episode.get("boss") != profile.current_boss:
                return MemoryPromptLine(
                    "episode",
                    "boss",
                    f"玩家当前卡点：{latest_boss_episode['boss']}",
                    latest_boss_episode.get("timestamp"),
                )

        if (
            profile.current_boss
            and profile_time
            and _is_within(profile_time, now, BOSS_FRESHNESS)
            and not (profile_boss_negated_at and profile_boss_negated_at >= profile_time)
        ):
            return MemoryPromptLine("profile", "current_boss", f"玩家当前卡点：{profile.current_boss}", profile_time.isoformat())
        return None

    def _latest_boss_episode(self) -> dict[str, Any] | None:
        episodes = []
        for episode in self.recent_episodes(limit=50):
            if not episode.get("boss") or _episode_negates_boss(episode):
                continue
            episode_time = _parse_timestamp(episode.get("timestamp"))
            negated_at = self._latest_negation_time_for_boss(episode.get("boss"))
            if negated_at and episode_time and negated_at >= episode_time:
                continue
            episodes.append(episode)
        if not episodes:
            return None
        return max(episodes, key=lambda episode: _parse_timestamp(episode.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc))

    def _latest_negation_time_for_boss(self, boss: str | None) -> datetime | None:
        if not boss:
            return None
        negation_times = [
            _parse_timestamp(episode.get("timestamp"))
            for episode in self.recent_episodes(limit=50)
            if boss in _detect_negated_bosses(str(episode.get("user_message_sample", "")).lower())
        ]
        valid_times = [timestamp for timestamp in negation_times if timestamp]
        if not valid_times:
            return None
        return max(valid_times)

    def _has_any_memory(self, profile: UserProfile) -> bool:
        return any(
            [
                profile.user_name,
                profile.favorite_game,
                profile.preferred_tone,
                profile.current_boss,
                profile.repeated_struggles,
                profile.emotional_notes,
                self.recent_episodes(limit=1),
            ]
        )

    def extract_and_update(
        self,
        user_message: str,
        assistant_reply: str,
        intent: str,
        timestamp: datetime,
    ) -> None:
        profile = self.load_profile()
        episode = self._extract_episode(user_message, assistant_reply, intent, timestamp)
        negated_bosses = _detect_negated_bosses(user_message.lower())
        changed = False

        if episode.get("boss"):
            profile.current_boss = episode["boss"]
            profile.favorite_game = profile.favorite_game or "Elden Ring"
            profile.memory_updated_at["current_boss"] = timestamp.isoformat()
            profile.memory_updated_at.setdefault("favorite_game", timestamp.isoformat())
            changed = True
        elif profile.current_boss and profile.current_boss in negated_bosses:
            profile.current_boss = None
            profile.memory_updated_at["current_boss"] = timestamp.isoformat()
            changed = True
        if episode.get("struggle") and episode["struggle"] not in profile.repeated_struggles:
            profile.repeated_struggles.append(episode["struggle"])
            changed = True
        if episode.get("preferred_tone"):
            profile.preferred_tone = episode["preferred_tone"]
            profile.likes_teasing = episode["preferred_tone"] == "轻微吐槽"
            profile.memory_updated_at["preferred_tone"] = timestamp.isoformat()
            changed = True
        if episode.get("skill_level"):
            profile.skill_level = episode["skill_level"]
            profile.memory_updated_at["skill_level"] = timestamp.isoformat()
            changed = True
        if episode.get("emotional_state"):
            note = episode["emotional_state"]
            if not profile.emotional_notes or profile.emotional_notes[-1] != note:
                profile.emotional_notes = [*profile.emotional_notes[-8:], note]
            profile.memory_updated_at["emotional_notes"] = timestamp.isoformat()
            changed = True
        if episode.get("user_name"):
            profile.user_name = episode["user_name"]
            profile.memory_updated_at["user_name"] = timestamp.isoformat()
            changed = True

        profile.last_seen_at = timestamp.isoformat()
        self.save_profile(profile)
        if changed:
            self._append_episode(episode)

    def _append_episode(self, episode: dict[str, Any]) -> None:
        with self.episodes_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(_normalize_episode(episode), ensure_ascii=False) + "\n")

    def _extract_episode(self, user_message: str, assistant_reply: str, intent: str, timestamp: datetime) -> dict[str, Any]:
        normalized = user_message.lower()
        boss = _detect_boss(normalized)
        emotional_state = _detect_emotion(user_message)
        preferred_tone = _detect_tone_preference(user_message)
        user_name = _detect_user_name(user_message)
        struggle = _detect_struggle(user_message, boss)
        skill_level = "新手" if any(word in user_message for word in ("新手", "刚玩", "第一次玩")) else None
        attitude = _detect_attitude_to_rei(user_message)
        summary = _build_summary(boss, struggle, emotional_state, preferred_tone, attitude)
        return _normalize_episode({
            "timestamp": timestamp.isoformat(),
            "intent": intent,
            "boss": boss,
            "struggle": struggle,
            "preferred_tone": preferred_tone,
            "skill_level": skill_level,
            "emotional_state": emotional_state,
            "topic": boss or ("Rei" if attitude else None),
            "attitude_to_rei": attitude,
            "user_name": user_name,
            "user_message_sample": user_message[:120],
            "assistant_reply_sample": normalize_terminology(assistant_reply[:120]),
            "summary": summary,
        })


def _detect_boss(normalized: str) -> str | None:
    negated = _detect_negated_bosses(normalized)
    for canonical, aliases in BOSS_ALIASES:
        if canonical in negated:
            continue
        if any(alias in normalized for alias in aliases):
            return canonical
    return None


def _detect_negated_bosses(normalized: str) -> set[str]:
    compact = re.sub(r"\s+", "", normalized.lower())
    negated: set[str] = set()
    for canonical, aliases in BOSS_ALIASES:
        for alias in aliases:
            alias_compact = re.sub(r"\s+", "", alias.lower())
            if f"不是{alias_compact}" in compact:
                negated.add(canonical)
                break
    return negated


def _episode_negates_boss(episode: dict[str, Any]) -> bool:
    boss = normalize_terminology(str(episode.get("boss") or ""))
    user_message = str(episode.get("user_message_sample") or "").lower()
    return boss in _detect_negated_bosses(user_message)


def _detect_emotion(message: str) -> str | None:
    return detect_user_emotion(message).label


def _detect_tone_preference(message: str) -> str | None:
    if any(word in message for word in ("吐槽我", "稍微吐槽", "轻微吐槽", "毒舌", "可以骂", "别太温柔")):
        return "轻微吐槽"
    if any(word in message for word in ("安慰我", "温柔点", "别吐槽", "别骂")):
        return "安慰"
    return None


def _detect_user_name(message: str) -> str | None:
    match = re.search(r"(?:叫我|我叫)([A-Za-z0-9_\-\u4e00-\u9fff]{1,20})", message)
    return match.group(1) if match else None


def _detect_struggle(message: str, boss: str | None) -> str | None:
    if any(word in message for word in ("又死", "一直死", "打不过", "卡住")):
        return f"{boss or '当前关卡'}死亡循环"
    if "贪刀" in message:
        return f"{boss or '战斗'}贪刀"
    if "翻滚" in message:
        return f"{boss or '战斗'}翻滚时机"
    return None


def _detect_attitude_to_rei(message: str) -> str | None:
    if any(word in message for word in ("喜欢你", "想你", "陪我")):
        return "靠近"
    if any(word in message for word in ("别管我", "闭嘴", "烦你")):
        return "拉开距离"
    return None


def _build_summary(
    boss: str | None,
    struggle: str | None,
    emotional_state: str | None,
    preferred_tone: str | None,
    attitude: str | None,
) -> str | None:
    if boss and struggle:
        return f"玩家最近卡在 {boss}，问题像是 {struggle}"
    if preferred_tone:
        return f"玩家喜欢 Rei 用{preferred_tone}的方式回应"
    if emotional_state:
        return emotional_state
    if attitude:
        return f"玩家对 Rei 的态度：{attitude}"
    return None


def _normalize_profile_data(data: dict[str, Any]) -> dict[str, Any]:
    return normalize_mapping_values(data)


def _normalize_episode(episode: dict[str, Any]) -> dict[str, Any]:
    return normalize_mapping_values(episode)


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


def _is_fresh(value: str | None, now: datetime, ttl: timedelta) -> bool:
    timestamp = _parse_timestamp(value)
    return bool(timestamp and _is_within(timestamp, now, ttl))


def _is_within(timestamp: datetime, now: datetime, ttl: timedelta) -> bool:
    return now - ttl <= timestamp <= now + timedelta(minutes=5)


def _extract_value_from_line(text: str) -> str:
    return text.split("：", 1)[-1]
