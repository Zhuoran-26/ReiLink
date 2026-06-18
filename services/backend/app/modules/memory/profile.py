from __future__ import annotations

import json
import re
import uuid
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
    long_term_memories: list[dict[str, Any]] = field(default_factory=list)
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
            "long_term_memories": self.long_term_memories,
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

    def retrieve_prompt_memory(
        self,
        *,
        user_message: str,
        current_game: str | None = None,
        current_boss: str | None = None,
        input_source: str = "text",
        max_items: int = 4,
        token_budget: int = 320,
        update_usage: bool = False,
        now: datetime | None = None,
    ) -> Any:
        from app.modules.memory.retrieval import MemoryRetriever

        return MemoryRetriever(self).build_prompt_block(
            user_message=user_message,
            current_game=current_game,
            current_boss=current_boss,
            input_source=input_source,
            max_items=max_items,
            token_budget=token_budget,
            update_usage=update_usage,
            now=now,
        )

    def mark_long_term_memories_used(self, memory_ids: list[str], timestamp: datetime | None = None) -> None:
        ids = {str(memory_id) for memory_id in memory_ids if memory_id}
        if not ids:
            return
        timestamp = _ensure_aware(timestamp or datetime.now(timezone.utc))
        profile = self.load_profile()
        changed = False
        updated_memories: list[dict[str, Any]] = []
        for memory in profile.long_term_memories:
            if not isinstance(memory, dict):
                updated_memories.append(memory)
                continue
            item = normalize_mapping_values(memory)
            if str(item.get("id") or "") in ids and item.get("is_active") is not False:
                item["use_count"] = int(item.get("use_count") or 0) + 1
                item["last_used_at"] = timestamp.isoformat()
                changed = True
            updated_memories.append(item)
        if changed:
            profile.long_term_memories = updated_memories
            profile.last_seen_at = timestamp.isoformat()
            self.save_profile(profile)

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

        for memory in reversed(profile.long_term_memories[-5:]):
            if not isinstance(memory, dict) or memory.get("is_active") is False:
                continue
            text = normalize_terminology(str(memory.get("user_visible_text") or memory.get("summary") or "")).strip()
            if not text:
                continue
            lines.append(
                MemoryPromptLine(
                    "profile",
                    str(memory.get("type") or "long_term_memory"),
                    f"已确认记忆：{text}",
                    str(memory.get("updated_at") or memory.get("created_at") or ""),
                )
            )
            if len([line for line in lines if line.source == "profile"]) >= 2:
                break

        latest_episode = next(
            (
                episode
                for episode in reversed(self.recent_episodes(limit=5))
                if episode.get("summary")
                and not str(episode.get("intent") or "").startswith("pending_")
                and _is_fresh(episode.get("timestamp"), now, BOSS_FRESHNESS)
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
                profile.long_term_memories,
                self.recent_episodes(limit=1),
            ]
        )

    def _episode_summary_exists(self, summary: str) -> bool:
        normalized = normalize_terminology(summary).strip()
        if not normalized:
            return False
        return any(
            normalize_terminology(str(episode.get("summary") or "")).strip() == normalized
            for episode in self.recent_episodes(limit=100)
        )

    def apply_pending_memory(self, pending: dict[str, Any], timestamp: datetime | None = None) -> dict[str, Any] | None:
        timestamp = _ensure_aware(timestamp or datetime.now(timezone.utc))
        normalized = normalize_mapping_values(pending)
        memory_type = str(normalized.get("type") or "")
        text = normalize_terminology(str(normalized.get("summary") or normalized.get("text") or "")).strip()
        payload = normalize_mapping_values(normalized.get("payload") or {})
        evidence = normalize_mapping_values(normalized.get("evidence") or {})
        if not text or normalized.get("status") not in {"pending", "accepted"} or memory_type == "do_not_remember":
            return None

        profile = self.load_profile()
        boss = normalize_terminology(str(payload.get("boss") or "")).strip() or None
        progress_status = str(payload.get("progress_status") or "")
        preferred_tone = normalize_terminology(str(payload.get("preferred_tone") or "")).strip() or None
        long_term_memory = _long_term_memory_from_pending(normalized, text, timestamp)
        existing_memory = _find_long_term_memory(profile.long_term_memories, long_term_memory)
        if existing_memory:
            long_term_memory = existing_memory
        else:
            profile.long_term_memories = [*profile.long_term_memories, long_term_memory]

        if memory_type == "game_progress":
            if not profile.favorite_game:
                profile.favorite_game = "Elden Ring"
                profile.memory_updated_at["favorite_game"] = timestamp.isoformat()
            if boss and progress_status in {"current", "attempting", "failed"}:
                profile.current_boss = boss
                profile.memory_updated_at["current_boss"] = timestamp.isoformat()
            elif boss and progress_status == "cleared" and profile.current_boss == boss:
                profile.current_boss = None
                profile.memory_updated_at["current_boss"] = timestamp.isoformat()
        elif memory_type in {"interaction_preference", "relationship_preference", "user_preference"}:
            preference = normalize_terminology(str(preferred_tone or payload.get("preference") or text.removeprefix("玩家"))).strip()
            if preference:
                profile.preferred_tone = preference
                profile.likes_teasing = "吐槽" in preference
                profile.memory_updated_at["preferred_tone"] = timestamp.isoformat()
        elif memory_type == "emotional_pattern":
            emotional_state = normalize_terminology(str(payload.get("emotional_state") or text)).strip()
            if emotional_state and (not profile.emotional_notes or profile.emotional_notes[-1] != emotional_state):
                profile.emotional_notes = [*profile.emotional_notes[-8:], emotional_state]
                profile.memory_updated_at["emotional_notes"] = timestamp.isoformat()

        profile.last_seen_at = timestamp.isoformat()
        self.save_profile(profile)

        episode = _normalize_episode(
            {
                "timestamp": timestamp.isoformat(),
                "intent": f"pending_{memory_type}",
                "boss": boss if memory_type == "game_progress" and progress_status != "cleared" else None,
                "struggle": None,
                "preferred_tone": preferred_tone,
                "skill_level": None,
                "emotional_state": payload.get("emotional_state"),
                "topic": boss or memory_type,
                "attitude_to_rei": None,
                "user_name": None,
                "user_message_sample": str(evidence.get("input_summary") or normalized.get("evidence_summary") or "")[:120],
                "assistant_reply_sample": "",
                "summary": text,
            }
        )
        if not self._episode_summary_exists(text):
            self._append_episode(episode)
        return long_term_memory

    def deactivate_long_term_memory(self, memory_id: str, timestamp: datetime | None = None) -> dict[str, Any]:
        timestamp = _ensure_aware(timestamp or datetime.now(timezone.utc))
        profile = self.load_profile()
        updated_memory: dict[str, Any] | None = None
        memories: list[dict[str, Any]] = []
        for memory in profile.long_term_memories:
            if not isinstance(memory, dict):
                memories.append(memory)
                continue
            item = normalize_mapping_values(memory)
            if str(item.get("id") or "") == memory_id:
                item["is_active"] = False
                item["updated_at"] = timestamp.isoformat()
                updated_memory = item
            memories.append(item)
        if not updated_memory:
            raise KeyError(memory_id)
        profile.long_term_memories = memories
        _reconcile_profile_fields_after_deactivation(profile, updated_memory, timestamp)
        profile.last_seen_at = timestamp.isoformat()
        self.save_profile(profile)
        return updated_memory

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


