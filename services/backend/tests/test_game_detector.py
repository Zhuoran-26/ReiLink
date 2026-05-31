import json
from datetime import datetime, timezone

from app.modules.game_detector.detector import (
    GameRegistry,
    LocalGameDetector,
    sync_game_session_from_detection,
)
from app.modules.game_session.state import GameSessionStore


def _registry(tmp_path, payload=None):
    path = tmp_path / "game_registry.json"
    path.write_text(
        json.dumps(
            payload
            or {
                "elden_ring": {
                    "display_name": "艾尔登法环",
                    "aliases": ["Elden Ring", "老头环", "艾尔登法环"],
                    "process_names": ["eldenring.exe", "Elden Ring"],
                    "steam_app_id": "1245620",
                    "knowledge_game_id": "elden_ring",
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return GameRegistry(path)


def test_running_when_process_exists(tmp_path):
    detection = LocalGameDetector(
        process_iter=[{"name": "eldenring.exe"}],
        system_name="Windows",
        registry=_registry(tmp_path),
    ).detect()

    assert detection.status == "running"
    assert detection.detected_game_id == "elden_ring"
    assert detection.display_name == "艾尔登法环"
    assert detection.process_name == "eldenring.exe"
    assert detection.match_source == "process"


def test_idle_when_process_missing(tmp_path):
    detection = LocalGameDetector(
        process_iter=[{"name": "steam.exe"}],
        system_name="Windows",
        registry=_registry(tmp_path),
    ).detect()

    assert detection.status == "idle"
    assert detection.detected_game_id is None


def test_unknown_process_does_not_match_elden_ring(tmp_path):
    detection = LocalGameDetector(
        process_iter=[{"name": "unknown-game.exe"}],
        system_name="Windows",
        registry=_registry(tmp_path),
    ).detect()

    assert detection.status in {"idle", "unknown"}
    assert detection.detected_game_id != "elden_ring"
    assert detection.knowledge_game_id is None


def test_detected_elden_ring_has_knowledge_game_id(tmp_path):
    detection = LocalGameDetector(
        process_iter=[{"name": "Elden Ring"}],
        system_name="Darwin",
        registry=_registry(tmp_path),
    ).detect()

    assert detection.status == "running"
    assert detection.detected_game_id == "elden_ring"
    assert detection.knowledge_game_id == "elden_ring"


def test_auto_detection_off_does_not_update_game_session(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    detection = LocalGameDetector(
        process_iter=[{"name": "eldenring.exe"}],
        system_name="Windows",
        registry=_registry(tmp_path),
    ).detect(now=datetime(2026, 1, 1, tzinfo=timezone.utc))

    changed = sync_game_session_from_detection(detection, auto_game_detection="off", game_session=store)

    assert changed is False
    assert store.load().current_game is None


def test_auto_detection_on_updates_game_session_without_boss(tmp_path):
    store = GameSessionStore(tmp_path / "game_session_state.json")
    detection = LocalGameDetector(
        process_iter=[{"name": "eldenring.exe"}],
        system_name="Windows",
        registry=_registry(tmp_path),
    ).detect(now=datetime(2026, 1, 1, tzinfo=timezone.utc))

    changed = sync_game_session_from_detection(detection, auto_game_detection="on", game_session=store)
    state = store.load()

    assert changed is True
    assert state.current_game == "艾尔登法环"
    assert state.current_boss is None


def test_detected_unsupported_game_can_be_represented(tmp_path):
    registry = _registry(
        tmp_path,
        {
            "stardew_valley": {
                "display_name": "星露谷物语",
                "aliases": ["Stardew Valley"],
                "process_names": ["Stardew Valley.exe"],
                "steam_app_id": "413150",
                "knowledge_game_id": None,
            }
        },
    )

    detection = LocalGameDetector(
        process_iter=[{"name": "Stardew Valley.exe"}],
        system_name="Windows",
        registry=registry,
    ).detect()

    assert detection.status == "running"
    assert detection.detected_game_id == "stardew_valley"
    assert detection.display_name == "星露谷物语"
    assert detection.knowledge_game_id is None
