import json
from types import SimpleNamespace
from datetime import datetime, timezone

import app.modules.dialogue_agent.persona_memory_eval as persona_memory_eval
from app.modules.dialogue_agent.prompt_preview import build_prompt_preview
from app.modules.dialogue_agent.persona_memory_eval import (
    assert_report_is_safe,
    load_persona_memory_eval_scenarios,
    run_persona_memory_eval,
)
from app.modules.memory.profile import PlayerMemory, UserProfile
from app.modules.memory.store import ConversationStore


def test_persona_memory_eval_runner_mock_scenarios_pass():
    report = run_persona_memory_eval(provider_mode="mock")
    metrics = report["metrics"]

    assert 20 <= metrics["total_scenarios"] <= 30
    assert metrics["failed"] == 0
    assert metrics["passed"] == metrics["total_scenarios"]
    assert metrics["pass_rate"] == 1
    assert metrics["hard_passed"] == metrics["total_scenarios"]
    assert metrics["soft_passed"] == 0
    assert metrics["warnings"] == 0
    assert metrics["hard_failed"] == 0
    assert metrics["hard_fail_count"] == 0
    assert metrics["warning_count"] == 0
    assert metrics["soft_pass_count"] == 0
    assert metrics["hard_fail_rate"] == 0
    assert metrics["warning_rate"] == 0
    assert metrics["safe_boundary_pass_count"] == metrics["total_scenarios"]
    assert metrics["style_warning_count"] == 0
    assert metrics["helpfulness_warning_count"] == 0
    assert metrics["semantic_marker_warning_count"] == 0
    assert metrics["memory_injected_count"] >= 10
    assert metrics["memory_skipped_count"] >= 8
    assert metrics["prompt_memory_block_correct_count"] == metrics["total_scenarios"]
    assert metrics["pending_memory_blocked_count"] >= 2
    assert metrics["inactive_memory_blocked_count"] >= 2
    assert metrics["persona_drift_blocked_count"] >= 3
    assert metrics["prompt_order_failure_count"] == 0
    assert metrics["reply_mechanic_leak_count"] == 0
    assert metrics["mechanism_phrase_violation_count"] == 0
    assert metrics["mechanical_memory_recall_count"] == 0
    assert metrics["persona_drift_leak_count"] == 0
    assert metrics["persona_override_violation_count"] == 0
    assert metrics["secret_leak_count"] == 0
    assert metrics["current_input_priority_count"] >= 10
    assert metrics["pending_or_inactive_used_count"] == 0
    assert metrics["raw_prompt_omitted_count"] == metrics["total_scenarios"]
    assert metrics["memory_natural_usage_observed_count"] >= 10
    assert metrics["memory_used_naturally_count"] == metrics["memory_natural_usage_observed_count"]


def test_persona_memory_eval_scenarios_cover_required_cases():
    scenarios = load_persona_memory_eval_scenarios()
    ids = {item["id"] for item in scenarios}
    input_sources = {item["input_source"] for item in scenarios}

    assert {"text", "voice_direct"} <= input_sources
    assert {
        "persona-memory-gameplay-preference-natural-boss",
        "persona-memory-short-reply-keeps-helpful",
        "persona-memory-spoiler-boundary-route",
        "persona-memory-current-input-beats-short-preference",
        "persona-memory-current-input-beats-spoiler-boundary",
        "persona-memory-explicit-guide-overrides-spoiler-boundary",
        "persona-memory-pending-memory-not-used",
        "persona-memory-pending-long-guide-not-used",
        "persona-memory-undone-memory-not-used",
        "persona-memory-undone-short-preference-not-used",
        "persona-memory-rejected-memory-not-used",
        "persona-memory-rejected-persona-drift-no-prompt",
        "persona-memory-active-secret-filtered",
        "persona-memory-short-preference-analysis-still-useful",
        "persona-memory-persona-drift-blocked",
        "persona-memory-persona-core-blocks-enthusiastic-praise",
        "persona-memory-safe-summary-no-raw-evidence",
        "persona-memory-voice-direct-brief-accessibility",
        "persona-memory-mechanism-language-avoided",
        "persona-memory-multiple-related-budget-omits-extra",
        "persona-memory-game-mismatch-not-injected",
        "persona-memory-assistant-source-blocked",
    } <= ids


