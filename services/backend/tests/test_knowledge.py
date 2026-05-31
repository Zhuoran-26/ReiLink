from pathlib import Path

import pytest

from app.modules.elden_ring_knowledge.knowledge import EldenRingKnowledge, KnowledgeError
from app.modules.knowledge.catalog import GameCatalog
from app.modules.knowledge.retriever import GameKnowledgeRetriever


def test_margit_query_returns_tips():
    results = EldenRingKnowledge().search("Margit 怎么打", "elden_ring_boss_strategy")
    assert results
    assert any("Margit" in item.title for item in results)
    assert any("延迟" in item.content for item in results)


def test_margit_location_returns_location():
    results = EldenRingKnowledge().search("Margit 在哪", "elden_ring_location")
    assert results
    assert any("史东薇尔" in item.content for item in results)


def test_unknown_query_returns_empty():
    assert EldenRingKnowledge().search("zzzz nonexistent shard spiral") == []


def test_missing_files_raise_clear_error(tmp_path: Path):
    with pytest.raises(KnowledgeError, match="Knowledge file missing"):
        EldenRingKnowledge(tmp_path).search("Margit")


def test_generic_retriever_matches_margit_for_current_game():
    result = GameKnowledgeRetriever().retrieve(
        current_game="Elden Ring",
        user_message="Margit 怎么打",
        current_boss=None,
        game_session_state={},
        intent="elden_ring_boss_strategy",
    )

    assert result.matched is True
    assert result.game_id == "elden_ring"
    assert result.game_display_name == "艾尔登法环"
    assert result.match_source == "current_game"
    assert any("Margit" in snippet.title for snippet in result.snippets)
    assert any("margit" in topic for topic in result.topics)
    assert result.snippets[0].source_id
    assert result.snippets[0].source.endswith("data/knowledge/games/elden_ring/snippets.json")
    assert result.knowledge_path == "data/knowledge/games/elden_ring/snippets.json"
    assert result.supported_games_count == 1


def test_game_catalog_matches_explicit_user_game_alias():
    match = GameCatalog().match_game(
        current_game=None,
        user_message="我在玩老头环，先看看路线",
        game_session_state={},
    )

    assert match.matched_game_id == "elden_ring"
    assert match.matched_game_display_name == "艾尔登法环"
    assert match.match_source == "alias"
    assert match.knowledge_path == "data/knowledge/games/elden_ring/snippets.json"
    assert match.supported_games_count == 1


def test_game_catalog_reports_supported_status_for_elden_ring():
    game = GameCatalog().get_game("elden_ring")

    assert game is not None
    assert game.support_status == "supported"
    assert game.knowledge_available is True
    assert GameCatalog().is_knowledge_available(game) is True


def test_game_catalog_recognizes_planned_game_without_knowledge():
    match = GameCatalog().match_game(
        current_game=None,
        user_message="我在玩空洞骑士，螳螂领主怎么打",
        game_session_state={},
    )

    assert match.matched_game_id == "hollow_knight"
    assert match.matched_game_display_name == "空洞骑士"
    assert match.support_status == "planned"
    assert match.knowledge_available is False
    assert match.fallback_reason == "no_supported_knowledge"


def test_game_catalog_prefers_current_game_when_supported():
    match = GameCatalog().match_game(
        current_game="Elden Ring",
        user_message="老头环里恶兆妖鬼怎么打",
        game_session_state={},
    )

    assert match.matched_game_id == "elden_ring"
    assert match.match_source == "current_game"
    assert match.confidence >= 0.9


def test_generic_retriever_infers_game_from_content_alias_without_game_name():
    result = GameKnowledgeRetriever().retrieve(
        current_game=None,
        user_message="我在打恶兆妖鬼，节奏好怪",
        current_boss=None,
        game_session_state={},
        intent="casual_chat",
    )

    assert result.matched is True
    assert result.game_id == "elden_ring"
    assert result.game_display_name == "艾尔登法环"
    assert result.match_source == "alias"
    assert result.snippets
    assert any("恶兆妖鬼 Margit" in snippet.title for snippet in result.snippets)


