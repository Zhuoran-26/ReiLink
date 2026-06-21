from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.modules.memory.pending import PendingMemoryQueue
from app.modules.session_archive.store import SessionArchiveStore, sanitize_archive_text

DEFAULT_RECENT_SCAN_LIMIT = 5
MAX_RECENT_SCAN_LIMIT = 20
ARCHIVE_CANDIDATE_TTL = timedelta(days=30)

_SECRET_REDACTION_TERMS = (
    "敏感内容已隐藏",
    "本地路径已隐藏",
    "内部提示",
    "内部数据",
    "聊天全文",
    "语音全文",
    "诊断输出",
)
_PERSONA_DRIFT_PATTERN = re.compile(r"(撒娇|甜一点|客服|每句都夸|像恋人|女朋友|治疗师|心理咨询|不要像\s*rei)", re.IGNORECASE)
_SESSION_EVENT_PATTERN = re.compile(r"(死亡|死了|寄了|阵亡|death|death_count|被.+打爆|掉血|击败|清掉|过了|通关)", re.IGNORECASE)
_EMOTIONAL_STATE_PATTERN = re.compile(r"(烦|烦躁|破防|生气|沮丧|崩溃|难受|frustrat|angry|upset)", re.IGNORECASE)
_EXPLICIT_PREFERENCE_PATTERN = re.compile(r"(偏好|喜欢|不喜欢|希望|以后|倾向|更想|更喜欢|记住|prefer|like|dislike|want)", re.IGNORECASE)
_GAMEPLAY_PREFERENCE_PATTERN = re.compile(
    r"(先探索|探索地图|先逛|打\s*boss\s*前|boss\s*前|不喜欢直接硬打|不想直接硬打|先看地图|先收集|before\s+boss|explor)",
    re.IGNORECASE,
)
_INTERACTION_PREFERENCE_PATTERN = re.compile(
    r"(短一点|简短|一句重点|别太长|不要太长|少一点|只给重点|少讲|brief|short repl|concise)",
    re.IGNORECASE,
)
_SPOILER_PREFERENCE_PATTERN = re.compile(r"(别剧透|不要剧透|不剧透|避免剧透|主动问攻略|除非.*攻略|spoiler)", re.IGNORECASE)


@dataclass(frozen=True)
class ArchiveEvidence:
    archive_id: str
    archive_title: str
    event_id: str | None
    safe_summary: str
    source: str
    event_type: str
    related_game: str | None
    related_entity: str | None
    privacy_level: str
    risk_flags: tuple[str, ...]


@dataclass(frozen=True)
class DetectedArchivePreference:
    key: str
    memory_type: str
    summary: str
    evidence: list[ArchiveEvidence]
    related_game: str | None
    related_entity: str | None
    confidence: float