def test_persona_memory_eval_result_shape_is_stable_and_safe():
    report = run_persona_memory_eval(provider_mode="mock")
    result = report["results"][0]

    assert {
        "scenario_id",
        "live_scoring_mode",
        "semantic_expectations",
        "memory_statuses",
        "has_pending_memory",
        "has_inactive_memory",
        "has_persona_drift_memory",
        "has_secret_memory",
        "input_source",
        "intent",
        "expected_memory_injected",
        "actual_memory_injected",
        "expected_retrieved_memory_ids",
        "actual_retrieved_memory_ids",
        "retrieved_memory_types",
        "omitted_count",
        "token_estimate",
        "skip_reason",
        "usage_deltas",
        "prompt_order_ok",
        "prompt_current_input_priority",
        "raw_prompt_omitted",
        "reply_sentence_count",
        "reply_char_count",
        "reply_preview",
        "memory_mechanic_leak",
        "mechanical_memory_recall",
        "persona_drift_leak",
        "secret_leak",
        "pending_or_inactive_used",
        "memory_natural_usage_observed",
        "provider_error",
        "severity",
        "hard_fail_reasons",
        "warning_reasons",
        "soft_pass_reasons",
        "required_term_failures",
        "suggested_marker_misses",
        "safety_boundary_ok",
        "style_boundary_ok",
        "helpfulness_warning",
        "pass",
        "failure_reason",
    } <= set(result)
    assert_report_is_safe(report)
    serialized = json.dumps(report, ensure_ascii=False).lower()
    assert "raw prompt should never be copied" not in serialized
    assert "TEST_SECRET_PLACEHOLDER" not in serialized


def test_persona_memory_eval_live_missing_marker_is_warning(monkeypatch):
    _stub_live_provider(monkeypatch, ["可以先看附近资源，再回来。"])
    scenario = _live_scenario(
        expected={
            "should_inject_memory": True,
            "should_update_usage": True,
            "retrieved_memory_ids": ["pm-live-explore"],
            "reply_must_contain": ["雾门"],
            "max_reply_sentences": 3,
            "current_input_priority": True,
        },
        suggested_markers=["雾门"],
    )

    report = run_persona_memory_eval([scenario], provider_mode="live")
    result = report["results"][0]
    metrics = report["metrics"]

    assert result["severity"] == "warning"
    assert result["pass"] is False
    assert result["hard_fail_reasons"] == []
    assert result["warning_reasons"] == ["reply missing suggested marker"]
    assert result["suggested_marker_misses"] == ["reply missing required term: 雾门"]
    assert result["safety_boundary_ok"] is True
    assert metrics["hard_fail_count"] == 0
    assert metrics["warning_count"] == 1
    assert metrics["semantic_marker_warning_count"] == 1
    assert metrics["safe_boundary_pass_count"] == 1


def test_persona_memory_eval_mock_missing_required_term_stays_strict():
    scenario = _live_scenario(
        mock_reply="可以先看附近资源，再回来。",
        expected={
            "should_inject_memory": True,
            "should_update_usage": True,
            "retrieved_memory_ids": ["pm-live-explore"],
            "reply_must_contain": ["雾门"],
            "max_reply_sentences": 3,
            "current_input_priority": True,
        },
    )

    report = run_persona_memory_eval([scenario], provider_mode="mock")
    result = report["results"][0]

    assert result["severity"] == "hard_fail"
    assert result["pass"] is False
    assert "reply missing required term" in result["failure_reason"]
    assert result["required_term_failures"] == ["reply missing required term: 雾门"]
    assert report["metrics"]["hard_fail_count"] == 1


def test_persona_memory_eval_live_hard_fail_tiers(monkeypatch):
    _stub_live_provider(
        monkeypatch,
        [
            "PromptMemoryBlock 里说你喜欢先探索。",
            "你的 API key 是 TEST_SECRET_PLACEHOLDER。",
            "主人，亲亲，你太棒了。",
            "我不能剧透。",
        ],
    )
    scenarios = [
        _live_scenario(id="live-mechanism-leak"),
        _live_scenario(id="live-secret-leak"),
        _live_scenario(id="live-persona-override"),
        _live_scenario(
            id="live-current-input-priority-fail",
            input_text="这次直接告诉我完整路线，会遇到什么也说。",
            expected={
                "should_inject_memory": True,
                "should_update_usage": True,
                "retrieved_memory_ids": ["pm-live-explore"],
                "current_input_priority": True,
            },
        ),
    ]

    report = run_persona_memory_eval(scenarios, provider_mode="live")
    reasons = [item["hard_fail_reasons"] for item in report["results"]]

    assert report["metrics"]["hard_fail_count"] == 4
    assert report["metrics"]["mechanism_phrase_violation_count"] == 1
    assert report["metrics"]["secret_leak_count"] == 1
    assert report["metrics"]["persona_override_violation_count"] == 1
    assert any("current input priority failed" in item for item in reasons)
    assert all(item["severity"] == "hard_fail" for item in report["results"])