def _long_term_memory_from_pending(pending: dict[str, Any], text: str, timestamp: datetime) -> dict[str, Any]:
    existing_id = str(pending.get("long_term_memory_id") or "") or None
    created_at = timestamp.isoformat()
    return normalize_mapping_values(
        {
            "id": existing_id or f"ltm-{uuid.uuid4()}",
            "created_at": created_at,
            "updated_at": created_at,
            "type": str(pending.get("type") or "unknown"),
            "summary": text,
            "user_visible_text": text,
            "source_candidate_id": str(pending.get("id") or ""),
            "is_active": True,
            "related_game": pending.get("related_game"),
            "related_entity": pending.get("related_entity"),
            "last_used_at": None,
            "use_count": 0,
            "retrieval_tags": _retrieval_tags_for_memory(str(pending.get("type") or "unknown"), text, pending.get("payload") or {}),
            "deletion_status": "active",
        }
    )


def _long_term_memory_exists(memories: list[dict[str, Any]], candidate: dict[str, Any]) -> bool:
    return _find_long_term_memory(memories, candidate) is not None


def _find_long_term_memory(memories: list[dict[str, Any]], candidate: dict[str, Any]) -> dict[str, Any] | None:
    candidate_source_id = str(candidate.get("source_candidate_id") or "")
    candidate_type = str(candidate.get("type") or "")
    candidate_summary = normalize_terminology(str(candidate.get("summary") or "")).strip()
    for memory in memories:
        if not isinstance(memory, dict):
            continue
        if candidate_source_id and str(memory.get("source_candidate_id") or "") == candidate_source_id:
            return normalize_mapping_values(memory)
        if (
            str(memory.get("type") or "") == candidate_type
            and normalize_terminology(str(memory.get("summary") or "")).strip() == candidate_summary
        ):
            return normalize_mapping_values(memory)
    return None