def test_detected_game_takes_priority_over_session_game():
    result = GameKnowledgeRetriever().retrieve(
        current_game="Stardew Valley",
        user_message="Margit 怎么打",
        current_boss=None,
        game_session_state={"current_game": "Stardew Valley"},
        detected_game={
            "status": "running",
            "detected_game_id": "elden_ring",
            "display_name": "艾尔登法环",
            "process_name": "eldenring.exe",
            "match_confidence": 1.0,
            "match_source": "process",
            "knowledge_game_id": "elden_ring",
        },
        intent="elden_ring_boss_strategy",
    )

    assert result.matched is True
    assert result.game_id == "elden_ring"
    assert result.match_source == "process"
    assert result.active_source == "detector"


def test_manual_override_takes_priority_over_detected_game():
    result = GameKnowledgeRetriever().retrieve(
        current_game="Stardew Valley",
        user_message="Margit 怎么打",
        current_boss=None,
        game_session_state={"current_game": "Stardew Valley"},
        detected_game={
            "status": "running",
            "detected_game_id": "stardew_valley",
            "display_name": "星露谷物语",
            "process_name": "Stardew Valley.exe",
            "match_confidence": 1.0,
            "match_source": "process",
            "knowledge_game_id": None,
        },
        manual_override={
            "enabled": True,
            "game_id": "elden_ring",
            "display_name": "艾尔登法环",
            "source": "user",
        },
        intent="elden_ring_boss_strategy",
    )

    assert result.matched is True
    assert result.game_id == "elden_ring"
    assert result.match_source == "manual"
    assert result.active_source == "manual"
    assert result.knowledge_available is True


def test_manual_override_unknown_game_does_not_reuse_elden_ring():
    result = GameKnowledgeRetriever().retrieve(
        current_game="Elden Ring",
        user_message="Margit 怎么打",
        current_boss=None,
        game_session_state={"current_game": "Elden Ring"},
        manual_override={
            "enabled": True,
            "game_id": "stardew_valley",
            "display_name": "星露谷物语",
            "source": "user",
        },
        intent="elden_ring_boss_strategy",
    )

    assert result.matched is False
    assert result.game_id is None
    assert result.game_display_name == "星露谷物语"
    assert result.fallback_reason == "no_supported_knowledge"
    assert result.knowledge_available is False


def test_planned_game_query_does_not_use_elden_ring_snippets():
    result = GameKnowledgeRetriever().retrieve(
        current_game=None,
        user_message="我在玩空洞骑士，螳螂领主怎么打",
        current_boss=None,
        game_session_state={},
        intent="casual_chat",
    )

    assert result.matched is False
    assert result.game_id == "hollow_knight"
    assert result.game_display_name == "空洞骑士"
    assert result.support_status == "planned"
    assert result.knowledge_available is False
    assert result.snippets == []
    assert result.fallback_reason == "no_supported_knowledge"


def test_generic_retriever_matches_waterfowl_sample():
    result = GameKnowledgeRetriever().retrieve(
        current_game="Elden Ring",
        user_message="水鸟乱舞怎么躲",
        current_boss=None,
        game_session_state={},
        intent="elden_ring_boss_strategy",
    )

    assert result.matched is True
    assert any("玛莲妮亚" in snippet.title for snippet in result.snippets)
    assert any("waterfowl" in topic for topic in result.topics)


def test_generic_retriever_ignores_non_game_chat():
    result = GameKnowledgeRetriever().retrieve(
        current_game="Elden Ring",
        user_message="今天有点困",
        current_boss=None,
        game_session_state={},
        intent="casual_chat",
    )

    assert result.matched is False
    assert result.snippets == []


def test_current_boss_context_is_used_for_followup_game_message():
    result = GameKnowledgeRetriever().retrieve(
        current_game="Elden Ring",
        user_message="还是没打过",
        current_boss="恶兆妖鬼 Margit",
        game_session_state={},
        intent="casual_chat",
    )

    assert result.matched is True
    assert any("恶兆妖鬼 Margit" in snippet.title for snippet in result.snippets)


