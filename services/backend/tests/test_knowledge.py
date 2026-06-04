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
    assert result.manifest_status == "loaded"
    assert result.knowledge_pack_version == "0.1.0"
    assert result.knowledge_pack_language == "zh-CN"
    assert result.knowledge_pack_status == "sample"
    assert "boss" in result.coverage
    assert result.last_updated == "2026-06-01"
    assert result.supported_games_count == 2
    assert result.snippets[0].entry_id == result.snippets[0].source_id
    assert result.snippets[0].pack_id == "elden_ring"
    assert result.snippets[0].game_id == "elden_ring"
    assert result.snippets[0].score > 0
    assert result.snippets[0].matched_terms
    assert len(result.snippets[0].content) <= 420
    assert result.as_debug_dict()["snippet_previews"]
    assert result.as_debug_dict()["matched_terms"]
    assert result.as_debug_dict()["result_scores"]


def test_game_catalog_matches_explicit_user_game_alias():
    match = GameCatalog().match_game(
        current_game=None,
        user_message="我在玩老头环，先看看路线",
        game_session_state={},
    )

    assert match.matched_game_id == "elden_ring"
    assert match.matched_game_display_name == "艾尔登法环"
    assert match.match_source == "user_switch"
    assert match.knowledge_path == "data/knowledge/games/elden_ring/snippets.json"
    assert match.supported_games_count == 2


def test_game_catalog_reports_supported_status_for_elden_ring():
    game = GameCatalog().get_game("elden_ring")

    assert game is not None
    assert game.support_status == "supported"
    assert game.knowledge_available is True
    assert game.manifest_path == "data/knowledge/games/elden_ring/manifest.json"
    assert GameCatalog().is_knowledge_available(game) is True


def test_game_catalog_loads_elden_ring_manifest():
    catalog = GameCatalog()
    manifest = catalog.load_manifest(catalog.get_game("elden_ring"))

    assert manifest.manifest_status == "loaded"
    assert manifest.knowledge_pack_version == "0.1.0"
    assert manifest.knowledge_pack_language == "zh-CN"
    assert manifest.knowledge_pack_status == "sample"
    assert "boss" in manifest.coverage
    assert manifest.last_updated == "2026-06-01"


def test_game_catalog_loads_hollow_knight_as_supported():
    game = GameCatalog().get_game("hollow_knight")

    assert game is not None
    assert game.display_name == "空洞骑士"
    assert game.support_status == "supported"
    assert game.knowledge_available is True
    assert game.manifest_path == "data/knowledge/games/hollow_knight/manifest.json"
    assert game.knowledge_path == "data/knowledge/games/hollow_knight/snippets.json"
    assert GameCatalog().is_knowledge_available(game) is True


def test_game_catalog_loads_hollow_knight_manifest():
    catalog = GameCatalog()
    manifest = catalog.load_manifest(catalog.get_game("hollow_knight"))

    assert manifest.manifest_status == "loaded"
    assert manifest.knowledge_pack_version == "0.1.0"
    assert manifest.knowledge_pack_language == "zh-CN"
    assert manifest.knowledge_pack_status == "sample"
    assert "beginner_tip" in manifest.coverage
    assert manifest.last_updated == "2026-06-01"


def test_game_catalog_matches_hollow_knight_chinese_alias():
    match = GameCatalog().match_game(
        current_game=None,
        user_message="我在玩空洞骑士，螳螂领主怎么打",
        game_session_state={},
    )

    assert match.matched_game_id == "hollow_knight"
    assert match.matched_game_display_name == "空洞骑士"
    assert match.support_status == "supported"
    assert match.knowledge_available is True
    assert match.knowledge_path == "data/knowledge/games/hollow_knight/snippets.json"


def test_game_catalog_matches_hollow_knight_english_alias():
    match = GameCatalog().match_game(
        current_game=None,
        user_message="我在玩 Hollow Knight",
        game_session_state={},
    )

    assert match.matched_game_id == "hollow_knight"
    assert match.matched_game_display_name == "空洞骑士"
    assert match.support_status == "supported"
    assert match.knowledge_available is True


