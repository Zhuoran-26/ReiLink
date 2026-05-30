from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.modules.elden_ring_knowledge.terminology import normalize_mapping_values, normalize_terminology
from app.modules.memory.profile import PlayerMemory

PENDING_TYPES = {"game_progress", "user_preference", "emotional_pattern", "relationship_preference", "playstyle"}
PENDING_STATUSES = {"pending", "accepted", "ignored"}
SENSITIVE_PATTERN = re.compile(
    r"(api[_ -]?key|deepseek|authorization|bearer|token|密钥|密碼|密码|密碼|sk-[a-z0-9])",
    re.IGNORECASE,
)


@dataclass
class PendingMemory:
    id: str
    type: str
    text: str
    source: str
    confidence: float
    status: str
    created_at: str
    updated_at: str
    evidence: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return normalize_mapping_values(
            {
                "id": self.id,
                "type": self.type,
                "text": self.text,
                "source": self.source,
                "confidence": self.confidence,
                "status": self.status,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "evidence": self.evidence,
                "payload": self.payload,
            }
        )


class PendingMemoryQueue:
    def __init__(self, path: Path | None = None, player_memory: PlayerMemory | None = None) -> None:
        self.path = path or settings.pending_memories_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.player_memory = player_memory or PlayerMemory()

    def list(self, status: str | None = "pending") -> list[dict[str, Any]]:
        items = self._read()
        if status is None:
            return items
        return [item for item in items if item.get("status") == status]

    def generate_and_enqueue(
        self,
        user_message: str,
        assistant_reply: str,
        intent: str,
        timestamp: datetime,
        game_state_summary: dict[str, Any] | None = None,
        semantic_extraction: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        candidates = self.generate_candidates(
            user_message,
            assistant_reply,
            intent,
            timestamp,
            game_state_summary,
            semantic_extraction=semantic_extraction,
        )
        return self.enqueue(candidates)

    def generate_candidates(
        self,
        user_message: str,
        assistant_reply: str,
        intent: str,
        timestamp: datetime,
        game_state_summary: dict[str, Any] | None = None,
        semantic_extraction: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        del assistant_reply, intent
        normalized_message = normalize_terminology(user_message.strip())
        if not normalized_message or _contains_sensitive_text(normalized_message):
            return []

        now = _ensure_aware(timestamp).isoformat()
        game_summary = game_state_summary or {}
        evidence = {
            "user_message": normalized_message[:200],
            "game_state_summary": _brief_game_state(game_summary),
        }
        candidates: list[PendingMemory] = []

        if _mentions_short_guide_preference(normalized_message):
            candidates.append(
                PendingMemory(
                    id=str(uuid.uuid4()),
                    type="user_preference",
                    text="玩家喜欢简短的游戏攻略",
                    source="explicit_user_statement",
                    confidence=0.94,
                    status="pending",
                    created_at=now,
                    updated_at=now,
                    evidence=evidence,
                    payload={"preference": "喜欢简短的游戏攻略"},
                )
            )

        if _mentions_long_guide_preference(normalized_message):
            candidates.append(
                PendingMemory(
                    id=str(uuid.uuid4()),
                    type="user_preference",
                    text="玩家不喜欢长篇攻略",
                    source="explicit_user_statement",
                    confidence=0.95,
                    status="pending",
                    created_at=now,
                    updated_at=now,
                    evidence=evidence,
                    payload={"preference": "不喜欢长篇攻略"},
                )
            )

        if _mentions_spirit_ashes_preference(normalized_message):
            candidates.append(
                PendingMemory(
                    id=str(uuid.uuid4()),
                    type="playstyle",
                    text="玩家不喜欢召唤骨灰，倾向自己打",
                    source="explicit_user_statement",
                    confidence=0.95,
                    status="pending",
                    created_at=now,
                    updated_at=now,
                    evidence=evidence,
                    payload={"playstyle": "不召唤骨灰"},
                )
            )

        if _mentions_companion_style_preference(normalized_message):
            candidates.append(
                PendingMemory(
                    id=str(uuid.uuid4()),
                    type="relationship_preference",
                    text="玩家喜欢 Rei 克制但有回应",
                    source="explicit_user_statement",
                    confidence=0.9,
                    status="pending",
                    created_at=now,
                    updated_at=now,
                    evidence=evidence,
                    payload={"preferred_tone": "克制但有回应"},
                )
            )

        explicit_preference = _explicit_personal_preference(normalized_message)
        if explicit_preference:
            candidates.append(
                PendingMemory(
                    id=str(uuid.uuid4()),
                    type="user_preference",
                    text=f"玩家{explicit_preference}",
                    source="explicit_user_statement",
                    confidence=0.9,
                    status="pending",
                    created_at=now,
                    updated_at=now,
                    evidence=evidence,
                    payload={"preference": explicit_preference},
                )
            )

        semantic_candidate = _semantic_memory_candidate(semantic_extraction, now, evidence)
        if semantic_candidate:
            candidates.append(semantic_candidate)

        last_cleared_boss = _boss_name(game_summary.get("last_cleared_boss"))
        current_activity = str(game_summary.get("current_activity") or "")
        if current_activity == "boss_cleared" and last_cleared_boss:
            candidates.append(
                PendingMemory(
                    id=str(uuid.uuid4()),
                    type="game_progress",
                    text=f"玩家已经打过{last_cleared_boss}",
                    source="game_session",
                    confidence=0.9,
                    status="pending",
                    created_at=now,
                    updated_at=now,
                    evidence=evidence,
                    payload={"boss": last_cleared_boss, "progress_status": "cleared"},
                )
            )

        return [
            candidate.as_dict()
            for candidate in candidates
            if candidate.confidence >= _minimum_candidate_confidence(candidate)
        ]

    def enqueue(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not candidates:
            return []
        items = self._read()
        created: list[dict[str, Any]] = []
        for candidate in candidates:
            normalized = _normalize_pending_item(candidate)
            if not normalized:
                continue
            if self._is_duplicate(normalized, items + created):
                continue
            items.append(normalized)
            created.append(normalized)
        if created:
            self._write(items)
        return created

    def accept(self, memory_id: str) -> dict[str, Any]:
        items = self._read()
        now = datetime.now(timezone.utc)
        for item in items:
            if item.get("id") != memory_id:
                continue
            if item.get("status") != "accepted":
                self.player_memory.apply_pending_memory(item, timestamp=now)
                item["status"] = "accepted"
                item["updated_at"] = now.isoformat()
                self._write(items)
            return item
        raise KeyError(memory_id)

    def ignore(self, memory_id: str) -> dict[str, Any]:
        items = self._read()
        now = datetime.now(timezone.utc).isoformat()
        for item in items:
            if item.get("id") != memory_id:
                continue
            item["status"] = "ignored"
            item["updated_at"] = now
            self._write(items)
            return item
        raise KeyError(memory_id)

    def clear(self) -> None:
        items = self._read()
        now = datetime.now(timezone.utc).isoformat()
        for item in items:
            if item.get("status") == "pending":
                item["status"] = "ignored"
                item["updated_at"] = now
        self._write(items)

    def clear_all(self) -> None:
        self.path.write_text("", encoding="utf-8")

    def _is_duplicate(self, candidate: dict[str, Any], items: list[dict[str, Any]]) -> bool:
        candidate_text = _similarity_text(candidate)
        for item in items:
            if item.get("status") not in {"pending", "accepted"}:
                continue
            if item.get("type") != candidate.get("type"):
                continue
            if _similar(candidate_text, _similarity_text(item)):
                return True
        for episode in self.player_memory.recent_episodes(limit=100):
            summary = str(episode.get("summary") or "")
            if summary and _similar(candidate_text, _normalize_text(summary)):
                return True
        return False

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        items: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = _normalize_pending_item(json.loads(line))
            except json.JSONDecodeError:
                continue
            if item:
                items.append(item)
        return items

    def _write(self, items: list[dict[str, Any]]) -> None:
        text = "\n".join(json.dumps(_normalize_pending_item(item) or item, ensure_ascii=False) for item in items)
        self.path.write_text(f"{text}\n" if text else "", encoding="utf-8")


def _normalize_pending_item(item: dict[str, Any]) -> dict[str, Any] | None:
    normalized = normalize_mapping_values(item)
    memory_type = str(normalized.get("type") or "")
    status = str(normalized.get("status") or "")
    if memory_type not in PENDING_TYPES or status not in PENDING_STATUSES:
        return None
    text = normalize_terminology(str(normalized.get("text") or "")).strip()
    if not text or _contains_sensitive_text(text):
        return None
    return {
        "id": str(normalized.get("id") or uuid.uuid4()),
        "type": memory_type,
        "text": text,
        "source": str(normalized.get("source") or "conversation"),
        "confidence": float(normalized.get("confidence") or 0),
        "status": status,
        "created_at": str(normalized.get("created_at") or datetime.now(timezone.utc).isoformat()),
        "updated_at": str(normalized.get("updated_at") or datetime.now(timezone.utc).isoformat()),
        "evidence": normalize_mapping_values(normalized.get("evidence") or {}),
        "payload": normalize_mapping_values(normalized.get("payload") or {}),
    }


def _contains_sensitive_text(text: str) -> bool:
    return bool(SENSITIVE_PATTERN.search(text))


SEMANTIC_MEMORY_TYPE_MAP = {
    "guide_preference": "user_preference",
    "playstyle_preference": "playstyle",
    "persona_preference": "relationship_preference",
    "personal_preference": "user_preference",
    "game_progress": "game_progress",
}


def _semantic_memory_candidate(
    semantic_extraction: dict[str, Any] | None,
    created_at: str,
    evidence: dict[str, Any],
) -> PendingMemory | None:
    if not isinstance(semantic_extraction, dict):
        return None
    final_decision = semantic_extraction.get("final_decision")
    if not isinstance(final_decision, dict):
        return None
    candidate = final_decision.get("memory_candidate")
    if not isinstance(candidate, dict) or not candidate.get("should_create_pending"):
        return None
    confidence = float(candidate.get("confidence") or 0)
    source_type = str(candidate.get("type") or "none")
    min_confidence = 0.65 if source_type == "persona_preference" else 0.75
    if confidence < min_confidence:
        return None
    pending_type = SEMANTIC_MEMORY_TYPE_MAP.get(source_type)
    text = normalize_terminology(str(candidate.get("text") or "")).strip()
    if not pending_type or not text or _contains_sensitive_text(text):
        return None
    return PendingMemory(
        id=str(uuid.uuid4()),
        type=pending_type,
        text=text,
        source="semantic_extraction",
        confidence=confidence,
        status="pending",
        created_at=created_at,
        updated_at=created_at,
        evidence={**evidence, "semantic_reason": str(candidate.get("reason") or "")[:160]},
        payload=_semantic_payload(source_type, text),
    )


def _minimum_candidate_confidence(candidate: PendingMemory) -> float:
    if candidate.source == "semantic_extraction" and candidate.type == "relationship_preference":
        return 0.65
    return 0.85


def _semantic_payload(source_type: str, text: str) -> dict[str, Any]:
    if source_type == "playstyle_preference":
        return {"playstyle": text.removeprefix("玩家")}
    if source_type == "persona_preference":
        return {"preferred_tone": text.removeprefix("玩家")}
    if source_type in {"guide_preference", "personal_preference"}:
        return {"preference": text.removeprefix("玩家")}
    if source_type == "game_progress":
        return {"progress_status": "semantic_candidate", "summary": text}
    return {}


def _mentions_short_guide_preference(message: str) -> bool:
    compact = _normalize_text(message)
    return bool(re.search(r"(?:喜欢|喜歡|希望|想要|尽量|盡量).{0,8}(?:简短|短一点|短點|一句|少一点|少點).{0,8}(?:攻略|提醒|回答)", compact))


def _mentions_long_guide_preference(message: str) -> bool:
    compact = _normalize_text(message)
    patterns = (
        r"不(?:想|要|喜欢|喜歡).{0,8}(?:长篇|長篇|详细|攻略)",
        r"(?:别|不要).{0,8}(?:长篇|長篇|攻略站|详细攻略)",
        r"(?:少|少一点|少點).{0,8}(?:攻略|长篇|長篇)",
        r"不喜欢攻略站",
    )
    return any(re.search(pattern, compact) for pattern in patterns)


def _mentions_spirit_ashes_preference(message: str) -> bool:
    compact = _normalize_text(message)
    patterns = (
        r"不(?:想|要|喜欢|喜歡|用|召).{0,8}(?:召唤|召喚|骨灰)",
        r"(?:不用|不召|别召|不要召).{0,4}骨灰",
        r"不想叫骨灰",
    )
    return any(re.search(pattern, compact) for pattern in patterns)


def _mentions_companion_style_preference(message: str) -> bool:
    compact = _normalize_text(message)
    return bool(re.search(r"(?:喜欢|希望).{0,8}(?:克制|冷淡|安静).{0,8}(?:回应|陪|说话)", compact))


def _explicit_personal_preference(message: str) -> str | None:
    compact = _normalize_text(message)
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


def _explicitly_mentions_current_attempt(message: str) -> bool:
    compact = _normalize_text(message)
    return bool(re.search(r"(?:现在|最近|正在|卡在|打不过|打不過).{0,10}(?:打|卡|boss|女武神|大树守卫|恶兆|margit|拉塔恩|玛莲妮亚)", compact))


def _boss_name(value: Any) -> str | None:
    if isinstance(value, dict):
        name = value.get("name")
    else:
        name = value
    text = normalize_terminology(str(name or "")).strip()
    return text or None


def _brief_game_state(game_state: dict[str, Any]) -> str:
    current_boss = _boss_name(game_state.get("current_boss"))
    parts = [
        f"current_game={game_state.get('current_game') or 'unknown'}",
        f"current_boss={current_boss or 'none'}",
        f"activity={game_state.get('current_activity') or 'none'}",
        f"last_attempted={_boss_name(game_state.get('last_attempted_boss')) or 'none'}",
        f"last_cleared={_boss_name(game_state.get('last_cleared_boss')) or 'none'}",
    ]
    return "; ".join(parts)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", normalize_terminology(text).lower())


def _similarity_text(item: dict[str, Any]) -> str:
    return _normalize_text(f"{item.get('type', '')}:{item.get('text', '')}")


def _similar(left: str, right: str) -> bool:
    return left == right or SequenceMatcher(None, left, right).ratio() >= 0.92


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
