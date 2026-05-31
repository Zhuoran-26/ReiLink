from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.modules.app_settings.store import AppSettingsStore
from app.modules.game_detector.detector import LocalGameDetector, sync_game_session_from_detection
from app.modules.game_session.state import GameSessionStore
from app.modules.knowledge.catalog import GameCatalog, GameCatalogEntry, GameSwitchDetection
from app.schemas.api import (
    GameCatalogOption,
    GameContextResponse,
    GameDetectionResponse,
    GameStatus,
    ManualGameOverride,
)


class UnknownGameOverrideError(ValueError):
    pass


class GameContextStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings.game_context_state_path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load_manual_override(self) -> ManualGameOverride:
        if not self.path.is_file():
            return ManualGameOverride()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        except (OSError, json.JSONDecodeError):
            return ManualGameOverride()
        override = raw.get("manual_game_override") if isinstance(raw, dict) else None
        if not isinstance(override, dict):
            return ManualGameOverride()
        try:
            return ManualGameOverride(**override)
        except ValueError:
            return ManualGameOverride()

    def save_manual_override(self, override: ManualGameOverride) -> ManualGameOverride:
        payload = json.dumps({"manual_game_override": override.model_dump(mode="json")}, ensure_ascii=False, indent=2)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(f"{payload}\n", encoding="utf-8")
        return override

    def clear_manual_override(self) -> ManualGameOverride:
        return self.save_manual_override(ManualGameOverride())


