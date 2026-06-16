import json

from fastapi.testclient import TestClient

from app.main import app
from app.modules.dialogue_agent import semantic_extraction as sem

client = TestClient(app)


def assert_chinese_reply(reply: str):
    assert "##" not in reply
    assert any("\u4e00" <= char <= "\u9fff" for char in reply)


def test_health_ok():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_game_status_schema():
    data = client.get("/api/game/status").json()
    assert {
        "game_id",
        "game_name",
        "process_name",
        "status",
        "confidence",
        "tags",
        "detected_game_id",
        "display_name",
        "match_confidence",
        "match_source",
        "knowledge_game_id",
        "detected_at",
    } <= data.keys()


def test_game_detected_schema():
    response = client.get("/api/game/detected")

    assert response.status_code == 200
    data = response.json()
    assert {
        "status",
        "detected_game_id",
        "display_name",
        "process_name",
        "match_confidence",
        "match_source",
        "knowledge_game_id",
        "detected_at",
    } <= data.keys()
    assert data["status"] in {"running", "idle", "unknown"}


def test_game_context_schema():
    response = client.get("/api/game/context")

    assert response.status_code == 200
    data = response.json()
    assert {
        "active_game_id",
        "active_game_display_name",
        "active_source",
        "manual_override",
        "detected_game",
        "session_game",
        "previous_game",
        "game_switched",
        "support_status",
        "knowledge_available",
        "fallback_reason",
        "warnings",
        "available_games",
    } <= data.keys()
    assert data["active_source"] in {"manual", "user_switch", "detector", "session", "user_message", "none"}
    assert isinstance(data["knowledge_available"], bool)
    assert isinstance(data["game_switched"], bool)
    assert isinstance(data["warnings"], list)
    assert any(game["game_id"] == "elden_ring" for game in data["available_games"])
    assert any(
        game["game_id"] == "hollow_knight"
        and game["support_status"] == "supported"
        and game["knowledge_available"] is True
        and game["manifest_path"] == "data/knowledge/games/hollow_knight/manifest.json"
        for game in data["available_games"]
    )


def test_manual_game_context_api_sets_and_clears_override():
    selected = client.post("/api/game/context/manual", json={"game_id": "elden_ring"})

    assert selected.status_code == 200
    data = selected.json()
    assert data["active_game_id"] == "elden_ring"
    assert data["active_source"] == "manual"
    assert data["manual_override"]["enabled"] is True
    assert data["knowledge_available"] is True
    assert data["support_status"] == "supported"

    cleared = client.post("/api/game/context/manual", json={"game_id": None})

    assert cleared.status_code == 200
    assert cleared.json()["manual_override"]["enabled"] is False


def test_manual_game_context_api_allows_planned_game_without_knowledge():
    selected = client.post("/api/game/context/manual", json={"game_id": "sekiro"})

    assert selected.status_code == 200
    data = selected.json()
    assert data["active_game_id"] == "sekiro"
    assert data["active_game_display_name"] == "只狼"
    assert data["active_source"] == "manual"
    assert data["support_status"] == "planned"
    assert data["knowledge_available"] is False
    assert data["fallback_reason"] == "no_supported_knowledge"

    client.post("/api/game/context/manual", json={"game_id": None})


def test_manual_game_context_api_rejects_unsupported_game():
    response = client.post("/api/game/context/manual", json={"game_id": "stardew_valley"})

    assert response.status_code == 400
    assert response.json()["detail"] == "no_supported_knowledge"


def test_chat_returns_chinese_reply():
    response = client.post("/api/chat", json={"message": "Margit 怎么打", "session_id": "api-test"})
    assert response.status_code == 200
    assert_chinese_reply(response.json()["reply"])


def test_identity_chat_has_no_sources():
    response = client.post("/api/chat", json={"message": "你是谁", "session_id": "api-identity"})
    assert response.status_code == 200
    data = response.json()
    assert data["sources"] == []
    assert_chinese_reply(data["reply"])


def test_invalid_chat_input_returns_422():
    response = client.post("/api/chat", json={"message": "", "session_id": "api-test"})
    assert response.status_code == 422