def test_game_catalog_recognizes_planned_game_without_knowledge():
    match = GameCatalog().match_game(
        current_game=None,
        user_message="我在玩只狼，弦一郎怎么打",
        game_session_state={},
    )

    assert match.matched_game_id == "sekiro"
    assert match.matched_game_display_name == "只狼"
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


def test_manual_override_hollow_knight_uses_hollow_knight_snippets():
    result = GameKnowledgeRetriever().retrieve(
        current_game="艾尔登法环",
        user_message="螳螂领主怎么打",
        current_boss=None,
        game_session_state={"current_game": "艾尔登法环"},
        manual_override={
            "enabled": True,
            "game_id": "hollow_knight",
            "display_name": "空洞骑士",
            "source": "user",
        },
        intent="casual_chat",
    )

    assert result.matched is True
    assert result.game_id == "hollow_knight"
    assert result.game_display_name == "空洞骑士"
    assert result.match_source == "manual"
    assert result.knowledge_available is True
    assert any("螳螂领主" in snippet.title for snippet in result.snippets)
    assert all("hollow_knight" in snippet.source for snippet in result.snippets)


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


def test_hollow_knight_query_uses_hollow_knight_snippets():
    result = GameKnowledgeRetriever().retrieve(
        current_game=None,
        user_message="我在玩空洞骑士，螳螂领主怎么打",
        current_boss=None,
        game_session_state={},
        intent="casual_chat",
    )

    assert result.game_id == "hollow_knight"
    assert result.game_display_name == "空洞骑士"
    assert result.matched is True
    assert result.support_status == "supported"
    assert result.knowledge_available is True
    assert result.knowledge_path == "data/knowledge/games/hollow_knight/snippets.json"
    assert result.manifest_status == "loaded"
    assert result.knowledge_pack_version == "0.1.0"
    assert result.knowledge_pack_language == "zh-CN"
    assert result.knowledge_pack_status == "sample"
    assert "boss" in result.coverage
    assert result.snippets
    assert any("螳螂领主" in snippet.title for snippet in result.snippets)
    assert all("hollow_knight" in snippet.source for snippet in result.snippets)
    assert result.fallback_reason is None


def test_hollow_knight_content_alias_matches_without_game_name():
    result = GameKnowledgeRetriever().retrieve(
        current_game=None,
        user_message="螳螂领主怎么打",
        current_boss=None,
        game_session_state={},
        intent="casual_chat",
    )

    assert result.matched is True
    assert result.game_id == "hollow_knight"
    assert result.game_display_name == "空洞骑士"
    assert result.match_source == "alias"
    assert any("螳螂领主" in snippet.title for snippet in result.snippets)
    assert all("hollow_knight" in snippet.source for snippet in result.snippets)


def test_hollow_knight_current_game_does_not_match_unrelated_boss():
    result = GameKnowledgeRetriever().retrieve(
        current_game="空洞骑士",
        user_message="大树守卫怎么打",
        current_boss=None,
        game_session_state={"current_game": "空洞骑士"},
        intent="casual_chat",
    )

    assert result.matched is False
    assert result.game_id == "hollow_knight"
    assert result.knowledge_available is True
    assert result.snippets == []
    assert result.fallback_reason == "no_knowledge_match"


def test_manual_override_elden_ring_does_not_use_hollow_knight_snippets():
    result = GameKnowledgeRetriever().retrieve(
        current_game="空洞骑士",
        user_message="螳螂领主怎么打",
        current_boss=None,
        game_session_state={"current_game": "空洞骑士"},
        manual_override={
            "enabled": True,
            "game_id": "elden_ring",
            "display_name": "艾尔登法环",
            "source": "user",
        },
        intent="casual_chat",
    )

    assert result.matched is False
    assert result.game_id == "elden_ring"
    assert result.game_display_name == "艾尔登法环"
    assert result.snippets == []
    assert result.fallback_reason == "no_knowledge_match"


