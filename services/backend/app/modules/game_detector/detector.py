from __future__ import annotations

import json
import platform
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

from app.core.config import settings
from app.modules.game_session.state import GameSessionStore
from app.schemas.api import GameDetectionResponse, GameStatus


@dataclass(frozen=True)
class GameRegistryEntry:
    game_id: str
    display_name: str
    aliases: list[str] = field(default_factory=list)
    process_names: list[str] = field(default_factory=list)
    steam_app_id: str | None = None
    knowledge_game_id: str | None = None


class GameRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings.game_registry_path
        self._entries_cache: list[GameRegistryEntry] | None = None

    def entries(self) -> list[GameRegistryEntry]:
        if self._entries_cache is not None:
            return self._entries_cache
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._entries_cache = []
            return []
        if not isinstance(raw, dict):
            self._entries_cache = []
            return []
        entries: list[GameRegistryEntry] = []
        for game_id, item in raw.items():
            if not isinstance(item, dict):
                continue
            display_name = str(item.get("display_name") or "").strip()
            if not game_id or not display_name:
                continue
            entries.append(
                GameRegistryEntry(
                    game_id=str(game_id),
                    display_name=display_name,
                    aliases=[str(value).strip() for value in item.get("aliases") or [] if str(value).strip()],
                    process_names=[
                        str(value).strip() for value in item.get("process_names") or [] if str(value).strip()
                    ],
                    steam_app_id=str(item.get("steam_app_id")) if item.get("steam_app_id") else None,
                    knowledge_game_id=str(item.get("knowledge_game_id")) if item.get("knowledge_game_id") else None,
                )
            )
        self._entries_cache = entries
        return entries

    def match_process(self, process_name: str | None) -> GameRegistryEntry | None:
        normalized_process = _normalize_process_name(process_name)
        if not normalized_process:
            return None
        for entry in self.entries():
            if any(normalized_process == _normalize_process_name(name) for name in entry.process_names):
                return entry
        return None


class LocalGameDetector:
    def __init__(
        self,
        process_iter: Iterable[Any] | None = None,
        system_name: str | None = None,
        registry: GameRegistry | None = None,
    ) -> None:
        self.process_iter = process_iter
        self.system_name = system_name or platform.system()
        self.registry = registry or GameRegistry()

    def detect(self, now: datetime | None = None) -> GameDetectionResponse:
        detected_at = now or datetime.now(timezone.utc)
        try:
            for proc in self._processes():
                process_name = self._process_name(proc)
                match = self.registry.match_process(process_name)
                if match:
                    return GameDetectionResponse(
                        status="running",
                        detected_game_id=match.game_id,
                        display_name=match.display_name,
                        process_name=process_name,
                        match_confidence=1.0,
                        match_source="process",
                        knowledge_game_id=match.knowledge_game_id,
                        detected_at=detected_at,
                    )
        except (psutil.Error, OSError):
            return _empty_detection("unknown", detected_at)
        return _empty_detection("idle", detected_at)

    def get_status(self) -> GameStatus:
        return detection_to_game_status(self.detect())

    def _processes(self) -> Iterable[Any]:
        if self.process_iter is not None:
            return self.process_iter
        if self.system_name not in {"Windows", "Darwin", "Linux"}:
            return []
        return psutil.process_iter(["name", "exe"])

    @staticmethod
    def _process_name(proc: Any) -> str | None:
        if isinstance(proc, dict):
            return str(proc.get("name") or proc.get("process_name") or proc.get("exe") or "").strip() or None
        info = getattr(proc, "info", None)
        if isinstance(info, dict):
            return str(info.get("name") or info.get("exe") or "").strip() or None
        name = getattr(proc, "name", None)
        value = name() if callable(name) else name
        return str(value).strip() if value else None


class EldenRingDetector(LocalGameDetector):
    """Compatibility wrapper for older callers and tests."""


def detection_to_game_status(detection: GameDetectionResponse) -> GameStatus:
    return GameStatus(
        game_id=detection.detected_game_id,
        game_name=detection.display_name,
        process_name=detection.process_name,
        status=detection.status,
        confidence=detection.match_confidence,
        tags=[],
        detected_game_id=detection.detected_game_id,
        display_name=detection.display_name,
        match_confidence=detection.match_confidence,
        match_source=detection.match_source,
        knowledge_game_id=detection.knowledge_game_id,
        detected_at=detection.detected_at,
    )


def idle_game_status(now: datetime | None = None) -> GameStatus:
    return detection_to_game_status(_empty_detection("idle", now or datetime.now(timezone.utc)))


def sync_game_session_from_detection(
    detection: GameDetectionResponse,
    *,
    auto_game_detection: str,
    game_session: GameSessionStore | None = None,
) -> bool:
    if auto_game_detection != "on":
        return False
    if detection.status != "running" or not detection.knowledge_game_id or not detection.display_name:
        return False
    store = game_session or GameSessionStore()
    state = store.load()
    state.current_game = detection.display_name
    state.last_updated_at = detection.detected_at.isoformat()
    store.save(state)
    return True


def _empty_detection(status: str, detected_at: datetime) -> GameDetectionResponse:
    return GameDetectionResponse(
        status=status,
        detected_game_id=None,
        display_name=None,
        process_name=None,
        match_confidence=0.0,
        match_source="none",
        knowledge_game_id=None,
        detected_at=detected_at,
    )


def _normalize_process_name(value: str | None) -> str:
    return (value or "").strip().lower()
