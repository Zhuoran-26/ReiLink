from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.config import settings

KnowledgeSource = str


def build_local_data_status() -> dict[str, object]:
    data_dir = settings.data_dir
    memory_dir = settings.memory_dir
    session_dir = settings.session_dir
    settings_dir = _settings_dir()
    logs_dir = data_dir / "logs"
    knowledge_dir = settings.knowledge_games_dir
    knowledge_source = _knowledge_source(knowledge_dir)

    return {
        "data_dir": str(data_dir),
        "memory_dir": str(memory_dir),
        "session_dir": str(session_dir),
        "settings_dir": str(settings_dir),
        "logs_dir": str(logs_dir),
        "knowledge_dir": str(knowledge_dir) if knowledge_dir else None,
        "knowledge_source": knowledge_source,
        "data_dir_exists": data_dir.is_dir(),
        "memory_files_count": _safe_file_count(memory_dir),
        "session_files_count": _safe_file_count(session_dir),
        "pending_memory_count": _safe_pending_memory_count(settings.pending_memories_path),
        "using_bundled_knowledge": knowledge_source == "bundled",
        "writable": _is_writable(data_dir),
    }


def _settings_dir() -> Path:
    configured = getattr(settings, "settings_dir", None)
    if isinstance(configured, Path):
        return configured
    if settings.settings_path.parent != settings.data_dir:
        return settings.settings_path.parent
    return settings.data_dir / "settings"


def _safe_file_count(directory: Path) -> int:
    try:
        if not directory.is_dir():
            return 0
        return sum(1 for item in directory.rglob("*") if item.is_file())
    except OSError:
        return 0


def _safe_pending_memory_count(path: Path) -> int:
    try:
        if not path.is_file():
            return 0
        count = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("status") == "pending":
                count += 1
        return count
    except OSError:
        return 0


def _knowledge_source(knowledge_dir: Path) -> KnowledgeSource:
    try:
        catalog_exists = (knowledge_dir / "catalog.json").is_file()
    except OSError:
        catalog_exists = False
    if not catalog_exists:
        return "missing"

    repo_knowledge_dir = settings.repo_root / "data" / "knowledge" / "games"
    if _same_path(knowledge_dir, repo_knowledge_dir):
        return "repo"
    if os.getenv("REILINK_KNOWLEDGE_DIR") or not _is_relative_to(knowledge_dir, settings.data_dir):
        return "bundled"
    return "repo"


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def _is_writable(path: Path) -> bool:
    try:
        if path.exists():
            return path.is_dir() and os.access(path, os.W_OK)
        parent = _nearest_existing_parent(path)
        return parent.is_dir() and os.access(parent, os.W_OK)
    except OSError:
        return False


def _nearest_existing_parent(path: Path) -> Path:
    current = path
    while not current.exists():
        parent = current.parent
        if parent == current:
            return current
        current = parent
    return current
