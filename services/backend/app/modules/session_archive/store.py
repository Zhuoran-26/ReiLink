from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.core.config import settings

ArchiveCreateStatus = Literal["created", "existing", "skipped"]

MAX_ARCHIVES = 20
MAX_EVENTS_PER_ARCHIVE = 80
MAX_EVENT_SUMMARY_CHARS = 180
MAX_ARCHIVE_SUMMARY_CHARS = 240

SAFE_EVENT_TYPES = {
    "game_selected",
    "boss_detected",
    "death_count_changed",
    "frustration_changed",
    "boss_cleared",
    "knowledge_used",
    "proactive_shown",
    "memory_accepted",
    "memory_ignored",
    "memory_undone",
    "voice_mode_used",
    "session_note",
}
SAFE_EVENT_SOURCES = {
    "renderer",
    "session_timeline",
    "game_context",
    "game_session",
    "knowledge",
    "proactive",
    "memory",
    "voice",
    "manual",
}
SAFE_INPUT_SOURCES = {"text", "voice_confirmed", "voice_direct"}
FORBIDDEN_ARCHIVE_TERMS = (
    ".env",
    "api_key",
    "api key",
    "authorization",
    "bearer",
    "raw prompt",
    "raw json",
    "raw model response",
    "raw chat transcript",
    "full voice transcript",
    "full transcript",
    "stdout",
    "stderr",
    "secret",
)
PHRASE_REPLACEMENTS = (
    (re.compile(r"\.env", re.IGNORECASE), "本地配置"),
    (re.compile(r"\bapi[_ -]?key\b", re.IGNORECASE), "敏感凭据"),
    (re.compile(r"\bauthorization\b", re.IGNORECASE), "敏感凭据"),
    (re.compile(r"\bbearer\b", re.IGNORECASE), "敏感凭据"),
    (re.compile(r"\bsecret\b", re.IGNORECASE), "敏感内容"),
    (re.compile(r"\braw\s+prompt\b", re.IGNORECASE), "内部提示"),
    (re.compile(r"\braw\s+json\b", re.IGNORECASE), "内部数据"),
    (re.compile(r"\braw\s+model\s+response\b", re.IGNORECASE), "模型输出"),
    (re.compile(r"\braw\s+chat\s+transcript\b", re.IGNORECASE), "聊天全文"),
    (re.compile(r"\bfull\s+voice\s+transcript\b", re.IGNORECASE), "语音全文"),
    (re.compile(r"\bfull\s+transcript\b", re.IGNORECASE), "转写全文"),
    (re.compile(r"\bstdout\b", re.IGNORECASE), "诊断输出"),
    (re.compile(r"\bstderr\b", re.IGNORECASE), "诊断输出"),
)
SECRET_VALUE_RE = re.compile(
    r"(?i)\b(?:sk-[a-z0-9_-]{12,}|[a-z0-9_-]{16,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}|"
    r"(?:api[_ -]?key|authorization|bearer|token|secret)\s*[:=]\s*[^\s，。；;,]+)"
)
LOCAL_PATH_RE = re.compile(r"(?:/Users|/private|/var|/tmp|[A-Za-z]:\\)[^\s，。；;,]+")
WHITESPACE_RE = re.compile(r"\s+")