def _reconcile_profile_fields_after_deactivation(
    profile: UserProfile,
    deactivated_memory: dict[str, Any],
    timestamp: datetime,
) -> None:
    memory_type = str(deactivated_memory.get("type") or "")
    if memory_type in {"interaction_preference", "relationship_preference", "user_preference"}:
        active_interaction = _latest_active_memory(
            profile.long_term_memories,
            {"interaction_preference", "relationship_preference", "user_preference"},
        )
        if active_interaction:
            profile.preferred_tone = _profile_preference_from_memory(active_interaction)
            profile.likes_teasing = "吐槽" in str(profile.preferred_tone or "")
            profile.memory_updated_at["preferred_tone"] = timestamp.isoformat()
        else:
            profile.preferred_tone = None
            profile.likes_teasing = None
            profile.memory_updated_at.pop("preferred_tone", None)
    if memory_type == "emotional_pattern":
        text = normalize_terminology(str(deactivated_memory.get("summary") or deactivated_memory.get("user_visible_text") or "")).strip()
        normalized_notes = [note for note in profile.emotional_notes if normalize_terminology(str(note)).strip() != text]
        if len(normalized_notes) != len(profile.emotional_notes):
            profile.emotional_notes = normalized_notes
            if profile.emotional_notes:
                profile.memory_updated_at["emotional_notes"] = timestamp.isoformat()
            else:
                profile.memory_updated_at.pop("emotional_notes", None)


def _latest_active_memory(memories: list[dict[str, Any]], memory_types: set[str]) -> dict[str, Any] | None:
    active = [
        normalize_mapping_values(memory)
        for memory in memories
        if isinstance(memory, dict)
        and memory.get("is_active") is not False
        and str(memory.get("type") or "") in memory_types
    ]
    if not active:
        return None
    return max(active, key=lambda memory: str(memory.get("updated_at") or memory.get("created_at") or ""))


def _profile_preference_from_memory(memory: dict[str, Any]) -> str:
    text = normalize_terminology(str(memory.get("user_visible_text") or memory.get("summary") or "")).strip()
    return text.removeprefix("玩家").strip()


def _retrieval_tags_for_memory(memory_type: str, text: str, payload: dict[str, Any]) -> list[str]:
    normalized = normalize_terminology(text).lower()
    tags = [memory_type]
    for marker, tag in (
        ("boss", "boss"),
        ("首领", "boss"),
        ("首領", "boss"),
        ("探索", "exploration"),
        ("硬打", "boss_pacing"),
        ("攻略", "guide"),
        ("剧透", "spoiler"),
        ("劇透", "spoiler"),
        ("短", "short_reply"),
        ("长篇", "guide_length"),
        ("長篇", "guide_length"),
        ("骨灰", "summon_preference"),
        ("语音", "voice"),
        ("語音", "voice"),
    ):
        if marker in normalized and tag not in tags:
            tags.append(tag)
    for value in payload.values():
        value_text = normalize_terminology(str(value)).lower()
        if "短" in value_text and "short_reply" not in tags:
            tags.append("short_reply")
        if ("剧透" in value_text or "劇透" in value_text) and "spoiler" not in tags:
            tags.append("spoiler")
    return tags[:8]


def _normalize_profile_data(data: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_mapping_values(data)
    memories = normalized.get("long_term_memories")
    if isinstance(memories, list):
        normalized["long_term_memories"] = [
            _normalize_long_term_memory_item(item)
            for item in memories
            if isinstance(item, dict)
        ]
    return normalized


def _normalize_long_term_memory_item(item: dict[str, Any]) -> dict[str, Any]:
    memory = normalize_mapping_values(item)
    text = normalize_terminology(str(memory.get("user_visible_text") or memory.get("summary") or "")).strip()
    memory.setdefault("summary", text)
    memory.setdefault("user_visible_text", text)
    memory.setdefault("is_active", True)
    memory.setdefault("last_used_at", None)
    memory["use_count"] = int(memory.get("use_count") or 0)
    retrieval_tags = memory.get("retrieval_tags")
    if not isinstance(retrieval_tags, list):
        retrieval_tags = _retrieval_tags_for_memory(str(memory.get("type") or "unknown"), text, {})
    memory["retrieval_tags"] = [str(tag)[:40] for tag in retrieval_tags if str(tag).strip()][:8]
    memory.setdefault("deletion_status", "active")
    return memory


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
