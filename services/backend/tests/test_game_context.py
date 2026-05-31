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
                },
                "hollow_knight": {
                    "display_name": "空洞骑士",
                    "aliases": ["Hollow Knight", "空洞骑士"],
                    "process_names": ["hollow_knight.exe", "Hollow Knight"],
                    "steam_app_id": "367520",
                    "knowledge_game_id": "hollow_knight",
                },
                "sekiro": {
                    "display_name": "只狼",
                    "aliases": ["Sekiro", "只狼"],
                    "process_names": ["sekiro.exe", "Sekiro"],
                    "steam_app_id": "814380",
                    "knowledge_game_id": "sekiro",
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
    assert context.support_status == "supported"


def test_manual_override_can_select_planned_game_without_knowledge(tmp_path):
    resolver = _resolver(tmp_path, process_names=[])

    resolver.set_manual_override("sekiro", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    context = resolver.resolve()

    assert context.active_game_id == "sekiro"
    assert context.active_game_display_name == "只狼"
    assert context.active_source == "manual"
    assert context.support_status == "planned"
    assert context.knowledge_available is False
    assert context.fallback_reason == "no_supported_knowledge"


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


def test_detected_planned_game_is_not_unknown(tmp_path):
    resolver = _resolver(tmp_path, process_names=["sekiro.exe"])

    context = resolver.resolve()

    assert context.active_game_id == "sekiro"
    assert context.active_game_display_name == "只狼"
    assert context.active_source == "detector"
    assert context.support_status == "planned"
    assert context.knowledge_available is False
    assert context.fallback_reason == "no_supported_knowledge"


def test_explicit_user_switch_overrides_session_game_and_clears_old_boss(tmp_path):
    resolver = _resolver(tmp_path, process_names=[])
    state = resolver.game_session.load()
    state.current_game = "艾尔登法环"
    state.current_boss = CurrentBoss(
        name="女武神",
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
        confidence=0.95,
        source="test",
    )
    state.last_attempted_boss = "女武神"
    resolver.game_session.save(state)

    context = resolver.resolve(user_message="我在玩空洞骑士，螳螂领主怎么打", sync_session=True)
    updated = resolver.game_session.load()

    assert context.active_game_id == "hollow_knight"
    assert context.active_game_display_name == "空洞骑士"
    assert context.active_source == "user_switch"
    assert context.previous_game == "艾尔登法环"
    assert context.game_switched is True
    assert context.support_status == "supported"
    assert context.knowledge_available is True
    assert context.fallback_reason is None
    assert updated.current_game == "空洞骑士"
    assert updated.current_boss is None
    assert updated.last_attempted_boss is None
    assert PendingMemoryQueue().list() == []


def test_explicit_user_switch_with_negated_old_game_uses_new_game(tmp_path):
    resolver = _resolver(tmp_path, process_names=[])
    state = resolver.game_session.load()
    state.current_game = "艾尔登法环"
    resolver.game_session.save(state)

    context = resolver.resolve(user_message="我现在不是玩艾尔登法环，是在玩只狼", sync_session=True)

    assert context.active_game_id == "sekiro"
    assert context.active_game_display_name == "只狼"
    assert context.active_source == "user_switch"
    assert context.support_status == "planned"
    assert context.knowledge_available is False
    assert context.fallback_reason == "no_supported_knowledge"
    assert resolver.game_session.load().current_game == "只狼"


def test_explicit_unknown_game_switch_overrides_old_session_game(tmp_path):
    resolver = _resolver(tmp_path, process_names=[])
    state = resolver.game_session.load()
    state.current_game = "艾尔登法环"
    resolver.game_session.save(state)

    context = resolver.resolve(user_message="我在玩星之门遗迹", sync_session=True)

    assert context.active_game_id is None
    assert context.active_game_display_name == "星之门遗迹"
    assert context.active_source == "user_switch"
    assert context.support_status == "unsupported"
    assert context.knowledge_available is False
    assert context.fallback_reason == "unknown_game"
    assert resolver.game_session.load().current_game == "星之门遗迹"


def test_manual_override_blocks_explicit_user_switch_and_reports_warning(tmp_path):
    resolver = _resolver(tmp_path, process_names=[])

    resolver.set_manual_override("elden_ring", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    context = resolver.resolve(user_message="我在玩空洞骑士")

    assert context.active_game_id == "elden_ring"
    assert context.active_game_display_name == "艾尔登法环"
    assert context.active_source == "manual"
    assert context.user_message_game_id == "hollow_knight"
    assert context.user_message_game_display_name == "空洞骑士"
    assert context.warnings == ["user_message_game_conflicts_with_manual_override"]


def test_weak_user_message_mention_does_not_override_session_game(tmp_path):
    resolver = _resolver(tmp_path, process_names=[])
    state = resolver.game_session.load()
    state.current_game = "艾尔登法环"
    resolver.game_session.save(state)

    context = resolver.resolve(user_message="空洞骑士也挺好玩")

    assert context.active_game_id == "elden_ring"
    assert context.active_game_display_name == "艾尔登法环"
    assert context.active_source == "session"
    assert context.user_message_game_id == "hollow_knight"
    assert context.user_message_game_display_name == "空洞骑士"
    assert context.game_switched is False


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


def test_manual_override_rejects_unknown_game(tmp_path):
    resolver = _resolver(tmp_path, process_names=[])

    with pytest.raises(UnknownGameOverrideError, match="no_supported_knowledge"):
        resolver.set_manual_override("stardew_valley")
