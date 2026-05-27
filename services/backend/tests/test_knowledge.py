from pathlib import Path

import pytest

from app.modules.elden_ring_knowledge.knowledge import EldenRingKnowledge, KnowledgeError


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
