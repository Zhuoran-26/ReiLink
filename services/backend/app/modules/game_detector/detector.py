import platform
from collections.abc import Iterable
from typing import Any

import psutil

from app.schemas.api import GameStatus

ELDEN_RING_PROCESS = "eldenring.exe"


class EldenRingDetector:
    def __init__(self, process_iter: Iterable[Any] | None = None, system_name: str | None = None) -> None:
        self.process_iter = process_iter
        self.system_name = system_name or platform.system()

    def get_status(self) -> GameStatus:
        if self._is_running():
            return GameStatus(
                game_id="elden_ring",
                game_name="Elden Ring",
                process_name=ELDEN_RING_PROCESS,
                status="running",
                confidence=1.0,
                tags=["soulslike", "dark_fantasy", "high_difficulty"],
            )
        return GameStatus(game_id=None, game_name=None, process_name=None, status="idle", confidence=0.0, tags=[])

    def _is_running(self) -> bool:
        if self.system_name != "Windows":
            return False
        try:
            iterator = self.process_iter if self.process_iter is not None else psutil.process_iter(["name"])
            for proc in iterator:
                name = self._process_name(proc)
                if name and name.lower() == ELDEN_RING_PROCESS:
                    return True
        except (psutil.Error, OSError):
            return False
        return False

    @staticmethod
    def _process_name(proc: Any) -> str | None:
        if isinstance(proc, dict):
            return proc.get("name")
        info = getattr(proc, "info", None)
        if isinstance(info, dict):
            return info.get("name")
        name = getattr(proc, "name", None)
        return name() if callable(name) else name