def test_hollow_knight_retriever_returns_at_most_three_snippets():
    result = GameKnowledgeRetriever().retrieve(
        current_game="空洞骑士",
        user_message="螳螂领主 大黄蜂 假骑士 灵魂大师 地图 护符 回血",
        current_boss=None,
        game_session_state={"current_game": "空洞骑士"},
        intent="hollow_knight_general_help",
        limit=10,
    )

    assert result.matched is True
    assert result.game_id == "hollow_knight"
    assert len(result.snippets) <= 3
    assert all("hollow_knight" in snippet.source for snippet in result.snippets)


def test_planned_game_query_does_not_use_elden_ring_snippets():
    result = GameKnowledgeRetriever().retrieve(
        current_game=None,
        user_message="我在玩只狼，弦一郎怎么打",
        current_boss=None,
        game_session_state={},
        intent="casual_chat",
    )

    assert result.matched is False
    assert result.game_id == "sekiro"
    assert result.game_display_name == "只狼"
    assert result.support_status == "planned"
    assert result.knowledge_available is False
    assert result.snippets == []
    assert result.fallback_reason == "no_supported_knowledge"


def test_explicit_user_switch_overrides_session_and_detector_game():
    result = GameKnowledgeRetriever().retrieve(
        current_game="艾尔登法环",
        user_message="我在玩空洞骑士，螳螂领主怎么打",
        current_boss="女武神",
        game_session_state={"current_game": "艾尔登法环", "current_boss": {"name": "女武神"}},
        detected_game={
            "status": "running",
            "detected_game_id": "elden_ring",
            "display_name": "艾尔登法环",
            "process_name": "eldenring.exe",
            "match_confidence": 1.0,
            "match_source": "process",
            "knowledge_game_id": "elden_ring",
        },
        intent="casual_chat",
    )

    assert result.matched is True
    assert result.game_id == "hollow_knight"
    assert result.game_display_name == "空洞骑士"
    assert result.match_source == "user_switch"
    assert result.active_source == "user_switch"
    assert result.knowledge_available is True
    assert any("螳螂领主" in snippet.title for snippet in result.snippets)
    assert all("hollow_knight" in snippet.source for snippet in result.snippets)
    assert result.fallback_reason is None


def test_explicit_user_switch_phrase_with_old_game_uses_new_game():
    result = GameKnowledgeRetriever().retrieve(
        current_game="艾尔登法环",
        user_message="先不聊艾尔登法环了，我在玩空洞骑士",
        current_boss=None,
        game_session_state={"current_game": "艾尔登法环"},
        intent="casual_chat",
    )

    assert result.game_id == "hollow_knight"
    assert result.game_display_name == "空洞骑士"
    assert result.match_source == "user_switch"
    assert result.knowledge_available is True
    assert result.fallback_reason == "no_knowledge_match"


def test_explicit_user_switch_negating_old_game_uses_new_game():
    result = GameKnowledgeRetriever().retrieve(
        current_game="艾尔登法环",
        user_message="我现在不是玩艾尔登法环，是在玩只狼",
        current_boss=None,
        game_session_state={"current_game": "艾尔登法环"},
        intent="casual_chat",
    )

    assert result.game_id == "sekiro"
    assert result.game_display_name == "只狼"
    assert result.support_status == "planned"
    assert result.knowledge_available is False
    assert result.fallback_reason == "no_supported_knowledge"


def test_explicit_user_switch_with_change_game_phrase_matches_catalog_alias():
    result = GameKnowledgeRetriever().retrieve(
        current_game="艾尔登法环",
        user_message="换个游戏，我玩赛博朋克",
        current_boss=None,
        game_session_state={"current_game": "艾尔登法环"},
        intent="casual_chat",
    )

    assert result.game_id == "cyberpunk_2077"
    assert result.game_display_name == "赛博朋克2077"
    assert result.support_status == "detected_only"
    assert result.knowledge_available is False


def test_explicit_unknown_game_switch_blocks_old_game_knowledge():
    result = GameKnowledgeRetriever().retrieve(
        current_game="艾尔登法环",
        user_message="我在玩星之门遗迹",
        current_boss="恶兆妖鬼 Margit",
        game_session_state={"current_game": "艾尔登法环"},
        intent="elden_ring_boss_strategy",
    )

    assert result.matched is False
    assert result.game_id is None
    assert result.game_display_name == "星之门遗迹"
    assert result.active_source == "user_switch"
    assert result.support_status == "unsupported"
    assert result.knowledge_available is False
    assert result.snippets == []
    assert result.fallback_reason == "unknown_game"