def test_current_boss_context_is_not_used_for_unrelated_preference():
    result = GameKnowledgeRetriever().retrieve(
        current_game="Elden Ring",
        user_message="我不喜欢长篇攻略",
        current_boss="恶兆妖鬼 Margit",
        game_session_state={},
        intent="casual_chat",
    )

    assert result.matched is False
    assert result.game_id == "elden_ring"
    assert result.snippets == []
    assert result.fallback_reason == "no_knowledge_match"


def test_generic_retriever_falls_back_for_unsupported_game():
    result = GameKnowledgeRetriever().retrieve(
        current_game="Stardew Valley",
        user_message="Margit 怎么打",
        current_boss=None,
        game_session_state={},
        intent="elden_ring_boss_strategy",
    )

    assert result.matched is False
    assert result.game_id is None
    assert result.fallback_reason == "no_game_detected"


def test_unsupported_current_game_does_not_reuse_elden_ring_content_alias():
    result = GameKnowledgeRetriever().retrieve(
        current_game="Stardew Valley",
        user_message="我在打恶兆妖鬼",
        current_boss=None,
        game_session_state={},
        intent="casual_chat",
    )

    assert result.matched is False
    assert result.game_id is None
    assert result.snippets == []
    assert result.fallback_reason == "no_game_detected"


def test_detected_unsupported_game_blocks_elden_ring_knowledge():
    result = GameKnowledgeRetriever().retrieve(
        current_game="Elden Ring",
        user_message="Margit 怎么打",
        current_boss=None,
        game_session_state={"current_game": "Elden Ring"},
        detected_game={
            "status": "running",
            "detected_game_id": "stardew_valley",
            "display_name": "星露谷物语",
            "process_name": "Stardew Valley.exe",
            "match_confidence": 1.0,
            "match_source": "process",
            "knowledge_game_id": None,
        },
        intent="elden_ring_boss_strategy",
    )

    assert result.matched is False
    assert result.game_id is None
    assert result.game_display_name == "星露谷物语"
    assert result.fallback_reason == "no_supported_knowledge"


def test_unknown_game_returns_no_game_detected():
    result = GameKnowledgeRetriever().retrieve(
        current_game=None,
        user_message="今天想随便聊两句",
        current_boss=None,
        game_session_state={},
        intent="casual_chat",
    )

    assert result.matched is False
    assert result.game_id is None
    assert result.fallback_reason == "no_game_detected"


def test_knowledge_disabled_does_not_inject_snippets(tmp_path):
    games_dir = tmp_path / "games"
    games_dir.mkdir()
    catalog = games_dir / "catalog.json"
    catalog.write_text(
        """
{
  "games": [
    {
      "game_id": "elden_ring",
      "display_name": "艾尔登法环",
      "aliases": ["Elden Ring", "艾尔登法环"],
      "knowledge_game_id": "elden_ring",
      "knowledge_path": "data/knowledge/games/elden_ring/snippets.json",
      "knowledge_available": true,
      "support_status": "supported",
      "enabled": false
    }
  ]
}
""",
        encoding="utf-8",
    )

    result = GameKnowledgeRetriever(games_dir).retrieve(
        current_game="Elden Ring",
        user_message="Margit 怎么打",
        current_boss=None,
        game_session_state={},
        intent="elden_ring_boss_strategy",
    )

    assert result.matched is False
    assert result.snippets == []
    assert result.support_status == "supported"
    assert result.knowledge_available is False
    assert result.fallback_reason == "knowledge_disabled"


def test_generic_retriever_returns_at_most_three_snippets():
    result = GameKnowledgeRetriever().retrieve(
        current_game="Elden Ring",
        user_message="Margit 水鸟乱舞 战斗节奏 怎么打 怎么躲",
        current_boss=None,
        game_session_state={},
        intent="elden_ring_boss_strategy",
        limit=10,
    )

    assert len(result.snippets) <= 3