class GameContextResolver:
    def __init__(
        self,
        *,
        catalog: GameCatalog | None = None,
        detector: LocalGameDetector | None = None,
        store: GameContextStore | None = None,
        game_session: GameSessionStore | None = None,
        settings_store: AppSettingsStore | None = None,
    ) -> None:
        self.catalog = catalog or GameCatalog()
        self.detector = detector or LocalGameDetector()
        self.store = store or GameContextStore()
        self.game_session = game_session or GameSessionStore()
        self.settings_store = settings_store or AppSettingsStore()

    def available_games(self) -> list[GameCatalogOption]:
        return [
            GameCatalogOption(
                game_id=game.game_id,
                display_name=game.display_name,
                enabled=game.enabled,
                knowledge_available=self.catalog.is_knowledge_available(game),
                support_status=game.support_status,
                knowledge_game_id=game.knowledge_game_id,
                manifest_path=game.manifest_path or None,
                knowledge_path=game.knowledge_path or None,
            )
            for game in self.catalog.enabled_games()
        ]

    def set_manual_override(self, game_id: str | None, now: datetime | None = None) -> ManualGameOverride:
        if not game_id:
            return self.store.clear_manual_override()
        game = self.catalog.get_game(game_id)
        if not game or not game.enabled:
            raise UnknownGameOverrideError("no_supported_knowledge")
        override = ManualGameOverride(
            enabled=True,
            game_id=game.game_id,
            display_name=game.display_name,
            set_at=now or datetime.now(timezone.utc),
            source="user",
        )
        self.store.save_manual_override(override)
        sync_game_session_from_manual_override(override, game_session=self.game_session)
        return override

    def resolve(
        self,
        *,
        user_message: str | None = None,
        detected_game: GameDetectionResponse | None = None,
        now: datetime | None = None,
        sync_session: bool = False,
    ) -> GameContextResponse:
        resolved_at = now or datetime.now(timezone.utc)
        app_settings = self.settings_store.load()
        detection = detected_game or self.detector.detect(now=resolved_at)
        manual_override = self.store.load_manual_override()
        session_state = self.game_session.load()
        available_games = self.available_games()
        user_switch = self.catalog.detect_explicit_game_switch(user_message or "")
        user_message_match = self._user_message_match(user_message or "")

        if manual_override.enabled and manual_override.game_id:
            response = self._manual_context(manual_override, detection, session_state.current_game, user_message_match, user_switch)
            if sync_session:
                sync_game_session_from_manual_override(manual_override, game_session=self.game_session)
            return response

        if user_switch:
            response = self._user_switch_context(user_switch, detection, session_state.current_game, manual_override, available_games)
            if sync_session:
                sync_game_session_from_user_switch(
                    response.active_game_display_name,
                    previous_game=session_state.current_game,
                    game_session=self.game_session,
                    timestamp=resolved_at,
                )
            return response

        detected_response = self._detected_context(detection, session_state.current_game, user_message_match, app_settings.auto_game_detection)
        if detected_response:
            detected_response.available_games = available_games
            if sync_session:
                sync_game_session_from_detection(detection, auto_game_detection=app_settings.auto_game_detection, game_session=self.game_session)
            return detected_response

        session_response = self._session_context(detection, session_state.current_game, user_message_match)
        if session_response:
            session_response.available_games = available_games
            return session_response

        if user_message_match:
            return GameContextResponse(
                active_game_id=user_message_match.game_id,
                active_game_display_name=user_message_match.display_name,
                active_source="user_message",
                manual_override=manual_override,
                detected_game=detection,
                session_game=session_state.current_game,
                previous_game=session_state.current_game,
                user_message_game_id=user_message_match.game_id,
                user_message_game_display_name=user_message_match.display_name,
                support_status=user_message_match.support_status,
                knowledge_available=self.catalog.is_knowledge_available(user_message_match),
                fallback_reason=None if self.catalog.is_knowledge_available(user_message_match) else "no_supported_knowledge",
                available_games=available_games,
            )

        return GameContextResponse(
            active_game_id=None,
            active_game_display_name=None,
            active_source="none",
            manual_override=manual_override,
            detected_game=detection,
            session_game=session_state.current_game,
            previous_game=session_state.current_game,
            user_message_game_id=None,
            user_message_game_display_name=None,
            support_status=None,
            knowledge_available=False,
            fallback_reason="no_game_detected",
            available_games=available_games,
        )

    def _manual_context(
        self,
        manual_override: ManualGameOverride,
        detection: GameDetectionResponse,
        session_game: str | None,
        user_message_match: GameCatalogEntry | None,
        user_switch: GameSwitchDetection | None,
    ) -> GameContextResponse:
        game = self.catalog.get_game(manual_override.game_id)
        knowledge_available = self.catalog.is_knowledge_available(game)
        manual_display_name = manual_override.display_name or (game.display_name if game else None)
        switch_game = user_switch.game if user_switch else None
        user_message_game_id = switch_game.game_id if switch_game else user_message_match.game_id if user_message_match else None
        user_message_game_display_name = (
            user_switch.display_name if user_switch else user_message_match.display_name if user_message_match else None
        )
        warnings = []
        if user_switch and _is_different_game(manual_display_name, user_switch.display_name):
            warnings.append("user_message_game_conflicts_with_manual_override")
        return GameContextResponse(
            active_game_id=game.game_id if game else manual_override.game_id,
            active_game_display_name=(game.display_name if game else manual_override.display_name),
            active_source="manual",
            manual_override=manual_override,
            detected_game=detection,
            session_game=session_game,
            previous_game=session_game,
            user_message_game_id=user_message_game_id,
            user_message_game_display_name=user_message_game_display_name,
            support_status=game.support_status if game else "unsupported",
            knowledge_available=knowledge_available,
            fallback_reason=None if knowledge_available else "no_supported_knowledge",
            warnings=warnings,
            available_games=self.available_games(),
        )

    def _user_switch_context(
        self,
        user_switch: GameSwitchDetection,
        detection: GameDetectionResponse,
        session_game: str | None,
        manual_override: ManualGameOverride,
        available_games: list[GameCatalogOption],
    ) -> GameContextResponse:
        game = user_switch.game
        knowledge_available = self.catalog.is_knowledge_available(game)
        display_name = game.display_name if game else user_switch.display_name
        fallback_reason = None if knowledge_available else "no_supported_knowledge" if game else "unknown_game"
        return GameContextResponse(
            active_game_id=game.game_id if game else None,
            active_game_display_name=display_name,
            active_source="user_switch",
            manual_override=manual_override,
            detected_game=detection,
            session_game=session_game,
            previous_game=session_game,
            game_switched=_is_different_game(session_game, display_name),
            user_message_game_id=game.game_id if game else None,
            user_message_game_display_name=display_name,
            support_status=game.support_status if game else "unsupported",
            knowledge_available=knowledge_available,
            fallback_reason=fallback_reason,
            available_games=available_games,
        )

    def _detected_context(
        self,
        detection: GameDetectionResponse,
        session_game: str | None,
        user_message_match: GameCatalogEntry | None,
        auto_game_detection: str,
    ) -> GameContextResponse | None:
        if auto_game_detection != "on" or detection.status != "running":
            return None
        game = self.catalog.get_game(detection.knowledge_game_id or detection.detected_game_id)
        if game and game.enabled and self.catalog.is_knowledge_available(game):
            return GameContextResponse(
                active_game_id=game.game_id,
                active_game_display_name=game.display_name,
                active_source="detector",
                manual_override=self.store.load_manual_override(),
                detected_game=detection,
                session_game=session_game,
                previous_game=session_game,
                user_message_game_id=user_message_match.game_id if user_message_match else None,
                user_message_game_display_name=user_message_match.display_name if user_message_match else None,
                support_status=game.support_status,
                knowledge_available=True,
                fallback_reason=None,
            )
        if game and game.enabled:
            return GameContextResponse(
                active_game_id=game.game_id,
                active_game_display_name=game.display_name,
                active_source="detector",
                manual_override=self.store.load_manual_override(),
                detected_game=detection,
                session_game=session_game,
                previous_game=session_game,
                user_message_game_id=user_message_match.game_id if user_message_match else None,
                user_message_game_display_name=user_message_match.display_name if user_message_match else None,
                support_status=game.support_status,
                knowledge_available=False,
                fallback_reason="no_supported_knowledge",
            )
        return GameContextResponse(
            active_game_id=detection.detected_game_id,
            active_game_display_name=detection.display_name,
            active_source="detector",
            manual_override=self.store.load_manual_override(),
            detected_game=detection,
            session_game=session_game,
            previous_game=session_game,
            user_message_game_id=user_message_match.game_id if user_message_match else None,
            user_message_game_display_name=user_message_match.display_name if user_message_match else None,
            support_status="unsupported",
            knowledge_available=False,
            fallback_reason="no_supported_knowledge",
        )

    def _session_context(
        self,
        detection: GameDetectionResponse,
        session_game: str | None,
        user_message_match: GameCatalogEntry | None,
    ) -> GameContextResponse | None:
        if not session_game:
            return None
        match = self.catalog.match_game(current_game=session_game, user_message="", game_session_state={})
        if match.matched_game_id:
            game = self.catalog.get_game(match.matched_game_id)
            return GameContextResponse(
                active_game_id=match.matched_game_id,
                active_game_display_name=match.matched_game_display_name,
                active_source="session",
                manual_override=self.store.load_manual_override(),
                detected_game=detection,
                session_game=session_game,
                previous_game=session_game,
                user_message_game_id=user_message_match.game_id if user_message_match else None,
                user_message_game_display_name=user_message_match.display_name if user_message_match else None,
                support_status=match.support_status,
                knowledge_available=self.catalog.is_knowledge_available(game),
                fallback_reason=None if self.catalog.is_knowledge_available(game) else "no_supported_knowledge",
            )
        return GameContextResponse(
            active_game_id=None,
            active_game_display_name=session_game,
            active_source="session",
            manual_override=self.store.load_manual_override(),
            detected_game=detection,
            session_game=session_game,
            previous_game=session_game,
            user_message_game_id=user_message_match.game_id if user_message_match else None,
            user_message_game_display_name=user_message_match.display_name if user_message_match else None,
            support_status="unsupported",
            knowledge_available=False,
            fallback_reason="no_supported_knowledge",
        )

    def _user_message_match(self, user_message: str) -> GameCatalogEntry | None:
        if not user_message.strip():
            return None
        match = self.catalog.match_game(current_game=None, user_message=user_message, game_session_state={})
        if not match.matched_game_id:
            return None
        return self.catalog.get_game(match.matched_game_id)