def test_debug_provider_returns_current_provider():
    response = client.get("/api/debug/provider")
    assert response.status_code == 200
    data = response.json()
    assert {
        "provider",
        "model",
        "base_url",
        "api_key_loaded",
        "configured_provider",
        "fallback_to_mock",
        "env_file_loaded",
        "env_file_path",
        "persona_mode",
        "model_route_mode",
        "deepseek_model_fast",
        "deepseek_model_pro",
        "selected_model",
        "main_reply_model",
        "route_reason",
        "route_intent",
        "estimated_complexity",
        "provider_latency_ms",
        "semantic_extraction_model",
        "fallback_reason",
    } <= data.keys()
    assert isinstance(data["api_key_loaded"], bool)
    assert isinstance(data["fallback_to_mock"], bool)
    assert isinstance(data["env_file_loaded"], bool)
    assert data["persona_mode"] in {"guarded", "minimal"}
    serialized = json.dumps(data, ensure_ascii=False).lower()
    assert "api_key" not in serialized.replace("api_key_loaded", "")
    assert "authorization" not in serialized
    assert "bearer" not in serialized


def test_setup_status_reports_missing_deepseek_key(monkeypatch):
    monkeypatch.setattr("app.api.routes_setup.settings.llm_provider", "deepseek")
    monkeypatch.setattr("app.api.routes_setup.settings.deepseek_api_key", "")

    response = client.get("/api/setup/status")

    assert response.status_code == 200
    data = response.json()
    assert data["backend_ready"] is True
    assert data["provider"] == "deepseek"
    assert data["provider_configured"] is False
    assert data["api_key_loaded"] is False
    assert data["needs_setup"] is True
    assert data["missing_items"] == ["DEEPSEEK_API_KEY"]


def test_setup_status_reports_configured_provider_without_secret(monkeypatch):
    monkeypatch.setattr("app.api.routes_setup.settings.llm_provider", "deepseek")
    monkeypatch.setattr("app.api.routes_setup.settings.deepseek_api_key", "test-secret-key")
    monkeypatch.setattr("app.api.routes_setup.settings.model_preference", "fast")
    monkeypatch.setattr("app.api.routes_setup.settings.persona_mode", "minimal")

    response = client.get("/api/setup/status")

    assert response.status_code == 200
    data = response.json()
    assert data["provider_configured"] is True
    assert data["api_key_loaded"] is True
    assert data["needs_setup"] is False
    assert data["missing_items"] == []
    assert data["model_preference"] == "fast"
    assert data["persona_mode"] == "minimal"
    assert data["memory_ready"] is True
    assert data["knowledge_ready"] is True
    assert data["base_url"] == "https://api.deepseek.com"
    assert data["fast_model"] == "deepseek-v4-flash"
    assert data["pro_model"] == "deepseek-v4-pro"
    serialized = json.dumps(data, ensure_ascii=False)
    assert "test-secret-key" not in serialized
    assert "authorization" not in serialized.lower()
    assert "bearer" not in serialized.lower()