def test_explicit_unknown_named_game_switch_extracts_display_name():
    result = GameKnowledgeRetriever().retrieve(
        current_game="艾尔登法环",
        user_message="我现在玩一个叫星之门遗迹的游戏",
        current_boss=None,
        game_session_state={"current_game": "艾尔登法环"},
        intent="casual_chat",
    )

    assert result.matched is False
    assert result.game_id is None
    assert result.game_display_name == "星之门遗迹"
    assert result.fallback_reason == "unknown_game"


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
    assert result.game_display_name == "Stardew Valley"
    assert result.fallback_reason == "unknown_game"


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
    assert result.game_display_name == "Stardew Valley"
    assert result.fallback_reason == "unknown_game"


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


def test_missing_manifest_does_not_block_snippet_retrieval(tmp_path):
    games_dir = tmp_path / "games"
    snippets_path = games_dir / "test_game" / "snippets.json"
    missing_manifest_path = games_dir / "test_game" / "missing_manifest.json"
    snippets_path.parent.mkdir(parents=True)
    snippets_path.write_text(
        """
[
  {
    "id": "test_boss",
    "title": "Test Boss",
    "kind": "boss_strategy",
    "topics": ["test_game", "boss_strategy"],
    "aliases": ["Test Boss"],
    "summary": "A short local sample."
  }
]
""",
        encoding="utf-8",
    )
    (games_dir / "catalog.json").write_text(
        f"""
{{
  "games": [
    {{
      "game_id": "test_game",
      "display_name": "测试游戏",
      "aliases": ["Test Game", "测试游戏"],
      "knowledge_game_id": "test_game",
      "manifest_path": "{missing_manifest_path}",
      "knowledge_path": "{snippets_path}",
      "knowledge_available": true,
      "support_status": "supported",
      "enabled": true
    }}
  ]
}}
""",
        encoding="utf-8",
    )

    result = GameKnowledgeRetriever(games_dir).retrieve(
        current_game="测试游戏",
        user_message="Test Boss 怎么打",
        current_boss=None,
        game_session_state={},
        intent="casual_chat",
    )

    assert result.matched is True
    assert result.snippets
    assert result.manifest_status == "manifest_missing"
    assert result.knowledge_pack_version == "unknown"
    assert result.knowledge_pack_language == "unknown"
    assert result.knowledge_pack_status == "unknown"
    assert result.coverage == []
    assert result.last_updated == "unknown"


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


def test_snippet_preview_length_limit_is_enforced_for_long_entries(tmp_path):
    games_dir = tmp_path / "games"
    snippets_path = games_dir / "long_game" / "snippets.json"
    snippets_path.parent.mkdir(parents=True)
    snippets_path.write_text(
        """
[
  {
    "id": "long_boss",
    "title": "Long Boss",
    "kind": "boss_strategy",
    "topics": ["long_game", "boss_strategy"],
    "aliases": ["Long Boss"],
    "summary": "%s"
  }
]
"""
        % ("Long Boss " + "very long content " * 80),
        encoding="utf-8",
    )
    (games_dir / "catalog.json").write_text(
        f"""
{{
  "games": [
    {{
      "game_id": "long_game",
      "display_name": "长文本游戏",
      "aliases": ["Long Game", "长文本游戏"],
      "knowledge_game_id": "long_game",
      "knowledge_path": "{snippets_path}",
      "knowledge_available": true,
      "support_status": "supported",
      "enabled": true
    }}
  ]
}}
""",
        encoding="utf-8",
    )

    result = GameKnowledgeRetriever(games_dir).retrieve(
        current_game="长文本游戏",
        user_message="Long Boss 怎么打",
        current_boss=None,
        game_session_state={},
        intent="casual_chat",
    )

    assert result.matched is True
    assert len(result.snippets[0].content) <= 420
