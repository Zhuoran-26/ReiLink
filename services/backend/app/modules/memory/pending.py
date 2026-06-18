from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.modules.elden_ring_knowledge.terminology import normalize_mapping_values, normalize_terminology
from app.modules.memory.candidate_check import MemoryCandidateCheck, check_memory_candidate
from app.modules.memory.profile import PlayerMemory

CANDIDATE_MEMORY_TYPES = {
    "gameplay_preference",
    "interaction_preference",
    "emotional_pattern",
    "accessibility_preference",
    "do_not_remember",
    "unknown",
}
LEGACY_MEMORY_TYPE_MAP = {
    "game_progress": "unknown",
    "user_preference": "interaction_preference",
    "relationship_preference": "interaction_preference",
    "playstyle": "gameplay_preference",
}
PENDING_TYPES = CANDIDATE_MEMORY_TYPES | set(LEGACY_MEMORY_TYPE_MAP)
PENDING_STATUSES = {"pending", "accepted", "ignored", "expired", "rejected_by_guard"}
PENDING_SOURCES = {
    "conversation",
    "explicit_user_statement",
    "semantic_extraction",
    "game_session",
    "voice_confirmed",
    "voice_direct",
    "assistant",
    "proactive",
}
GUARD_REASONS = {
    "allow_candidate",
    "reject_candidate",
    "ignore_no_memory_intent",
    "requires_confirmation",
    "explicit_user_memory_request",
    "session_event_only",
    "persona_drift_blocked",
    "sensitive_secret_blocked",
    "assistant_source_blocked",
    "duplicate_candidate",
    "do_not_remember",
}
CANDIDATE_TTL = timedelta(days=30)
SENSITIVE_PATTERN = re.compile(
    r"(api[_ -]?key|openai[_ -]?api[_ -]?key|deepseek|authorization|bearer|token|密钥|密碼|密码|ak-[a-z0-9]|sk-[a-z0-9])",
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
    source_event_id: str | None = None
    long_term_memory_id: str | None = None
    expires_at: str | None = None
    summary: str | None = None
    evidence_summary: str | None = None
    requires_confirmation: bool = True
    guard_reason: str = "requires_confirmation"
    privacy_level: str = "normal"
    related_game: str | None = None
    related_entity: str | None = None
    from_voice: bool = False
    from_proactive: bool = False
    from_assistant: bool = False
    confirmation_intent: str = "implicit"

    def as_dict(self) -> dict[str, Any]:
        summary = normalize_terminology(str(self.summary or self.text)).strip()
        created_at = self.created_at
        expires_at = self.expires_at or _default_expires_at(created_at)
        return normalize_mapping_values(
            {
                "id": self.id,
                "type": self.type,
                "source": self.source,
                "source_event_id": self.source_event_id,
                "long_term_memory_id": self.long_term_memory_id,
                "created_at": created_at,
                "expires_at": expires_at,
                "summary": summary,
                "text": summary,
                "evidence_summary": self.evidence_summary or "安全摘要：用户表达了可确认的记忆候选",
                "confidence": self.confidence,
                "requires_confirmation": self.requires_confirmation,
                "status": self.status,
                "updated_at": self.updated_at,
                "guard_reason": self.guard_reason,
                "privacy_level": self.privacy_level,
                "related_game": self.related_game,
                "related_entity": self.related_entity,
                "from_voice": self.from_voice,
                "from_proactive": self.from_proactive,
                "from_assistant": self.from_assistant,
                "confirmation_intent": self.confirmation_intent,
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
        items = self._expire_pending_items(self._read())
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
        input_source: str | None = None,
        source_event_id: str | None = None,
        from_assistant: bool = False,
        from_proactive: bool = False,
    ) -> list[dict[str, Any]]:
        candidates = self.generate_candidates(
            user_message,
            assistant_reply,
            intent,
            timestamp,
            game_state_summary,
            semantic_extraction=semantic_extraction,
            input_source=input_source,
            source_event_id=source_event_id,
            from_assistant=from_assistant,
            from_proactive=from_proactive,
        )
        return self.enqueue(candidates)

    def process_user_message(
        self,
        user_message: str,
        assistant_reply: str,
        intent: str,
        timestamp: datetime,
        game_state_summary: dict[str, Any] | None = None,
        semantic_extraction: dict[str, Any] | None = None,
        input_source: str | None = None,
        source_event_id: str | None = None,
        from_assistant: bool = False,
        from_proactive: bool = False,
    ) -> dict[str, Any]:
        created = self.generate_and_enqueue(
            user_message,
            assistant_reply,
            intent,
            timestamp,
            game_state_summary,
            semantic_extraction=semantic_extraction,
            input_source=input_source,
            source_event_id=source_event_id,
            from_assistant=from_assistant,
            from_proactive=from_proactive,
        )
        auto_saved: dict[str, Any] | None = None
        for item in created:
            if _should_auto_save(item):
                auto_saved = self.accept(str(item["id"]))
                break
        pending = self.list()
        if auto_saved:
            return _memory_update_result(
                status="auto_saved",
                item=auto_saved,
                pending_count=len(pending),
            )
        pending_created = [item for item in created if item.get("status") == "pending"]
        if pending_created:
            return _memory_update_result(
                status="pending",
                item=pending_created[0],
                pending_count=len(pending),
            )
        return _memory_update_result(status="none", pending_count=len(pending))

    def generate_candidates(
        self,
        user_message: str,
        assistant_reply: str,
        intent: str,
        timestamp: datetime,
        game_state_summary: dict[str, Any] | None = None,
        semantic_extraction: dict[str, Any] | None = None,
        input_source: str | None = None,
        source_event_id: str | None = None,
        from_assistant: bool = False,
        from_proactive: bool = False,
    ) -> list[dict[str, Any]]:
        del assistant_reply, intent
        normalized_message = normalize_terminology(user_message.strip())
        if not normalized_message:
            return []

        now_dt = _ensure_aware(timestamp)
        now = now_dt.isoformat()
        input_source_value = _candidate_input_source(input_source, semantic_extraction)
        from_voice = input_source_value in {"voice_confirmed", "voice_direct"}
        game_summary = game_state_summary or {}
        evidence = _safe_evidence(
            {
                "source_channel": input_source_value,
                "game_state_summary": _brief_game_state(game_summary),
            }
        )

        if from_assistant or from_proactive:
            return [
                _rejected_candidate(
                    created_at=now,
                    source="proactive" if from_proactive else "assistant",
                    source_event_id=source_event_id,
                    summary="非用户来源内容不会写入记忆",
                    guard_reason="assistant_source_blocked",
                    from_voice=from_voice,
                    from_assistant=from_assistant,
                    from_proactive=from_proactive,
                ).as_dict()
            ]

        if _contains_sensitive_text(normalized_message):
            return [
                _rejected_candidate(
                    created_at=now,
                    source=_candidate_source(input_source_value, "explicit_user_statement"),
                    source_event_id=source_event_id,
                    summary="内容包含敏感凭据，已阻止记忆",
                    guard_reason="sensitive_secret_blocked",
                    privacy_level="secret",
                    from_voice=from_voice,
                ).as_dict()
            ]

        compact = _normalize_text(normalized_message)
        if _negative_memory_request(compact):
            return [
                _rejected_candidate(
                    created_at=now,
                    source=_candidate_source(input_source_value, "explicit_user_statement"),
                    source_event_id=source_event_id,
                    type="do_not_remember",
                    summary="用户要求不要记住这次内容",
                    guard_reason="do_not_remember",
                    from_voice=from_voice,
                    confirmation_intent=_confirmation_intent(input_source_value, explicit=True),
                ).as_dict()
            ]

        if _persona_drift_request(compact):
            return [
                _rejected_candidate(
                    created_at=now,
                    source=_candidate_source(input_source_value, "explicit_user_statement"),
                    source_event_id=source_event_id,
                    summary="人格变更类记忆请求已被阻止",
                    guard_reason="persona_drift_blocked",
                    from_voice=from_voice,
                    confirmation_intent=_confirmation_intent(input_source_value, explicit=True),
                ).as_dict()
            ]

        base = {
            "created_at": now,
            "updated_at": now,
            "expires_at": (now_dt + CANDIDATE_TTL).isoformat(),
            "source": _candidate_source(input_source_value, "explicit_user_statement"),
            "source_event_id": source_event_id,
            "evidence": evidence,
            "from_voice": from_voice,
            "from_proactive": False,
            "from_assistant": False,
        }
        candidates: list[PendingMemory] = []
        memory_check = check_memory_candidate(
            normalized_message,
            input_source=input_source_value,
            game_state_summary=game_summary,
        )
        memory_check_created = False

        if memory_check.suggested_action == "reject":
            return [
                _rejected_candidate(
                    created_at=now,
                    source=_candidate_source(input_source_value, "semantic_extraction"),
                    source_event_id=source_event_id,
                    summary="记忆候选检查未通过",
                    guard_reason=_memory_check_reject_reason(memory_check),
                    from_voice=from_voice,
                    confirmation_intent=_confirmation_intent(input_source_value, explicit=memory_check.explicit_request),
                ).as_dict()
            ]

        if memory_check.should_create:
            candidates.append(
                _candidate_from_memory_check(
                    memory_check,
                    created_at=now,
                    updated_at=now,
                    expires_at=(now_dt + CANDIDATE_TTL).isoformat(),
                    source=_candidate_source(input_source_value, "semantic_extraction"),
                    source_event_id=source_event_id,
                    evidence=_safe_evidence({**evidence, **memory_check.as_evidence()}),
                    input_source=input_source_value,
                    from_voice=from_voice,
                )
            )
            memory_check_created = True

        if not memory_check_created and (
            _mentions_short_guide_preference(normalized_message) or _mentions_short_reply_preference(normalized_message)
        ):
            candidates.append(
                _pending_candidate(
                    summary="玩家偏好简短回答和简短游戏提醒",
                    type="interaction_preference",
                    confidence=0.94,
                    guard_reason="requires_confirmation",
                    confirmation_intent=_confirmation_intent(input_source_value),
                    evidence_summary="用户表达了回答长度偏好：简短、低打扰",
                    payload={"preference": "回答尽量简短"},
                    **base,
                )
            )

        if not memory_check_created and _mentions_long_guide_preference(normalized_message):
            candidates.append(
                _pending_candidate(
                    summary="玩家不喜欢长篇攻略",
                    type="interaction_preference",
                    confidence=0.95,
                    guard_reason="requires_confirmation",
                    confirmation_intent=_confirmation_intent(input_source_value),
                    evidence_summary="用户表达了攻略呈现偏好：避免长篇攻略",
                    payload={"preference": "不喜欢长篇攻略"},
                    **base,
                )
            )

        if not memory_check_created and _mentions_spirit_ashes_preference(normalized_message):
            candidates.append(
                _pending_candidate(
                    summary="玩家不喜欢召唤骨灰，倾向自己打",
                    type="gameplay_preference",
                    confidence=0.95,
                    guard_reason="requires_confirmation",
                    confirmation_intent=_confirmation_intent(input_source_value),
                    evidence_summary="用户表达了玩法偏好：倾向不召唤骨灰",
                    payload={"playstyle": "不召唤骨灰"},
                    **base,
                )
            )

        if not memory_check_created and _mentions_companion_style_preference(normalized_message):
            candidates.append(
                _pending_candidate(
                    summary="玩家偏好 Rei 回应克制、低打扰",
                    type="interaction_preference",
                    confidence=0.9,
                    guard_reason="requires_confirmation",
                    confirmation_intent=_confirmation_intent(input_source_value),
                    evidence_summary="用户表达了互动偏好：克制但有回应",
                    payload={"preferred_tone": "克制、低打扰"},
                    **base,
                )
            )

        explicit_preference = _explicit_personal_preference(normalized_message)
        if explicit_preference and not memory_check_created:
            candidates.append(
                _pending_candidate(
                    summary=f"玩家{explicit_preference}",
                    type="unknown",
                    confidence=0.9,
                    guard_reason="explicit_user_memory_request",
                    confirmation_intent=_confirmation_intent(input_source_value, explicit=True),
                    evidence_summary="用户提出了显式记忆请求",
                    payload={"preference": explicit_preference},
                    **base,
                )
            )

        playstyle_preference = _explicit_boss_exploration_preference(normalized_message)
        if playstyle_preference and not memory_check_created:
            candidates.append(
                _pending_candidate(
                    summary=f"玩家{playstyle_preference}",
                    type="gameplay_preference",
                    confidence=0.94,
                    guard_reason="explicit_user_memory_request",
                    confirmation_intent=_confirmation_intent(input_source_value, explicit=True),
                    evidence_summary="用户提出了玩法偏好的显式记忆请求",
                    payload={"playstyle": playstyle_preference},
                    **base,
                )
            )

        spoiler_preference = _spoiler_preference(normalized_message)
        if spoiler_preference and not memory_check_created:
            candidates.append(
                _pending_candidate(
                    summary=spoiler_preference,
                    type="gameplay_preference",
                    confidence=0.92,
                    guard_reason="requires_confirmation",
                    confirmation_intent=_confirmation_intent(input_source_value),
                    evidence_summary="用户表达了剧透边界偏好",
                    payload={"playstyle": "避免剧透，除非主动询问"},
                    **base,
                )
            )

        accessibility_preference = _accessibility_preference(normalized_message)
        if accessibility_preference and not memory_check_created:
            candidates.append(
                _pending_candidate(
                    summary=accessibility_preference,
                    type="accessibility_preference",
                    confidence=0.9,
                    guard_reason="requires_confirmation",
                    confirmation_intent=_confirmation_intent(input_source_value),
                    evidence_summary="用户表达了可访问性或舒适度偏好",
                    payload={"preference": accessibility_preference.removeprefix("玩家")},
                    **base,
                )
            )

        semantic_candidate = _semantic_memory_candidate(
            semantic_extraction,
            now,
            evidence,
            input_source=input_source_value,
            source_event_id=source_event_id,
            from_voice=from_voice,
        )
        if semantic_candidate:
            candidates.append(semantic_candidate)

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
        items = self._expire_pending_items(self._read())
        now = datetime.now(timezone.utc)
        for item in items:
            if item.get("id") != memory_id:
                continue
            if item.get("status") == "pending":
                long_term_memory = self.player_memory.apply_pending_memory(item, timestamp=now)
                if long_term_memory:
                    item["long_term_memory_id"] = long_term_memory.get("id")
                item["status"] = "accepted"
                item["requires_confirmation"] = False
                item["updated_at"] = now.isoformat()
                self._write(items)
            return item
        raise KeyError(memory_id)

    def ignore(self, memory_id: str) -> dict[str, Any]:
        items = self._expire_pending_items(self._read())
        now = datetime.now(timezone.utc).isoformat()
        for item in items:
            if item.get("id") != memory_id:
                continue
            if item.get("status") == "pending":
                item["status"] = "ignored"
                item["requires_confirmation"] = False
                item["updated_at"] = now
                self._write(items)
            return item
        raise KeyError(memory_id)

    def clear(self) -> None:
        items = self._expire_pending_items(self._read())
        now = datetime.now(timezone.utc).isoformat()
        for item in items:
            if item.get("status") == "pending":
                item["status"] = "ignored"
                item["requires_confirmation"] = False
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

    def _expire_pending_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        changed = False
        for item in items:
            if item.get("status") != "pending":
                continue
            expires_at = _parse_timestamp(str(item.get("expires_at") or ""))
            if expires_at and expires_at < now:
                item["status"] = "expired"
                item["requires_confirmation"] = False
                item["updated_at"] = now.isoformat()
                changed = True
        if changed:
            self._write(items)
        return items

    def _write(self, items: list[dict[str, Any]]) -> None:
        text = "\n".join(json.dumps(_normalize_pending_item(item) or item, ensure_ascii=False) for item in items)
        self.path.write_text(f"{text}\n" if text else "", encoding="utf-8")


def _normalize_pending_item(item: dict[str, Any]) -> dict[str, Any] | None:
    normalized = normalize_mapping_values(item)
    memory_type = _canonical_memory_type(str(normalized.get("type") or ""))
    status = str(normalized.get("status") or "")
    if memory_type not in PENDING_TYPES or status not in PENDING_STATUSES:
        return None
    text = normalize_terminology(str(normalized.get("summary") or normalized.get("text") or "")).strip()
    if not text or _contains_sensitive_text(text):
        return None
    created_at = str(normalized.get("created_at") or datetime.now(timezone.utc).isoformat())
    source = _canonical_source(str(normalized.get("source") or "conversation"))
    from_voice = _coerce_bool(normalized.get("from_voice")) or source in {"voice_confirmed", "voice_direct"}
    privacy_level = str(normalized.get("privacy_level") or "normal")
    if privacy_level not in {"normal", "sensitive", "secret"}:
        privacy_level = "normal"
    requires_confirmation = _coerce_bool(normalized.get("requires_confirmation"))
    if normalized.get("requires_confirmation") is None:
        requires_confirmation = status == "pending"
    if status != "pending":
        requires_confirmation = False
    evidence = _safe_evidence(normalized.get("evidence") or {})
    evidence_summary = normalize_terminology(str(normalized.get("evidence_summary") or "")).strip()
    if not evidence_summary:
        evidence_summary = _default_evidence_summary(source=source, from_voice=from_voice)
    if _contains_sensitive_text(evidence_summary):
        evidence_summary = "安全摘要已隐藏"
    return {
        "id": str(normalized.get("id") or uuid.uuid4()),
        "type": memory_type,
        "summary": text,
        "text": text,
        "source": source,
        "source_event_id": str(normalized.get("source_event_id") or "") or None,
        "long_term_memory_id": str(normalized.get("long_term_memory_id") or "") or None,
        "confidence": float(normalized.get("confidence") or 0),
        "requires_confirmation": requires_confirmation,
        "status": status,
        "created_at": created_at,
        "expires_at": str(normalized.get("expires_at") or _default_expires_at(created_at)),
        "updated_at": str(normalized.get("updated_at") or datetime.now(timezone.utc).isoformat()),
        "guard_reason": _safe_guard_reason(
            str(normalized.get("guard_reason") or ("requires_confirmation" if status == "pending" else "ignore_no_memory_intent"))
        ),
        "privacy_level": privacy_level,
        "related_game": str(normalized.get("related_game") or "") or None,
        "related_entity": str(normalized.get("related_entity") or "") or None,
        "from_voice": from_voice,
        "from_proactive": _coerce_bool(normalized.get("from_proactive")),
        "from_assistant": _coerce_bool(normalized.get("from_assistant")),
        "confirmation_intent": _safe_confirmation_intent(str(normalized.get("confirmation_intent") or "")),
        "evidence_summary": evidence_summary,
        "evidence": evidence,
        "payload": _safe_payload(normalized.get("payload") or {}),
    }


def _canonical_memory_type(value: str) -> str:
    return LEGACY_MEMORY_TYPE_MAP.get(value, value)


def _canonical_source(value: str) -> str:
    return value if value in PENDING_SOURCES else "conversation"


def _safe_confirmation_intent(value: str) -> str:
    if value in {"explicit", "implicit", "voice_confirmed", "voice_direct", "none"}:
        return value
    return "implicit"


def _safe_guard_reason(value: str) -> str:
    return value if value in GUARD_REASONS else "requires_confirmation"


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _default_expires_at(created_at: str) -> str:
    created = _parse_timestamp(created_at) or datetime.now(timezone.utc)
    return (created + CANDIDATE_TTL).isoformat()


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return _ensure_aware(datetime.fromisoformat(value))
    except ValueError:
        return None


def _safe_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        return {}
    normalized = normalize_mapping_values(evidence)
    allowed_keys = (
        "input_summary",
        "source_channel",
        "game_state_summary",
        "semantic_reason",
        "guard_decision",
        "memory_check_source",
        "memory_check_reason",
        "memory_check_status",
    )
    safe: dict[str, Any] = {}
    for key in allowed_keys:
        value = normalized.get(key)
        if value is None:
            continue
        text = normalize_terminology(str(value)).strip()
        if not text or _contains_sensitive_text(text):
            continue
        safe[key] = text[:220]
    if "input_summary" not in safe and normalized.get("user_message"):
        safe["input_summary"] = "用户输入已转为安全摘要"
    return safe


def _safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    normalized = normalize_mapping_values(payload)
    safe: dict[str, Any] = {}
    for key, value in normalized.items():
        key_text = str(key)
        value_text = normalize_terminology(str(value)).strip()
        if _contains_sensitive_text(key_text) or _contains_sensitive_text(value_text):
            continue
        safe[key_text] = value
    return safe


def _default_evidence_summary(*, source: str, from_voice: bool) -> str:
    if source == "semantic_extraction":
        return "来自语义识别结果的安全摘要"
    if from_voice:
        return "来自语音输入的安全摘要"
    return "来自用户输入的安全摘要"


def _pending_candidate(
    *,
    summary: str,
    type: str,
    confidence: float,
    created_at: str,
    updated_at: str,
    expires_at: str,
    source: str,
    source_event_id: str | None,
    evidence: dict[str, Any],
    evidence_summary: str,
    payload: dict[str, Any],
    guard_reason: str,
    confirmation_intent: str,
    from_voice: bool,
    from_proactive: bool,
    from_assistant: bool,
    related_game: str | None = None,
    related_entity: str | None = None,
) -> PendingMemory:
    safe_summary = normalize_terminology(summary).strip()
    return PendingMemory(
        id=str(uuid.uuid4()),
        type=type,
        text=safe_summary,
        summary=safe_summary,
        source=source,
        source_event_id=source_event_id,
        confidence=confidence,
        requires_confirmation=True,
        status="pending",
        created_at=created_at,
        expires_at=expires_at,
        updated_at=updated_at,
        guard_reason=guard_reason,
        privacy_level="normal",
        evidence_summary=evidence_summary,
        related_game=related_game,
        related_entity=related_entity,
        from_voice=from_voice,
        from_proactive=from_proactive,
        from_assistant=from_assistant,
        confirmation_intent=confirmation_intent,
        evidence=evidence,
        payload=payload,
    )


def _rejected_candidate(
    *,
    created_at: str,
    source: str,
    source_event_id: str | None,
    summary: str,
    guard_reason: str,
    type: str = "unknown",
    privacy_level: str = "normal",
    from_voice: bool = False,
    from_assistant: bool = False,
    from_proactive: bool = False,
    confirmation_intent: str = "none",
) -> PendingMemory:
    return PendingMemory(
        id=str(uuid.uuid4()),
        type=type,
        text=summary,
        summary=summary,
        source=source,
        source_event_id=source_event_id,
        confidence=0.0,
        requires_confirmation=False,
        status="rejected_by_guard",
        created_at=created_at,
        expires_at=_default_expires_at(created_at),
        updated_at=created_at,
        guard_reason=guard_reason,
        privacy_level=privacy_level,
        evidence_summary="记忆 guard 已阻止保存",
        from_voice=from_voice,
        from_assistant=from_assistant,
        from_proactive=from_proactive,
        confirmation_intent=confirmation_intent,
        evidence=_safe_evidence({"source_channel": source, "guard_decision": "reject_candidate"}),
        payload={},
    )


def _candidate_input_source(input_source: str | None, semantic_extraction: dict[str, Any] | None) -> str:
    if input_source in {"text", "voice_confirmed", "voice_direct"}:
        return input_source
    if isinstance(semantic_extraction, dict):
        semantic_input_source = semantic_extraction.get("input_source")
        if semantic_input_source in {"text", "voice_confirmed", "voice_direct"}:
            return str(semantic_input_source)
        llm_guard = semantic_extraction.get("llm_guard")
        if isinstance(llm_guard, dict) and llm_guard.get("input_source") in {"text", "voice_confirmed", "voice_direct"}:
            return str(llm_guard["input_source"])
    return "text"


def _candidate_source(input_source: str, default: str) -> str:
    if input_source in {"voice_confirmed", "voice_direct"}:
        return input_source
    return default


def _confirmation_intent(input_source: str, *, explicit: bool = False) -> str:
    if input_source == "voice_direct":
        return "voice_direct"
    if input_source == "voice_confirmed":
        return "voice_confirmed"
    return "explicit" if explicit else "implicit"


def _contains_sensitive_text(text: str) -> bool:
    return bool(SENSITIVE_PATTERN.search(text))


SEMANTIC_MEMORY_TYPE_MAP = {
    "guide_preference": "interaction_preference",
    "playstyle_preference": "gameplay_preference",
    "game_preference": "gameplay_preference",
    "persona_preference": "interaction_preference",
    "personal_preference": "unknown",
    "accessibility_preference": "accessibility_preference",
}


def _semantic_memory_candidate(
    semantic_extraction: dict[str, Any] | None,
    created_at: str,
    evidence: dict[str, Any],
    *,
    input_source: str,
    source_event_id: str | None,
    from_voice: bool,
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
    text = normalize_terminology(str(candidate.get("safe_summary") or candidate.get("text") or "")).strip()
    if not pending_type or not text or _contains_sensitive_text(text):
        return None
    if _persona_drift_request(_normalize_text(text)):
        return None
    evidence_summary = "语义识别提出了待确认记忆候选"
    semantic_reason = normalize_terminology(str(candidate.get("reason") or "")).strip()
    semantic_evidence = _safe_evidence({**evidence, "semantic_reason": semantic_reason})
    return _pending_candidate(
        summary=text,
        type=pending_type,
        confidence=confidence,
        created_at=created_at,
        expires_at=_default_expires_at(created_at),
        updated_at=created_at,
        source="semantic_extraction",
        source_event_id=source_event_id,
        guard_reason="requires_confirmation",
        confirmation_intent=_confirmation_intent(input_source),
        evidence_summary=evidence_summary,
        evidence=semantic_evidence,
        from_voice=from_voice,
        from_proactive=False,
        from_assistant=False,
        payload=_semantic_payload(source_type, text),
    )


def _minimum_candidate_confidence(candidate: PendingMemory) -> float:
    if candidate.payload.get("memory_check_source"):
        return 0.72
    if candidate.source == "semantic_extraction" and candidate.payload.get("semantic_type") == "persona_preference":
        return 0.65
    return 0.85


def _candidate_from_memory_check(
    memory_check: MemoryCandidateCheck,
    *,
    created_at: str,
    updated_at: str,
    expires_at: str,
    source: str,
    source_event_id: str | None,
    evidence: dict[str, Any],
    input_source: str,
    from_voice: bool,
) -> PendingMemory:
    explicit = bool(memory_check.explicit_request)
    guard_reason = "explicit_user_memory_request" if explicit else "requires_confirmation"
    evidence_summary = (
        "显式记忆请求已通过 Memory Candidate Check"
        if explicit
        else "LLM-primary Memory Candidate Check 提出了待确认记忆候选"
    )
    return _pending_candidate(
        summary=memory_check.safe_summary,
        type=memory_check.memory_type,
        confidence=memory_check.confidence,
        created_at=created_at,
        updated_at=updated_at,
        expires_at=expires_at,
        source=source,
        source_event_id=source_event_id,
        evidence=evidence,
        evidence_summary=evidence_summary,
        payload=_memory_check_payload(memory_check),
        guard_reason=guard_reason,
        confirmation_intent=_confirmation_intent(input_source, explicit=explicit),
        from_voice=from_voice,
        from_proactive=False,
        from_assistant=False,
    )


def _memory_check_payload(memory_check: MemoryCandidateCheck) -> dict[str, Any]:
    text = memory_check.safe_summary.removeprefix("玩家").strip()
    payload: dict[str, Any] = {
        "memory_check_source": memory_check.source,
        "memory_check_reason": memory_check.reason,
        "memory_check_action": memory_check.suggested_action,
    }
    if memory_check.memory_type == "gameplay_preference":
        payload["playstyle"] = text
    elif memory_check.memory_type == "interaction_preference":
        payload["preference"] = text
    elif memory_check.memory_type == "accessibility_preference":
        payload["preference"] = text
    elif memory_check.memory_type == "emotional_pattern":
        payload["emotional_state"] = text
    else:
        payload["preference"] = text
    return payload


def _memory_check_reject_reason(memory_check: MemoryCandidateCheck) -> str:
    if memory_check.reason in {"sensitive_secret_blocked", "persona_drift_blocked", "do_not_remember"}:
        return memory_check.reason
    return "reject_candidate"


def _should_auto_save(item: dict[str, Any]) -> bool:
    if item.get("status") != "pending":
        return False
    if item.get("guard_reason") != "explicit_user_memory_request":
        return False
    if item.get("type") == "do_not_remember":
        return False
    if item.get("from_assistant") or item.get("from_proactive"):
        return False
    if item.get("privacy_level") == "secret":
        return False
    return item.get("confirmation_intent") in {"explicit", "voice_confirmed", "voice_direct"}


def _memory_update_result(
    *,
    status: str,
    item: dict[str, Any] | None = None,
    pending_count: int = 0,
) -> dict[str, Any]:
    return {
        "status": status,
        "summary": (item or {}).get("summary") or None,
        "pending_memory_id": (item or {}).get("id") or None,
        "long_term_memory_id": (item or {}).get("long_term_memory_id") or None,
        "pending_count": pending_count,
        "undo_available": status == "auto_saved" and bool((item or {}).get("long_term_memory_id")),
    }


def _semantic_payload(source_type: str, text: str) -> dict[str, Any]:
    base = {"semantic_type": source_type}
    if source_type == "playstyle_preference":
        return {**base, "playstyle": text.removeprefix("玩家")}
    if source_type == "persona_preference":
        return {**base, "preferred_tone": text.removeprefix("玩家")}
    if source_type in {"guide_preference", "personal_preference"}:
        return {**base, "preference": text.removeprefix("玩家")}
    if source_type in {"game_preference", "accessibility_preference"}:
        return {**base, "preference": text.removeprefix("玩家")}
    return base


def _mentions_short_guide_preference(message: str) -> bool:
    compact = _normalize_text(message)
    return bool(re.search(r"(?:喜欢|喜歡|希望|想要|尽量|盡量).{0,8}(?:简短|短一点|短點|一句|少一点|少點).{0,8}(?:攻略|提醒|回答)", compact))


def _mentions_short_reply_preference(message: str) -> bool:
    compact = _normalize_text(message)
    patterns = (
        r"(?:以后|之後|之后|后面|後面)?.{0,4}(?:回答|回复|回覆|说话|說話).{0,8}(?:短一点|短點|简短|簡短|少一点|少點)",
        r"(?:以后|之後|之后|后面|後面).{0,8}(?:短一点|短點|简短|簡短|少一点|少點).{0,6}(?:回答|回复|回覆|说话|說話)",
    )
    return any(re.search(pattern, compact) for pattern in patterns)


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


def _spoiler_preference(message: str) -> str | None:
    compact = _normalize_text(message)
    if any(marker in compact for marker in ("别剧透", "別劇透", "不要剧透", "不要劇透", "不想被剧透", "不想被劇透")):
        return "玩家偏好避免剧透，除非主动询问"
    if "剧透" in compact and any(marker in compact for marker in ("除非我问", "除非我問", "我主动问", "我主動問")):
        return "玩家偏好避免剧透，除非主动询问"
    return None


def _accessibility_preference(message: str) -> str | None:
    compact = _normalize_text(message)
    if any(marker in compact for marker in ("语音短一点", "語音短一點", "播报短一点", "播報短一點", "朗读短一点", "朗讀短一點")):
        return "玩家偏好语音播报更短"
    if any(marker in compact for marker in ("读慢一点", "讀慢一點", "说慢一点", "說慢一點")):
        return "玩家偏好语音输出更慢"
    return None


def _persona_drift_request(compact: str) -> bool:
    persona_drift_markers = (
        "撒娇",
        "撒嬌",
        "每句话都夸",
        "每句話都誇",
        "每句话夸",
        "每句話誇",
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
    if any(marker in compact for marker in persona_drift_markers):
        return True
    return bool(re.search(r"(?:以后|之後|之后).{0,8}(?:都|每句|每句话|每句話).{0,8}(?:夸|誇|哄|撒娇|撒嬌)", compact))


def _explicit_personal_preference(message: str) -> str | None:
    compact = _normalize_text(message)
    if _negative_memory_request(compact):
        return None
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


def _explicit_boss_exploration_preference(message: str) -> str | None:
    compact = _normalize_text(message)
    if _negative_memory_request(compact):
        return None
    if not re.search(r"(?:记住|記住|记得|記得|帮我记|幫我記)", compact):
        return None
    has_boss_context = "boss" in compact or "打boss" in compact
    has_exploration = any(marker in compact for marker in ("先探索", "探索地图", "探索地圖", "先跑图", "先跑圖"))
    has_hard_push_dislike = any(marker in compact for marker in ("不喜欢直接硬打", "不喜歡直接硬打", "不想直接硬打", "不要直接硬打"))
    if not has_boss_context or not (has_exploration or has_hard_push_dislike):
        return None
    return "打 Boss 前喜欢先探索地图，不喜欢直接硬打"


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