def test_settings_routes_persist_safe_values():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert {
        "persona_mode",
        "debug_panel",
        "memory_enabled",
        "pending_memory_mode",
        "response_length",
        "model_preference",
        "proactive_companion",
        "proactive_sensitivity",
        "auto_game_detection",
        "overlay_enabled",
        "overlay_position",
        "overlay_opacity",
        "overlay_message_count",
        "onboarding_completed",
        "onboarding_last_seen_at",
    } <= data.keys()
    assert data["onboarding_completed"] is False
    assert data["onboarding_last_seen_at"] is None
    serialized = json.dumps(data, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "deepseek" not in serialized

    seen_at = "2026-06-01T12:00:00.000Z"
    updated = client.post(
        "/api/settings",
        json={
            "persona_mode": "minimal",
            "debug_panel": "hide",
            "memory_enabled": False,
            "pending_memory_mode": "manual",
            "response_length": "short",
            "model_preference": "pro",
            "proactive_companion": "on",
            "proactive_sensitivity": "high",
            "auto_game_detection": "off",
            "overlay_enabled": "on",
            "overlay_position": "top-left",
            "overlay_opacity": 0.85,
            "overlay_message_count": 1,
            "onboarding_completed": True,
            "onboarding_last_seen_at": seen_at,
        },
    )

    assert updated.status_code == 200
    saved = updated.json()
    assert saved["persona_mode"] == "minimal"
    assert saved["debug_panel"] == "hide"
    assert saved["memory_enabled"] is False
    assert saved["pending_memory_mode"] == "manual"
    assert saved["response_length"] == "short"
    assert saved["model_preference"] == "pro"
    assert saved["proactive_companion"] == "on"
    assert saved["proactive_sensitivity"] == "high"
    assert saved["auto_game_detection"] == "off"
    assert saved["overlay_enabled"] == "on"
    assert saved["overlay_position"] == "top-left"
    assert saved["overlay_opacity"] == 0.85
    assert saved["overlay_message_count"] == 1
    assert saved["onboarding_completed"] is True
    assert saved["onboarding_last_seen_at"] == seen_at
    assert client.get("/api/settings").json() == saved
    assert client.get("/api/debug/provider").json()["persona_mode"] == "minimal"
    assert client.get("/api/proactive/status").json()["enabled"] is True
    saved_serialized = json.dumps(saved, ensure_ascii=False).lower()
    assert "api_key" not in saved_serialized
    assert "secret" not in saved_serialized

    reset_onboarding = client.post(
        "/api/settings",
        json={"onboarding_completed": False, "onboarding_last_seen_at": None},
    )
    assert reset_onboarding.status_code == 200
    reset_saved = reset_onboarding.json()
    assert reset_saved["onboarding_completed"] is False
    assert reset_saved["onboarding_last_seen_at"] is None
    assert client.get("/api/settings").json()["onboarding_last_seen_at"] is None


def test_debug_chat_returns_last_latency_fields():
    client.post("/api/chat", json={"message": "你好", "session_id": "api-debug-chat"})

    response = client.get("/api/debug/chat")

    assert response.status_code == 200
    data = response.json()
    assert {
        "intent",
        "selected_model",
        "model_route_mode",
        "route_reason",
        "route_intent",
        "estimated_complexity",
        "provider_latency_ms",
        "semantic_extraction_model",
        "main_reply_model",
        "thinking_enabled",
        "reasoning_effort",
        "prompt_tokens_estimate",
        "llm_latency_ms",
        "memory_latency_ms",
        "total_latency_ms",
        "request_started_at",
        "response_latency_ms",
        "knowledge_matched",
        "knowledge_game_id",
        "knowledge_game_display_name",
        "knowledge_match_source",
        "knowledge_path",
        "manifest_path",
        "manifest_status",
        "knowledge_pack_version",
        "knowledge_pack_language",
        "knowledge_pack_status",
        "coverage",
        "last_updated",
        "knowledge_supported_games_count",
        "knowledge_fallback_reason",
        "knowledge_confidence",
        "active_game_id",
        "active_game_display_name",
        "active_source",
        "support_status",
        "knowledge_available",
        "matched_topics",
        "snippets_count",
        "snippet_titles",
        "snippet_previews",
        "matched_terms",
        "result_scores",
        "knowledge_used_in_prompt",
        "knowledge_retrieval_status",
        "knowledge_not_used_reason",
        "knowledge_retrieval_min_score",
    } <= data.keys()
    assert data["knowledge_matched"] is False
    assert data["snippets_count"] == 0


def test_memory_profile_and_episodes_routes():
    client.post("/api/chat", json={"message": "我不喜欢长篇攻略", "session_id": "api-memory"})

    pending = client.get("/api/memory/pending")
    assert pending.status_code == 200
    pending_items = pending.json()
    assert pending_items
    assert pending_items[0]["type"] == "user_preference"
    assert "payload" not in pending_items[0]

    profile = client.get("/api/memory/profile")
    assert profile.status_code == 200
    assert profile.json()["preferred_tone"] is None

    accepted = client.post(f"/api/memory/pending/{pending_items[0]['id']}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    profile = client.get("/api/memory/profile")
    assert profile.status_code == 200
    assert profile.json()["preferred_tone"] == "不喜欢长篇攻略"

    episodes = client.get("/api/memory/episodes")
    assert episodes.status_code == 200
    assert episodes.json()[0]["summary"] == "玩家不喜欢长篇攻略"


def test_debug_memory_returns_provenance_items():
    session_id = "api-memory-debug"
    client.post("/api/debug/game-session/reset")
    client.post("/api/chat", json={"message": "我现在卡在女武神", "session_id": session_id})
    client.post("/api/chat", json={"message": "我不喜欢长篇攻略", "session_id": session_id})
    pending_items = client.get("/api/memory/pending").json()
    assert pending_items
    preference_item = next(item for item in pending_items if item["type"] == "user_preference")
    client.post(f"/api/memory/pending/{preference_item['id']}/accept")

    response = client.get(f"/api/debug/memory?session_id={session_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["prompt_order"] == ["current_user_message", "current_session", "memory", "persona"]
    assert data["memory_written"] is True
    assert data["recent_episode_count"] >= 1
    sources = {item["source"] for item in data["items"]}
    assert {"current_session", "episode"} <= sources
    assert all(item["text"] for item in data["items"])

    game_data = client.get("/api/debug/game-session").json()
    assert game_data["current_boss"]["name"] == "女武神"


def test_debug_game_session_routes():
    client.post("/api/debug/game-session/reset")
    client.post("/api/chat", json={"message": "我现在卡在女武神", "session_id": "api-game-session"})

    response = client.get("/api/debug/game-session")

    assert response.status_code == 200
    data = response.json()
    assert data["current_game"] == "艾尔登法环"
    assert data["current_boss"]["name"] == "女武神"
    assert data["current_boss"]["confidence"] >= 0.9
    assert data["current_boss"]["is_fresh"] is True
    assert {
        "last_boss",
        "last_attempted_boss",
        "last_cleared_boss",
        "boss_history",
        "death_count",
        "frustration_count",
        "last_game_intent",
    } <= data.keys()
    assert data["last_attempted_boss"] == "女武神"
    assert data["boss_history"][0]["name"] == "女武神"

    reset = client.post("/api/debug/game-session/reset")
    assert reset.status_code == 200
    assert reset.json() == {"status": "reset"}
    assert client.get("/api/debug/game-session").json()["current_boss"] is None


def test_prompt_preview_endpoint_returns_structured_context_without_secrets():
    session_id = "api-prompt-preview"
    client.post("/api/debug/game-session/reset")
    client.post("/api/chat", json={"message": "我现在卡在女武神", "session_id": session_id})

    response = client.get(f"/api/debug/prompt-preview?session_id={session_id}")

    assert response.status_code == 200
    data = response.json()
    assert {
        "persona_mode",
        "current_user_message",
        "prompt_order",
        "model_route_summary",
        "game_context_summary",
        "session_focus_summary",
        "game_state_summary",
        "persona_pack_summary",
        "knowledge_summary",
        "memory_summary",
        "final_context_summary",
        "warnings",
    } <= data.keys()
    assert data["persona_mode"] in {"guarded", "minimal"}
    assert {"selected_model", "route_reason"} <= data["model_route_summary"].keys()
    assert data["current_user_message"] == "我现在卡在女武神"
    assert data["game_state_summary"]["current_game"] == "艾尔登法环"
    assert data["game_context_summary"]["active_source"] in {"manual", "user_switch", "detector", "session", "user_message", "none"}
    assert {"support_status", "knowledge_available", "fallback_reason"} <= data["game_context_summary"].keys()
    assert data["game_state_summary"]["current_boss"]["name"] == "女武神"
    assert data["game_state_summary"]["freshness"] == "fresh"
    assert data["persona_pack_summary"]["id"] == "rei"
    assert data["persona_pack_summary"]["enabled"] is True
    assert data["persona_pack_summary"]["status"] == "loaded"
    assert data["persona_pack_summary"]["version"] == "1.1.2"
    assert data["persona_pack_summary"]["raw_content_omitted"] is True
    assert data["persona_pack_summary"]["path_omitted"] is True
    assert data["persona_pack_summary"]["fallback_used"] is False
    assert data["persona_pack_summary"]["persona_section_truncated"] in {True, False}
    assert "persona" in data["persona_pack_summary"]["injected_sections"]
    assert "style_calibration" in data["persona_pack_summary"]["injected_sections"]
    assert "response_patterns" in data["persona_pack_summary"]["injected_sections"]
    assert data["persona_pack_summary"]["prompt_char_count"] <= data["persona_pack_summary"]["prompt_char_budget"]
    assert "persona_pack" in data["prompt_order"]
    persona_block = next(
        block for block in data["final_context_summary"]["blocks"] if block["name"] == "persona_pack"
    )
    assert persona_block["raw_content_omitted"] is True
    assert persona_block["path_omitted"] is True
    assert "persona" in persona_block["loaded_sections"]
    assert "persona" in persona_block["injected_sections"]
    assert "style_calibration" in persona_block["injected_sections"]
    assert "response_patterns" in persona_block["injected_sections"]
    assert "persona_section_truncated" in persona_block
    assert isinstance(data["memory_summary"]["injected"], list)
    assert isinstance(data["memory_summary"]["skipped"], list)
    assert data["final_context_summary"]["raw_prompt_omitted"] is True
    serialized = json.dumps(data, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "deepseek_api_key" not in serialized
    assert "authorization" not in serialized
    assert "local-first game companion agent" not in serialized
    assert "rei 是 reilink 的原创游戏陪伴角色" not in serialized
    assert "话多程度：1/5" not in serialized
    assert "/Users/" not in serialized


def test_prompt_preview_sanitizes_sensitive_preview_strings():
    session_id = "api-prompt-preview-sensitive"
    client.post(
        "/api/chat",
        json={
            "message": "不要显示 /Users/aragoto/private/.env raw JSON raw stdout DEEPSEEK_API_KEY=secret",
            "session_id": session_id,
        },
    )

    response = client.get(f"/api/debug/prompt-preview?session_id={session_id}")

    assert response.status_code == 200
    serialized = json.dumps(response.json(), ensure_ascii=False).lower()
    assert "/users/aragoto" not in serialized
    assert ".env" not in serialized
    assert "raw json" not in serialized
    assert "raw stdout" not in serialized
    assert "api_key" not in serialized
    assert "deepseek_api_key" not in serialized
    assert "secret" not in serialized


def test_persona_pack_does_not_bypass_pending_memory_confirmation():
    client.post("/api/memory/reset")
    client.post(
        "/api/chat",
        json={
            "message": "记住我打 Boss 前喜欢先探索地图，不喜欢直接硬打。",
            "session_id": "api-persona-pack-memory-boundary",
        },
    )

    pending_items = client.get("/api/memory/pending").json()

    assert any(item["type"] == "playstyle" and "探索地图" in item["text"] for item in pending_items)
    assert client.get("/api/memory/profile").json()["preferred_tone"] is None

    client.post("/api/memory/pending/clear")
    client.post(
        "/api/chat",
        json={
            "message": "以后不用记住这个，只是我这次随便说一下。",
            "session_id": "api-persona-pack-memory-negative",
        },
    )

    assert client.get("/api/memory/pending").json() == []


def test_prompt_preview_shows_knowledge_summary():
    session_id = "api-prompt-preview-knowledge"
    client.post("/api/debug/game-session/reset")
    client.post("/api/chat", json={"message": "Margit 怎么打", "session_id": session_id})

    response = client.get(f"/api/debug/prompt-preview?session_id={session_id}")

    assert response.status_code == 200
    knowledge = response.json()["knowledge_summary"]
    assert knowledge["knowledge_matched"] is True
    assert knowledge["game_id"] == "elden_ring"
    assert knowledge["matched_game_id"] == "elden_ring"
    assert knowledge["matched_game_display_name"] == "艾尔登法环"
    assert knowledge["support_status"] == "supported"
    assert knowledge["knowledge_available"] is True
    assert knowledge["match_source"] in {"alias", "current_game", "user_message"}
    assert knowledge["knowledge_path"] == "data/knowledge/games/elden_ring/snippets.json"
    assert knowledge["manifest_path"] == "data/knowledge/games/elden_ring/manifest.json"
    assert knowledge["manifest_status"] == "loaded"
    assert knowledge["knowledge_pack_version"] == "0.1.0"
    assert knowledge["knowledge_pack_language"] == "zh-CN"
    assert knowledge["knowledge_pack_status"] == "sample"
    assert "boss" in knowledge["coverage"]
    assert knowledge["last_updated"] == "2026-06-01"
    assert knowledge["supported_games_count"] == 2
    assert knowledge["snippets_count"] > 0
    assert knowledge["snippet_titles"]
    assert knowledge["snippet_previews"]
    assert knowledge["matched_terms"]
    assert knowledge["result_scores"]
    assert knowledge["knowledge_used_in_prompt"] is True
    assert knowledge["retrieval_status"] == "used"
    assert knowledge["not_used_reason"] is None
    serialized = json.dumps(knowledge, ensure_ascii=False)
    assert "api_key" not in serialized.lower()
    assert ".env" not in serialized
    assert "/Users/" not in serialized
    assert knowledge["fallback_reason"] is None


def test_prompt_preview_shows_hollow_knight_knowledge_summary():
    session_id = "api-prompt-preview-hollow-knight"
    client.post("/api/debug/game-session/reset")
    client.post("/api/chat", json={"message": "我在玩空洞骑士，螳螂领主怎么打？", "session_id": session_id})

    response = client.get(f"/api/debug/prompt-preview?session_id={session_id}")

    assert response.status_code == 200
    data = response.json()
    game_context = data["game_context_summary"]
    knowledge = data["knowledge_summary"]
    assert game_context["active_game_id"] == "hollow_knight"
    assert game_context["active_game_display_name"] == "空洞骑士"
    assert game_context["active_source"] == "user_switch"
    assert game_context["support_status"] == "supported"
    assert game_context["knowledge_available"] is True
    assert game_context["fallback_reason"] is None
    assert knowledge["active_game_id"] == "hollow_knight"
    assert knowledge["active_game_display_name"] == "空洞骑士"
    assert knowledge["active_source"] == "user_switch"
    assert knowledge["support_status"] == "supported"
    assert knowledge["knowledge_available"] is True
    assert knowledge["manifest_status"] == "loaded"
    assert knowledge["knowledge_pack_version"] == "0.1.0"
    assert knowledge["knowledge_pack_language"] == "zh-CN"
    assert knowledge["knowledge_pack_status"] == "sample"
    assert "beginner_tip" in knowledge["coverage"]
    assert knowledge["knowledge_used_in_prompt"] is True
    assert knowledge["retrieval_status"] == "used"
    assert knowledge["snippets_count"] > 0
    assert any("螳螂领主" in title for title in knowledge["snippet_titles"])
    assert "螳螂领主" in knowledge["matched_topics"]
    assert knowledge["fallback_reason"] is None


def test_prompt_preview_warns_on_negated_clear_phrase():
    session_id = "api-prompt-preview-negated-clear"
    client.post("/api/debug/game-session/reset")
    client.post("/api/chat", json={"message": "我现在卡在恶兆妖鬼", "session_id": session_id})
    client.post("/api/chat", json={"message": "还是没打过", "session_id": session_id})

    response = client.get(f"/api/debug/prompt-preview?session_id={session_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["current_user_message"] == "还是没打过"
    assert data["game_state_summary"]["current_activity"] == "boss_failed"
    assert data["game_state_summary"]["current_boss"]["name"] == "恶兆妖鬼 Margit"
    assert data["game_state_summary"]["last_cleared_boss"] != "恶兆妖鬼 Margit"
    assert "current user message contains negated clear phrase" in data["warnings"]


def test_semantic_extraction_debug_endpoint_returns_latest_without_secrets():
    client.post("/api/chat", json={"message": "我喜欢简短的游戏攻略", "session_id": "api-semantic-debug"})

    response = client.get("/api/debug/semantic-extraction/latest")

    assert response.status_code == 200
    data = response.json()
    assert {
        "latest_user_message",
        "rule_result",
        "rule_confidence",
        "raw_rule_confidence",
        "ambiguity_detected",
        "llm_called",
        "semantic_extraction_model",
        "semantic_extraction_latency_ms",
        "provider_latency_ms",
        "llm_result",
            "final_decision",
            "fallback_reason",
            "source",
            "confidence",
            "applied_updates",
            "extraction_trace",
            "skip_reason",
            "why_pending_created",
            "latency_ms",
            "parse_error",
            "llm_shadow",
            "llm_shadow_status",
            "llm_shadow_confidence",
            "llm_shadow_summary",
            "llm_shadow_diff",
        } <= data.keys()
    assert data["latest_user_message"].startswith("游戏状态表达 /")
    assert "我喜欢简短的游戏攻略" not in data["latest_user_message"]
    assert data["source"] == "rule"
    assert data["confidence"] == "high"
    assert "memory_candidate_created" in data["applied_updates"]
    assert data["llm_called"] is False
    assert data["final_decision"]["memory_candidate"]["should_create_pending"] is True
    serialized = json.dumps(data, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "deepseek_api_key" not in serialized
    assert "authorization" not in serialized
    assert "bearer" not in serialized
    assert "sk-" not in serialized


def test_chat_accepts_voice_direct_input_source_in_semantic_debug():
    client.post(
        "/api/chat",
        json={"message": "我换去打玛尔基特了", "session_id": "api-voice-direct-source", "input_source": "voice_direct"},
    )

    response = client.get("/api/debug/semantic-extraction/latest")

    assert response.status_code == 200
    data = response.json()
    assert data["input_source"] == "voice_direct"
    assert {"llm_primary_status", "llm_provider_status", "llm_schema_valid", "rule_grounding"} <= data.keys()


def test_semantic_shadow_events_endpoint_returns_final_events_without_secrets(monkeypatch):
    monkeypatch.setattr(sem.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(sem.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(
        sem,
        "_call_deepseek_flash",
        lambda *args, **kwargs: json.dumps(
            {
                "is_game_related": True,
                "confidence": "medium",
                "game": {"operation": "unknown", "value": "unknown", "confidence": "low"},
                "boss": {"operation": "set", "value": "tree_sentinel", "surface_label": None, "confidence": "medium"},
                "death_count": {"operation": "increment", "value": 1, "confidence": "medium"},
                "frustration": {"operation": "none", "confidence": "low"},
                "boss_cleared": {"operation": "none", "confidence": "low"},
                "memory_candidate": {"should_create": False, "kind": "none", "safe_summary": None, "confidence": "low"},
                "proactive_signal": {"type": "none", "confidence": "low", "reason": ""},
                "reasoning_summary": "安全候选",
            },
            ensure_ascii=False,
        ),
    )
    since_id = client.get("/api/debug/semantic-shadow/events").json()["latest_id"]
    deferred = sem.extract_semantics(
        "我在那个骑马金甲大哥那里又寄了几次。",
        "casual_chat",
        {"current_game": "Elden Ring"},
        run_llm_shadow=False,
    )
    trace_id = sem.schedule_semantic_shadow_event(deferred)
    sem.run_semantic_shadow_background(
        "我在那个骑马金甲大哥那里又寄了几次。",
        "casual_chat",
        {"current_game": "Elden Ring"},
        trace_id=trace_id,
    )

    response = client.get(f"/api/debug/semantic-shadow/events?since_id={since_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["latest_id"] >= since_id + 2
    statuses = [event["status"] for event in data["events"]]
    assert "shadow_deferred" in statuses
    assert "shadow_succeeded" in statuses
    final = [event for event in data["events"] if event["status"] == "shadow_succeeded"][-1]
    assert final["applied_updates"] == []
    assert "final_decision" not in final
    assert "memory_candidate" not in final
    assert "proactive_signal" not in final
    serialized = json.dumps(data, ensure_ascii=False).lower()
    assert "骑马金甲大哥" not in serialized
    assert "api_key" not in serialized
    assert "authorization" not in serialized
    assert ".env" not in serialized
    assert "raw prompt" not in serialized


def test_memory_reset_route():
    client.post("/api/chat", json={"message": "我不喜欢长篇攻略", "session_id": "api-memory-reset"})
    assert client.get("/api/memory/pending").json()
    response = client.post("/api/memory/reset")

    assert response.status_code == 200
    assert response.json() == {"status": "reset"}
    assert client.get("/api/memory/profile").json()["current_boss"] is None
    assert client.get("/api/memory/episodes").json() == []
    assert client.get("/api/memory/pending").json() == []