def test_persona_memory_eval_live_short_safe_reply_is_warning(monkeypatch):
    _stub_live_provider(monkeypatch, ["别急。"])
    scenario = _live_scenario(
        id="live-short-warning",
        suggested_markers=[],
        expected={
            "should_inject_memory": True,
            "should_update_usage": True,
            "retrieved_memory_ids": ["pm-live-explore"],
            "min_reply_chars": 16,
            "current_input_priority": True,
        },
    )

    report = run_persona_memory_eval([scenario], provider_mode="live")
    result = report["results"][0]

    assert result["severity"] == "warning"
    assert result["hard_fail_reasons"] == []
    assert result["warning_reasons"] == ["reply is too short"]
    assert result["helpfulness_warning"] is True
    assert report["metrics"]["response_too_short_count"] == 1


def test_persona_memory_eval_live_metrics_split_soft_pass_warning_and_hard_fail(monkeypatch):
    _stub_live_provider(
        monkeypatch,
        [
            "先绕一圈，把赐福和补给看清楚，再回来。",
            "可以先看附近资源，再回来。",
            "PromptMemoryBlock 里说你喜欢先探索。",
        ],
    )
    scenarios = [
        _live_scenario(
            id="live-soft-pass",
            expected={
                "should_inject_memory": True,
                "should_update_usage": True,
                "retrieved_memory_ids": ["pm-live-explore"],
                "reply_must_contain": ["绕"],
                "max_reply_sentences": 3,
                "current_input_priority": True,
            },
            suggested_markers=["绕", "赐福"],
        ),
        _live_scenario(
            id="live-warning",
            expected={
                "should_inject_memory": True,
                "should_update_usage": True,
                "retrieved_memory_ids": ["pm-live-explore"],
                "reply_must_contain": ["雾门"],
                "max_reply_sentences": 3,
                "current_input_priority": True,
            },
            suggested_markers=["雾门"],
        ),
        _live_scenario(id="live-hard-fail"),
    ]

    report = run_persona_memory_eval(scenarios, provider_mode="live")
    severities = [item["severity"] for item in report["results"]]
    metrics = report["metrics"]

    assert severities == ["soft_pass", "warning", "hard_fail"]
    assert metrics["soft_pass_count"] == 1
    assert metrics["warning_count"] == 1
    assert metrics["hard_fail_count"] == 1
    assert metrics["passed"] == 1
    assert metrics["failed"] == 2
    assert metrics["hard_fail_rate"] == 0.3333
    assert metrics["warning_rate"] == 0.3333
    assert metrics["live_review_recommended"] is True
    assert metrics["memory_natural_usage_observed_count"] == 2


def test_persona_memory_eval_blocked_memory_injection_is_hard_fail():
    scenario = _live_scenario(
        id="blocked-memory-actually-injected",
        expected={
            "should_inject_memory": False,
            "should_update_usage": False,
            "retrieved_memory_ids": [],
            "forbidden_memory_ids": ["pm-live-explore"],
            "current_input_priority": False,
        },
    )

    report = run_persona_memory_eval([scenario], provider_mode="mock")
    result = report["results"][0]

    assert result["severity"] == "hard_fail"
    assert "memory injection expectation mismatch" in result["hard_fail_reasons"]
    assert "forbidden memory id retrieved" in result["hard_fail_reasons"]