def sync_game_session_from_manual_override(
    manual_override: ManualGameOverride,
    *,
    game_session: GameSessionStore | None = None,
) -> bool:
    if not manual_override.enabled or not manual_override.display_name:
        return False
    store = game_session or GameSessionStore()
    state = store.load()
    state.current_game = manual_override.display_name
    state.last_updated_at = (manual_override.set_at or datetime.now(timezone.utc)).isoformat()
    store.save(state)
    return True


def sync_game_session_from_user_switch(
    display_name: str | None,
    *,
    previous_game: str | None,
    game_session: GameSessionStore | None = None,
    timestamp: datetime | None = None,
) -> bool:
    if not display_name:
        return False
    store = game_session or GameSessionStore()
    state = store.load()
    now = timestamp or datetime.now(timezone.utc)
    changed = _is_different_game(previous_game or state.current_game, display_name)
    state.current_game = display_name
    state.last_updated_at = now.isoformat()
    if changed:
        state.current_boss = None
        state.last_boss = None
        state.last_attempted_boss = None
        state.last_failed_boss = None
        state.last_cleared_boss = None
        state.current_activity = "game_switch"
        state.recent_game_topics = [display_name]
    store.save(state)
    return changed


def _is_different_game(previous_game: str | None, next_game: str | None) -> bool:
    if not previous_game or not next_game:
        return bool(next_game)
    return previous_game.strip().casefold() != next_game.strip().casefold()


def game_status_from_context(context: GameContextResponse) -> GameStatus:
    active = bool(context.active_game_id or context.active_game_display_name)
    confidence = 1.0 if context.active_source == "manual" else context.detected_game.match_confidence
    return GameStatus(
        game_id=context.active_game_id,
        game_name=context.active_game_display_name,
        process_name=context.detected_game.process_name,
        status="running" if active else context.detected_game.status,
        confidence=confidence if active else 0.0,
        tags=[],
        detected_game_id=context.detected_game.detected_game_id,
        display_name=context.detected_game.display_name,
        match_confidence=confidence if active else context.detected_game.match_confidence,
        match_source="manual" if context.active_source == "manual" else context.detected_game.match_source,
        knowledge_game_id=context.active_game_id if context.knowledge_available else None,
        detected_at=context.detected_game.detected_at,
    )