class SessionArchiveStore:
    def __init__(self, path: Path | None = None, retention_limit: int = MAX_ARCHIVES) -> None:
        self.path = path or settings.session_archives_path
        self.retention_limit = retention_limit

    def list_archives(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        entries = [self._normalize_entry(item) for item in self._read()]
        if not include_deleted:
            entries = [item for item in entries if not item["is_deleted"]]
        return sorted(entries, key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)

    def get_archive(self, archive_id: str) -> dict[str, Any]:
        for item in self._read():
            entry = self._normalize_entry(item)
            if entry["id"] == archive_id and not entry["is_deleted"]:
                return entry
        raise KeyError(archive_id)

    def archive_current(
        self,
        *,
        session_id: str = "default",
        events: list[dict[str, Any]] | None = None,
        started_at: str | None = None,
        ended_at: str | None = None,
        game: str | None = None,
        area: str | None = None,
        boss: str | None = None,
        source: str = "manual",
    ) -> dict[str, Any]:
        safe_session_id = _safe_session_id(session_id)
        raw_events = events or []
        safe_events = [
            event
            for event in (
                self._sanitize_event(raw_event, session_id=safe_session_id)
                for raw_event in raw_events[:MAX_EVENTS_PER_ARCHIVE]
            )
            if event is not None
        ]
        if not safe_events:
            message = "本局还没有可归档的关键变化。" if not raw_events else "没有可安全归档的事件。"
            return {"status": "skipped", "archive": None, "message": message}

        now = _utc_now()
        normalized_game = sanitize_archive_text(game, max_chars=64)
        normalized_area = sanitize_archive_text(area, max_chars=64)
        normalized_boss = sanitize_archive_text(boss, max_chars=64)
        inferred_game = normalized_game or _first_text(safe_events, "related_game") or _infer_from_summary(safe_events, "游戏")
        inferred_boss = normalized_boss or _first_text(safe_events, "related_entity") or _infer_from_summary(safe_events, "Boss")
        safe_started_at = _safe_timestamp(started_at) or safe_events[0]["timestamp"]
        safe_ended_at = _safe_timestamp(ended_at) or safe_events[-1]["timestamp"]
        safe_source = _safe_source(source)
        safe_event_summaries = [event["safe_summary"] for event in safe_events]
        accepted_memory_count = sum(1 for event in safe_events if event["event_type"] == "memory_accepted")
        content_hash = _content_hash(
            {
                "session_id": safe_session_id,
                "game": inferred_game,
                "area": normalized_area,
                "boss": inferred_boss,
                "events": [
                    {
                        "event_type": event["event_type"],
                        "timestamp": event["timestamp"],
                        "safe_summary": event["safe_summary"],
                    }
                    for event in safe_events
                ],
            }
        )

        entries = [self._normalize_entry(item) for item in self._read()]
        for existing in entries:
            if not existing["is_deleted"] and existing.get("content_hash") == content_hash:
                return {"status": "existing", "archive": existing, "message": "这段会话已经归档。"}

        archive_id = f"archive-{uuid.uuid4().hex[:16]}"
        title = _archive_title(inferred_game, inferred_boss)
        archive = {
            "id": archive_id,
            "session_id": safe_session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "started_at": safe_started_at,
            "ended_at": safe_ended_at,
            "source": safe_source,
            "game": inferred_game,
            "area": normalized_area or None,
            "boss": inferred_boss,
            "summary": _archive_summary(safe_events, inferred_game, inferred_boss),
            "event_count": len(safe_events),
            "safe_event_summaries": safe_event_summaries,
            "events": [{**event, "session_id": safe_session_id} for event in safe_events],
            "memory_candidate_count": 0,
            "accepted_memory_count": accepted_memory_count,
            "privacy_level": _archive_privacy_level(safe_events),
            "retention_policy": f"manual_latest_{self.retention_limit}",
            "is_deleted": False,
            "deletion_status": "active",
            "content_hash": content_hash,
        }
        active_entries = [archive, *entries]
        self._write(self._apply_retention(active_entries))
        return {"status": "created", "archive": archive, "message": "会话已归档。"}

    def delete_archive(self, archive_id: str) -> dict[str, Any]:
        now = _utc_now()
        entries = [self._normalize_entry(item) for item in self._read()]
        updated: list[dict[str, Any]] = []
        deleted: dict[str, Any] | None = None
        for item in entries:
            if item["id"] == archive_id and not item["is_deleted"]:
                item = {
                    **item,
                    "updated_at": now,
                    "is_deleted": True,
                    "deletion_status": "deleted",
                }
                deleted = item
            updated.append(item)
        if deleted is None:
            raise KeyError(archive_id)
        self._write(updated)
        return deleted

    def clear_archives(self) -> int:
        now = _utc_now()
        entries = [self._normalize_entry(item) for item in self._read()]
        count = sum(1 for item in entries if not item["is_deleted"])
        self._write(
            [
                {
                    **item,
                    "updated_at": now if not item["is_deleted"] else item["updated_at"],
                    "is_deleted": True,
                    "deletion_status": "deleted",
                }
                for item in entries
            ]
        )
        return count

    def _sanitize_event(self, raw_event: dict[str, Any], *, session_id: str) -> dict[str, Any] | None:
        if not isinstance(raw_event, dict):
            return None
        raw_summary = raw_event.get("safe_summary") or raw_event.get("summary") or ""
        safe_summary = sanitize_archive_text(raw_summary, max_chars=MAX_EVENT_SUMMARY_CHARS)
        if not safe_summary:
            return None

        event_type = _safe_event_type(raw_event.get("event_type") or raw_event.get("type"))
        source = _safe_source(raw_event.get("source"))
        related_game = sanitize_archive_text(raw_event.get("related_game"), max_chars=64)
        related_entity = sanitize_archive_text(raw_event.get("related_entity"), max_chars=64)
        input_source = str(raw_event.get("input_source") or "").strip()
        risk_flags: list[str] = []
        if _contains_sensitive_text(str(raw_summary)):
            risk_flags.append("content_removed")
        if LOCAL_PATH_RE.search(str(raw_summary)):
            risk_flags.append("path_removed")
        if input_source not in SAFE_INPUT_SOURCES:
            input_source = ""

        event_id = str(raw_event.get("id") or "").strip()
        if not _safe_identifier(event_id):
            event_id = f"event-{uuid.uuid4().hex[:16]}"

        privacy_level = str(raw_event.get("privacy_level") or "normal").strip().lower()
        if privacy_level not in {"normal", "sensitive"}:
            privacy_level = "sensitive"
        if risk_flags:
            privacy_level = "sensitive"

        return {
            "id": event_id,
            "session_id": _safe_session_id(session_id),
            "timestamp": _safe_timestamp(raw_event.get("timestamp")) or _utc_now(),
            "event_type": event_type,
            "safe_summary": safe_summary,
            "source": source,
            "input_source": input_source or None,
            "related_game": related_game or None,
            "related_entity": related_entity or None,
            "risk_flags": risk_flags,
            "privacy_level": privacy_level,
            "can_generate_memory_candidate": False,
        }

    def _read(self) -> list[dict[str, Any]]:
        try:
            if not self.path.is_file():
                return []
            data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        except (OSError, json.JSONDecodeError):
            return []
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        archives = data.get("archives") if isinstance(data, dict) else None
        if not isinstance(archives, list):
            return []
        return [item for item in archives if isinstance(item, dict)]

    def _write(self, entries: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"archives": entries}
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.path)

    def _apply_retention(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        active = [item for item in entries if not item["is_deleted"]]
        deleted = [item for item in entries if item["is_deleted"]]
        active = sorted(active, key=lambda item: item.get("created_at") or "", reverse=True)
        kept_active = active[: self.retention_limit]
        expired_active = [
            {
                **item,
                "updated_at": _utc_now(),
                "is_deleted": True,
                "deletion_status": "retention_expired",
            }
            for item in active[self.retention_limit :]
        ]
        return [*kept_active, *expired_active, *deleted]

    def _normalize_entry(self, item: dict[str, Any]) -> dict[str, Any]:
        now = _utc_now()
        events = [
            event
            for event in (
                self._sanitize_event(raw_event, session_id=_safe_session_id(item.get("session_id")))
                for raw_event in item.get("events", [])
                if isinstance(raw_event, dict)
            )
            if event is not None
        ]
        safe_summaries = [event["safe_summary"] for event in events]
        if not safe_summaries:
            safe_summaries = [
                summary
                for summary in (
                    sanitize_archive_text(text, max_chars=MAX_EVENT_SUMMARY_CHARS)
                    for text in item.get("safe_event_summaries", [])
                )
                if summary
            ]
        return {
            "id": str(item.get("id") or f"archive-{uuid.uuid4().hex[:16]}"),
            "session_id": _safe_session_id(item.get("session_id")),
            "title": sanitize_archive_text(item.get("title"), max_chars=96) or "最近会话",
            "created_at": _safe_timestamp(item.get("created_at")) or now,
            "updated_at": _safe_timestamp(item.get("updated_at")) or _safe_timestamp(item.get("created_at")) or now,
            "started_at": _safe_timestamp(item.get("started_at")) or _safe_timestamp(item.get("created_at")) or now,
            "ended_at": _safe_timestamp(item.get("ended_at")) or _safe_timestamp(item.get("updated_at")) or now,
            "source": _safe_source(item.get("source")),
            "game": sanitize_archive_text(item.get("game"), max_chars=64) or None,
            "area": sanitize_archive_text(item.get("area"), max_chars=64) or None,
            "boss": sanitize_archive_text(item.get("boss"), max_chars=64) or None,
            "summary": sanitize_archive_text(item.get("summary"), max_chars=MAX_ARCHIVE_SUMMARY_CHARS)
            or "本局保存了安全摘要。",
            "event_count": int(item.get("event_count") or len(safe_summaries)),
            "safe_event_summaries": safe_summaries,
            "events": events,
            "memory_candidate_count": 0,
            "accepted_memory_count": int(item.get("accepted_memory_count") or 0),
            "privacy_level": str(item.get("privacy_level") or "normal")
            if str(item.get("privacy_level") or "normal") in {"normal", "sensitive"}
            else "sensitive",
            "retention_policy": str(item.get("retention_policy") or f"manual_latest_{self.retention_limit}"),
            "is_deleted": bool(item.get("is_deleted")),
            "deletion_status": str(item.get("deletion_status") or ("deleted" if item.get("is_deleted") else "active")),
            "content_hash": str(item.get("content_hash") or ""),
        }


def sanitize_archive_text(value: Any, *, max_chars: int = MAX_ARCHIVE_SUMMARY_CHARS) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = SECRET_VALUE_RE.sub("敏感内容已隐藏", text)
    text = LOCAL_PATH_RE.sub("本地路径已隐藏", text)
    for pattern, replacement in PHRASE_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    if not text:
        return ""
    for term in FORBIDDEN_ARCHIVE_TERMS:
        if term in text.lower():
            return ""
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"
    return text


def _archive_summary(events: list[dict[str, Any]], game: str | None, boss: str | None) -> str:
    deaths = _latest_summary(events, "death_count_changed")
    cleared = _latest_summary(events, "boss_cleared")
    knowledge_count = sum(1 for event in events if event["event_type"] == "knowledge_used")
    memory_count = sum(1 for event in events if event["event_type"] == "memory_accepted")
    parts: list[str] = []
    if game:
        parts.append(f"游戏：{game}")
    if boss:
        parts.append(f"Boss：{boss}")
    if cleared:
        parts.append(cleared)
    elif deaths:
        parts.append(deaths)
    if knowledge_count:
        parts.append(f"使用了 {knowledge_count} 条知识摘要")
    if memory_count:
        parts.append(f"确认了 {memory_count} 条记忆")
    if not parts:
        parts = [event["safe_summary"] for event in events[:2]]
    return sanitize_archive_text("；".join(parts), max_chars=MAX_ARCHIVE_SUMMARY_CHARS) or "本局保存了安全摘要。"


def _archive_title(game: str | None, boss: str | None) -> str:
    if game and boss:
        return sanitize_archive_text(f"{game} / {boss}", max_chars=96) or "最近会话"
    if game:
        return sanitize_archive_text(game, max_chars=96) or "最近会话"
    if boss:
        return sanitize_archive_text(boss, max_chars=96) or "最近会话"
    return "最近会话"


def _archive_privacy_level(events: list[dict[str, Any]]) -> str:
    return "sensitive" if any(event["privacy_level"] == "sensitive" for event in events) else "normal"


def _content_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _contains_sensitive_text(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in FORBIDDEN_ARCHIVE_TERMS) or bool(SECRET_VALUE_RE.search(text))


def _safe_event_type(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in SAFE_EVENT_TYPES:
        return raw
    if "voice" in raw:
        return "voice_mode_used"
    return "session_note"


def _safe_source(value: Any) -> str:
    raw = str(value or "manual").strip().lower()
    if raw in SAFE_EVENT_SOURCES:
        return raw
    if raw in {"voice_confirmed", "voice_direct", "local_asr", "web_speech"}:
        return "voice"
    if _contains_sensitive_text(raw):
        return "manual"
    return "renderer"


def _safe_identifier(value: str) -> bool:
    return bool(value) and bool(re.fullmatch(r"[A-Za-z0-9_.:-]{1,96}", value))


def _safe_session_id(value: Any) -> str:
    raw = str(value or "default").strip()
    if not raw or _contains_sensitive_text(raw):
        return "default"
    safe = re.sub(r"[^A-Za-z0-9_.:-]", "-", raw)[:80].strip(".:-")
    return safe or "default"


def _safe_timestamp(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    text = str(value or "").strip()
    if not text:
        return None
    try:
        normalized = text.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first_text(events: list[dict[str, Any]], key: str) -> str | None:
    for event in events:
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _infer_from_summary(events: list[dict[str, Any]], label: str) -> str | None:
    pattern = re.compile(rf"{re.escape(label)}[：:]\s*([^；,/]+)")
    for event in events:
        match = pattern.search(event["safe_summary"])
        if match:
            return sanitize_archive_text(match.group(1), max_chars=64) or None
    return None


def _latest_summary(events: list[dict[str, Any]], event_type: str) -> str:
    for event in reversed(events):
        if event["event_type"] == event_type:
            return event["safe_summary"]
    return ""
