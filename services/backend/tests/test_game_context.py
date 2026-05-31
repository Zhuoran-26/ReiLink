import json
from datetime import datetime, timezone

import pytest

from app.modules.game_context.context import GameContextResolver, GameContextStore, UnknownGameOverrideError
from app.modules.game_detector.detector import GameRegistry, LocalGameDetector
from app.modules.game_session.state import CurrentBoss, GameSessionStore
from app.modules.memory.pending import PendingMemoryQueue


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


def _resolver(tmp_path, process_names=None, registry_payload=None):
    return GameContextResolver(
        detector=LocalGameDetector(
            process_iter=[{"name": name} for name in (process_names or [])],
            system_name="Windows",
            registry=_registry(tmp_path, registry_payload),
        ),
        store=GameContextStore(tmp_path / "game_context_state.json"),
        game_session=GameSessionStore(tmp_path / "game_session_state.json"),
    )


def test_manual_override_selects_elden_ring(tmp_path):
    resolver = _resolver(tmp_path, process_names=[])

    resolver.set_manual_override("elden_ring", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    context = resolver.resolve()

    assert context.active_game_id == "elden_ring"
    assert context.active_game_display_name == "艾尔登法环"
    assert context.active_source == "manual"
    assert context.manual_override.enabled is True
    assert context.knowledge_available is True


def test_manual_override_takes_priority_over_detected_game(tmp_path):
    resolver = _resolver(
        tmp_path,
        process_names=["Stardew Valley.exe"],
        registry_payload={
            "stardew_valley": {
                "display_name": "星露谷物语",
                "aliases": ["Stardew Valley"],
                "process_names": ["Stardew Valley.exe"],
                "steam_app_id": "413150",
                "knowledge_game_id": None,
            }
        },
    )

    resolver.set_manual_override("elden_ring", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    context = resolver.resolve()

    assert context.active_game_id == "elden_ring"
    assert context.active_source == "manual"
    assert context.detected_game.detected_game_id == "stardew_valley"
    assert context.detected_game.display_name == "星露谷物语"


def test_clearing_manual_override_returns_to_detected_game(tmp_path):
    resolver = _resolver(tmp_path, process_names=["eldenring.exe"])

    resolver.set_manual_override("elden_ring", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    resolver.set_manual_override(None)
    context = resolver.resolve(sync_session=True)

    assert context.manual_override.enabled is False
    assert context.active_game_id == "elden_ring"
    assert context.active_source == "detector"
    assert resolver.game_session.load().current_game == "艾尔登法环"


def test_manual_override_does_not_set_or_clear_current_boss(tmp_path):
    resolver = _resolver(tmp_path, process_names=[])
    state = resolver.game_session.load()
    state.current_boss = CurrentBoss(
        name="恶兆妖鬼 Margit",
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
        confidence=0.9,
        source="test",
    )
    resolver.game_session.save(state)

    resolver.set_manual_override("elden_ring", now=datetime(2026, 1, 2, tzinfo=timezone.utc))
    updated = resolver.game_session.load()

    assert updated.current_game == "艾尔登法环"
    assert updated.current_boss is not None
    assert updated.current_boss.name == "恶兆妖鬼 Margit"


def test_manual_override_does_not_create_pending_memory(tmp_path):
    resolver = _resolver(tmp_path, process_names=[])

    resolver.set_manual_override("elden_ring", now=datetime(2026, 1, 1, tzinfo=timezone.utc))

    assert PendingMemoryQueue().list() == []


def test_manual_override_rejects_unsupported_game(tmp_path):
    resolver = _resolver(tmp_path, process_names=[])

    with pytest.raises(UnknownGameOverrideError, match="no_supported_knowledge"):
        resolver.set_manual_override("stardew_valley")