class ArchiveMemoryCandidateBridge:
    def __init__(
        self,
        archive_store: SessionArchiveStore | None = None,
        pending_queue: PendingMemoryQueue | None = None,
    ) -> None:
        self.archive_store = archive_store or SessionArchiveStore()
        self.pending_queue = pending_queue or PendingMemoryQueue()

    def scan_archive(self, archive_id: str) -> dict[str, Any]:
        archive = self.archive_store.get_archive(archive_id)
        return self._scan_archives([archive], mode="single_archive")

    def scan_recent(
        self,
        *,
        limit: int = DEFAULT_RECENT_SCAN_LIMIT,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        safe_limit = max(1, min(int(limit or DEFAULT_RECENT_SCAN_LIMIT), MAX_RECENT_SCAN_LIMIT))
        start = _timestamp_value(date_from)
        end = _timestamp_value(date_to)
        archives = [
            archive
            for archive in self.archive_store.list_archives()
            if _archive_in_range(archive, start=start, end=end)
        ][:safe_limit]
        return self._scan_archives(archives, mode="recent_archives")

    def _scan_archives(self, archives: list[dict[str, Any]], *, mode: str) -> dict[str, Any]:
        evidence = _archive_evidence(archives)
        created_candidates: list[dict[str, Any]] = []
        skipped_candidates: list[dict[str, Any]] = []
        rejected_candidates: list[dict[str, Any]] = []
        usable_evidence: list[ArchiveEvidence] = []

        for item in evidence:
            rejection_reason = _rejection_reason(item)
            if rejection_reason:
                rejected_candidates.append(_scan_item_from_evidence(item, guard_reason=rejection_reason))
                continue
            usable_evidence.append(item)

        if not archives:
            skipped_candidates.append(
                _scan_item(
                    archive_id=None,
                    archive_event_ids=[],
                    guard_reason="no_recent_archives",
                    safe_summary="暂无可检查的会话归档。",
                )
            )

        if archives and not usable_evidence and not rejected_candidates:
            skipped_candidates.append(
                _scan_item(
                    archive_id=str(archives[0].get("id") or ""),
                    archive_event_ids=[],
                    guard_reason="no_safe_archive_events",
                    safe_summary="这条会话归档没有可用于候选记忆检查的安全事件。",
                )
            )

        detections = _detect_preferences(usable_evidence, mode=mode)
        detection_keys = {detection.key for detection in detections}
        for item in usable_evidence:
            if _event_is_single_session_state(item) and "single_session_event_only" not in detection_keys:
                skipped_candidates.append(_scan_item_from_evidence(item, guard_reason="single_session_event_only"))
            elif _event_is_single_emotional_state(item) and "single_emotional_state_only" not in detection_keys:
                skipped_candidates.append(_scan_item_from_evidence(item, guard_reason="single_emotional_state_only"))

        for detection in detections:
            candidate = _pending_candidate_from_detection(detection, mode=mode)
            created = self.pending_queue.enqueue([candidate])
            if created:
                created_candidates.extend(created)
            else:
                skipped_candidates.append(
                    _scan_item(
                        archive_id=detection.evidence[0].archive_id if detection.evidence else None,
                        archive_event_ids=[item.event_id for item in detection.evidence if item.event_id],
                        candidate_type=detection.memory_type,
                        guard_reason="duplicate_candidate",
                        safe_summary=detection.summary,
                        evidence_summary=_evidence_summary(detection.evidence),
                    )
                )

        if archives and not created_candidates and not skipped_candidates and not rejected_candidates:
            skipped_candidates.append(
                _scan_item(
                    archive_id=str(archives[0].get("id") or ""),
                    archive_event_ids=[],
                    guard_reason="no_candidate",
                    safe_summary="没有发现值得保存为长期记忆的稳定偏好。",
                )
            )

        return {
            "created_candidates": created_candidates,
            "skipped_candidates": _dedupe_scan_items(skipped_candidates),
            "rejected_candidates": _dedupe_scan_items(rejected_candidates),
            "scan_summary": {
                "mode": mode,
                "archives_scanned": len(archives),
                "events_scanned": len(evidence),
                "created_count": len(created_candidates),
                "skipped_count": len(_dedupe_scan_items(skipped_candidates)),
                "rejected_count": len(_dedupe_scan_items(rejected_candidates)),
            },
        }


def _archive_evidence(archives: list[dict[str, Any]]) -> list[ArchiveEvidence]:
    items: list[ArchiveEvidence] = []
    for archive in archives:
        archive_id = str(archive.get("id") or "")
        title = sanitize_archive_text(archive.get("title"), max_chars=96) or "最近会话"
        events = archive.get("events") or []
        if isinstance(events, list) and events:
            for raw_event in events:
                if not isinstance(raw_event, dict):
                    continue
                safe_summary = sanitize_archive_text(raw_event.get("safe_summary") or raw_event.get("summary"), max_chars=180)
                if not safe_summary:
                    continue
                items.append(
                    ArchiveEvidence(
                        archive_id=archive_id,
                        archive_title=title,
                        event_id=str(raw_event.get("id") or "") or None,
                        safe_summary=safe_summary,
                        source=str(raw_event.get("source") or "renderer"),
                        event_type=str(raw_event.get("event_type") or "session_note"),
                        related_game=sanitize_archive_text(raw_event.get("related_game") or archive.get("game"), max_chars=64)
                        or None,
                        related_entity=sanitize_archive_text(
                            raw_event.get("related_entity") or archive.get("boss") or archive.get("area"), max_chars=64
                        )
                        or None,
                        privacy_level=str(raw_event.get("privacy_level") or archive.get("privacy_level") or "normal"),
                        risk_flags=tuple(str(flag) for flag in raw_event.get("risk_flags") or []),
                    )
                )
            continue

        for index, summary in enumerate(archive.get("safe_event_summaries") or []):
            safe_summary = sanitize_archive_text(summary, max_chars=180)
            if not safe_summary:
                continue
            items.append(
                ArchiveEvidence(
                    archive_id=archive_id,
                    archive_title=title,
                    event_id=f"summary-{index}",
                    safe_summary=safe_summary,
                    source=str(archive.get("source") or "manual"),
                    event_type="session_note",
                    related_game=sanitize_archive_text(archive.get("game"), max_chars=64) or None,
                    related_entity=sanitize_archive_text(archive.get("boss") or archive.get("area"), max_chars=64) or None,
                    privacy_level=str(archive.get("privacy_level") or "normal"),
                    risk_flags=(),
                )
            )
    return items


def _rejection_reason(evidence: ArchiveEvidence) -> str | None:
    text = evidence.safe_summary
    source = evidence.source.lower()
    if source == "assistant":
        return "assistant_source_blocked"
    if source == "proactive":
        return "proactive_source_blocked"
    if evidence.privacy_level == "sensitive" or evidence.risk_flags or any(term in text for term in _SECRET_REDACTION_TERMS):
        return "sensitive_secret_blocked"
    if _PERSONA_DRIFT_PATTERN.search(text):
        return "persona_drift_blocked"
    return None


def _detect_preferences(evidence: list[ArchiveEvidence], *, mode: str) -> list[DetectedArchivePreference]:
    grouped: dict[str, list[ArchiveEvidence]] = {
        "gameplay_preference": [],
        "interaction_preference": [],
        "spoiler_preference": [],
    }
    for item in evidence:
        text = item.safe_summary
        if _GAMEPLAY_PREFERENCE_PATTERN.search(text):
            grouped["gameplay_preference"].append(item)
        if _INTERACTION_PREFERENCE_PATTERN.search(text):
            grouped["interaction_preference"].append(item)
        if _SPOILER_PREFERENCE_PATTERN.search(text):
            grouped["spoiler_preference"].append(item)

    detections: list[DetectedArchivePreference] = []
    for key, items in grouped.items():
        if not items:
            continue
        if mode == "single_archive" and not any(_EXPLICIT_PREFERENCE_PATTERN.search(item.safe_summary) for item in items):
            continue
        if mode == "recent_archives" and len({item.archive_id for item in items}) < 2 and not any(
            _EXPLICIT_PREFERENCE_PATTERN.search(item.safe_summary) for item in items
        ):
            continue
        selected = items[:4]
        related_game = next((item.related_game for item in selected if item.related_game), None)
        related_entity = next((item.related_entity for item in selected if item.related_entity), None)
        if key == "gameplay_preference":
            detections.append(
                DetectedArchivePreference(
                    key=key,
                    memory_type="gameplay_preference",
                    summary="用户打 Boss 前偏好先探索地图，不喜欢直接硬打。",
                    evidence=selected,
                    related_game=related_game,
                    related_entity=related_entity,
                    confidence=0.9 if len(selected) > 1 else 0.84,
                )
            )
        elif key == "interaction_preference":
            detections.append(
                DetectedArchivePreference(
                    key=key,
                    memory_type="interaction_preference",
                    summary="用户希望游戏中回复更短、更聚焦重点。",
                    evidence=selected,
                    related_game=related_game,
                    related_entity=related_entity,
                    confidence=0.88 if len(selected) > 1 else 0.82,
                )
            )
        elif key == "spoiler_preference":
            detections.append(
                DetectedArchivePreference(
                    key=key,
                    memory_type="interaction_preference",
                    summary="用户偏好避免剧透，除非主动询问攻略。",
                    evidence=selected,
                    related_game=related_game,
                    related_entity=related_entity,
                    confidence=0.89 if len(selected) > 1 else 0.83,
                )
            )
    return detections


def _pending_candidate_from_detection(detection: DetectedArchivePreference, *, mode: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    archive_event_ids = [item.event_id for item in detection.evidence if item.event_id]
    source_archive_id = detection.evidence[0].archive_id if detection.evidence else None
    return {
        "id": f"archive-mem-{uuid.uuid4().hex[:16]}",
        "type": detection.memory_type,
        "summary": detection.summary,
        "text": detection.summary,
        "source": "session_archive",
        "source_event_id": ":".join([source_archive_id or "archive", archive_event_ids[0] if archive_event_ids else "summary"]),
        "confidence": detection.confidence,
        "requires_confirmation": True,
        "status": "pending",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": (now + ARCHIVE_CANDIDATE_TTL).isoformat(),
        "guard_reason": "requires_confirmation",
        "privacy_level": "normal",
        "related_game": detection.related_game,
        "related_entity": detection.related_entity,
        "from_voice": any(item.source == "voice" for item in detection.evidence),
        "from_proactive": False,
        "from_assistant": False,
        "confirmation_intent": "implicit",
        "evidence_summary": _evidence_summary(detection.evidence),
        "evidence": {
            "source_channel": "session_archive",
            "input_summary": _evidence_summary(detection.evidence),
            "source_archive_id": source_archive_id or "",
            "source_archive_event_ids": ", ".join(archive_event_ids[:4]),
            "archive_evidence_count": str(len(detection.evidence)),
            "archive_scan_mode": mode,
        },
        "payload": {
            "source_archive_id": source_archive_id,
            "source_archive_event_ids": archive_event_ids,
            "archive_evidence_count": len(detection.evidence),
            "preference": detection.summary,
        },
    }


def _evidence_summary(evidence: list[ArchiveEvidence]) -> str:
    snippets = [item.safe_summary for item in evidence if item.safe_summary][:2]
    if not snippets:
        return "来自会话归档安全摘要。"
    return sanitize_archive_text(f"来自 {len(evidence)} 条会话归档安全摘要：{'；'.join(snippets)}", max_chars=220)


def _event_is_single_session_state(evidence: ArchiveEvidence) -> bool:
    if evidence.event_type in {"death_count_changed", "boss_cleared"}:
        return True
    return bool(_SESSION_EVENT_PATTERN.search(evidence.safe_summary)) and not _EXPLICIT_PREFERENCE_PATTERN.search(evidence.safe_summary)


def _event_is_single_emotional_state(evidence: ArchiveEvidence) -> bool:
    if evidence.event_type == "frustration_changed":
        return True
    return bool(_EMOTIONAL_STATE_PATTERN.search(evidence.safe_summary)) and not _EXPLICIT_PREFERENCE_PATTERN.search(evidence.safe_summary)


def _scan_item_from_evidence(evidence: ArchiveEvidence, *, guard_reason: str) -> dict[str, Any]:
    return _scan_item(
        archive_id=evidence.archive_id,
        archive_event_ids=[evidence.event_id] if evidence.event_id else [],
        guard_reason=guard_reason,
        safe_summary=evidence.safe_summary,
        evidence_summary=f"{evidence.archive_title} / {evidence.event_type}",
    )


def _scan_item(
    *,
    archive_id: str | None,
    archive_event_ids: list[str | None],
    guard_reason: str,
    safe_summary: str,
    candidate_id: str | None = None,
    candidate_type: str | None = None,
    evidence_summary: str | None = None,
) -> dict[str, Any]:
    return {
        "archive_id": archive_id,
        "archive_event_ids": [str(item) for item in archive_event_ids if item],
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "guard_reason": guard_reason,
        "safe_summary": sanitize_archive_text(safe_summary, max_chars=180) or "安全摘要不可用。",
        "evidence_summary": sanitize_archive_text(evidence_summary, max_chars=220) if evidence_summary else None,
    }


def _dedupe_scan_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str | None, tuple[str, ...], str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        key = (
            item.get("archive_id"),
            tuple(item.get("archive_event_ids") or []),
            str(item.get("guard_reason") or ""),
            str(item.get("safe_summary") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _timestamp_value(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _archive_in_range(archive: dict[str, Any], *, start: datetime | None, end: datetime | None) -> bool:
    if not start and not end:
        return True
    timestamp = _timestamp_value(str(archive.get("started_at") or archive.get("created_at") or ""))
    if timestamp is None:
        return True
    if start and timestamp < start:
        return False
    if end and timestamp > end:
        return False
    return True
