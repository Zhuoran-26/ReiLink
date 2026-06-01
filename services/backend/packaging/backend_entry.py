from __future__ import annotations

import os
import sys

import uvicorn

from app.core.config import settings


def _validate_runtime_paths() -> None:
    missing: list[str] = []
    for writable_dir in (
        settings.data_dir,
        settings.memory_dir,
        settings.session_dir,
        settings.conversations_dir,
        settings.data_dir / "settings",
        settings.data_dir / "logs",
    ):
        writable_dir.mkdir(parents=True, exist_ok=True)
    if not (settings.knowledge_games_dir / "catalog.json").is_file():
        missing.append(f"knowledge catalog: {settings.knowledge_games_dir / 'catalog.json'}")
    if missing:
        print(
            "ReiLink backend runtime error: required local data paths were not found.\n"
            + "\n".join(f"- {item}" for item in missing)
            + "\nSet REILINK_PROJECT_ROOT, REILINK_DATA_DIR, or REILINK_KNOWLEDGE_DIR, then start the backend again.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def main() -> None:
    _validate_runtime_paths()
    host = os.getenv("REILINK_BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("REILINK_BACKEND_PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
