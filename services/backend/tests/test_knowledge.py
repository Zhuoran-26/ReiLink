from pathlib import Path

import pytest

from app.modules.elden_ring_knowledge.knowledge import EldenRingKnowledge, KnowledgeError
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
    assert any("Margit" in snippet.title for snippet in result.snippets)
    assert any("margit" in topic for topic in result.topics)
    assert result.snippets[0].source_id
    assert result.snippets[0].source.endswith("data/knowledge/games/elden_ring/snippets.json")


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