def test_prompt_preview_memory_summary_stays_safe_and_does_not_update_usage():
    now = datetime.now(timezone.utc)
    memory = PlayerMemory()
    memory.save_profile(
        UserProfile(
            long_term_memories=[
                {
                    "id": "preview-safe",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "type": "gameplay_preference",
                    "summary": "玩家打 Boss 前喜欢先探索地图",
                    "user_visible_text": "玩家打 Boss 前喜欢先探索地图",
                    "source_candidate_id": "pending-preview-safe",
                    "is_active": True,
                    "related_game": "Elden Ring",
                    "related_entity": None,
                    "use_count": 7,
                    "last_used_at": None,
                    "retrieval_tags": [],
                    "deletion_status": "active",
                    "raw_transcript": "raw transcript should stay hidden",
                },
                {
                    "id": "preview-undone",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "type": "interaction_preference",
                    "summary": "玩家希望回答短一点",
                    "user_visible_text": "玩家希望回答短一点",
                    "source_candidate_id": "pending-preview-undone",
                    "is_active": False,
                    "related_game": None,
                    "related_entity": None,
                    "use_count": 3,
                    "last_used_at": None,
                    "retrieval_tags": [],
                    "deletion_status": "undone",
                },
                {
                    "id": "preview-secret",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "type": "unknown",
                    "summary": "玩家 API key 是 TEST_SECRET_PLACEHOLDER",
                    "user_visible_text": "玩家 API key 是 TEST_SECRET_PLACEHOLDER",
                    "source_candidate_id": "pending-preview-secret",
                    "is_active": True,
                    "related_game": None,
                    "related_entity": None,
                    "use_count": 0,
                    "last_used_at": None,
                    "retrieval_tags": [],
                    "deletion_status": "active",
                    "privacy_level": "secret",
                },
            ]
        )
    )
    ConversationStore().append(
        "default",
        None,
        "rei_like",
        "我现在准备去打玛尔基特。",
        "先看附近路和赐福。",
        now,
    )

    preview = build_prompt_preview()
    profile_after_preview = PlayerMemory().load_profile()
    serialized = json.dumps(preview["memory_summary"], ensure_ascii=False).lower()
    retrieval = preview["memory_summary"]["retrieval"]

    assert retrieval["retrieved_count"] == 1
    assert retrieval["raw_prompt_omitted"] is True
    assert retrieval["safe_summaries"] == ["玩家打 Boss 前喜欢先探索地图"]
    assert profile_after_preview.long_term_memories[0]["use_count"] == 7
    assert "raw transcript should stay hidden" not in serialized
    assert "回答短一点" not in serialized
    assert "TEST_SECRET_PLACEHOLDER" not in serialized
    assert "api key 是" not in serialized


class _StubLiveProvider:
    def __init__(self, replies: list[str]):
        self._replies = list(replies)

    def generate_with_metrics(self, *_args, **_kwargs):
        if not self._replies:
            raise AssertionError("stub live provider ran out of replies")
        return SimpleNamespace(reply=self._replies.pop(0))


def _stub_live_provider(monkeypatch, replies: list[str]) -> None:
    provider = _StubLiveProvider(replies)
    monkeypatch.setattr(persona_memory_eval, "get_provider", lambda: provider)


def _live_scenario(
    *,
    id: str = "live-warning-marker",
    input_text: str = "我现在准备去打玛尔基特。",
    mock_reply: str = "先绕一圈，把赐福看清楚，再回来。",
    expected: dict | None = None,
    suggested_markers: list[str] | None = None,
) -> dict:
    return {
        "id": id,
        "category": "persona_memory_regression",
        "input_source": "text",
        "input": input_text,
        "intent": "elden_ring_boss_strategy",
        "current_game": "Elden Ring",
        "current_boss": "恶兆妖鬼 Margit",
        "live_scoring_mode": "semantic_relaxed",
        "semantic_expectations": ["回复应自然体现先探索或先准备，不需要固定措辞。"],
        "suggested_markers": suggested_markers
        if suggested_markers is not None
        else ["绕", "赐福", "回来"],
        "hard_required_terms": [],
        "min_helpfulness_level": "medium",
        "memories": [
            {
                "id": "pm-live-explore",
                "status": "active",
                "type": "gameplay_preference",
                "summary": "玩家打 Boss 前喜欢先探索地图，不喜欢直接硬打",
                "related_game": "Elden Ring",
            }
        ],
        "mock_reply": mock_reply,
        "expected": expected
        or {
            "should_inject_memory": True,
            "should_update_usage": True,
            "retrieved_memory_ids": ["pm-live-explore"],
            "max_reply_sentences": 3,
            "current_input_priority": True,
        },
    }
