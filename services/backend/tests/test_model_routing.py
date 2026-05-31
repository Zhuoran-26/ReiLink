import json
import urllib.error

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.dialogue_agent.providers import DeepSeekProvider
from app.modules.dialogue_agent.routing import select_model_route


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps({"choices": [{"message": {"content": "好的"}}]}).encode("utf-8")


def test_model_preference_fast_forces_fast_model(monkeypatch):
    monkeypatch.setattr(settings, "model_preference", "fast")

    route = select_model_route("elden_ring_boss_strategy", "详细讲 Margit 怎么打")

    assert route.selected_model == "deepseek-v4-flash"
    assert route.model_route_mode == "fast"
    assert route.route_reason == "preference_fast"
    assert route.thinking_enabled is False


def test_model_preference_fast_main_reply_uses_fast_model(monkeypatch):
    captured_models = []

    def fake_urlopen(request, timeout):
        del timeout
        captured_models.append(json.loads(request.data.decode("utf-8"))["model"])
        return _FakeResponse()

    monkeypatch.setattr(settings, "model_preference", "fast")
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr("app.modules.dialogue_agent.providers.urllib.request.urlopen", fake_urlopen)

    result = DeepSeekProvider().generate_with_metrics("中文短句", "详细讲 Margit 怎么打", [], "elden_ring_boss_strategy")

    assert captured_models == ["deepseek-v4-flash"]
    assert result.selected_model == "deepseek-v4-flash"


def test_model_preference_pro_forces_pro_model(monkeypatch):
    monkeypatch.setattr(settings, "model_preference", "pro")

    route = select_model_route("casual_chat", "你好")

    assert route.selected_model == "deepseek-v4-pro"
    assert route.model_route_mode == "pro"
    assert route.route_reason == "preference_pro"
    assert route.thinking_enabled is True


def test_model_preference_pro_main_reply_uses_pro_model(monkeypatch):
    captured_models = []

    def fake_urlopen(request, timeout):
        del timeout
        captured_models.append(json.loads(request.data.decode("utf-8"))["model"])
        return _FakeResponse()

    monkeypatch.setattr(settings, "model_preference", "pro")
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr("app.modules.dialogue_agent.providers.urllib.request.urlopen", fake_urlopen)

    result = DeepSeekProvider().generate_with_metrics("中文短句", "你好", [], "casual_chat")

    assert captured_models == ["deepseek-v4-pro"]
    assert result.selected_model == "deepseek-v4-pro"


def test_casual_chat_selects_fast_model():
    route = select_model_route("casual_chat", "你好")

    assert route.selected_model == "deepseek-v4-flash"
    assert route.model_route_mode == "auto"
    assert route.route_reason == "casual_or_short_reply"
    assert route.route_intent == "casual_chat"
    assert route.estimated_complexity == "low"
    assert route.thinking_enabled is False
    assert route.reasoning_effort is None


def test_affection_selects_fast_model():
    route = select_model_route("casual_chat", "我喜欢你")

    assert route.selected_model == "deepseek-v4-flash"
    assert route.thinking_enabled is False


def test_emotional_death_loop_selects_fast_model():
    route = select_model_route("casual_chat", "我又死了")

    assert route.selected_model == "deepseek-v4-flash"
    assert route.thinking_enabled is False


def test_detailed_guide_selects_reasoning_model():
    route = select_model_route("elden_ring_boss_strategy", "详细讲 Margit 怎么打")

    assert route.selected_model == "deepseek-v4-pro"
    assert route.model_route_mode == "auto"
    assert route.route_reason == "explicit_detail_request"
    assert route.estimated_complexity == "high"
    assert route.thinking_enabled is True
    assert route.reasoning_effort == "medium"


def test_fast_failure_falls_back_to_pro_and_records_reason(monkeypatch):
    captured_models = []

    def fake_urlopen(request, timeout):
        del timeout
        model = json.loads(request.data.decode("utf-8"))["model"]
        captured_models.append(model)
        if len(captured_models) == 1:
            raise urllib.error.URLError("fast unavailable")
        return _FakeResponse()

    monkeypatch.setattr(settings, "model_preference", "fast")
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr("app.modules.dialogue_agent.providers.urllib.request.urlopen", fake_urlopen)

    result = DeepSeekProvider().generate_with_metrics("中文短句", "你好", [], "casual_chat")

    assert captured_models == ["deepseek-v4-flash", "deepseek-v4-pro"]
    assert result.selected_model == "deepseek-v4-pro"
    assert result.fallback_reason.startswith("fast_model_failed:")


def test_pro_failure_returns_clear_error_without_mock_fallback(monkeypatch):
    captured_models = []

    def fake_urlopen(request, timeout):
        del timeout
        captured_models.append(json.loads(request.data.decode("utf-8"))["model"])
        raise urllib.error.URLError("pro unavailable")

    monkeypatch.setattr(settings, "model_preference", "pro")
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr("app.modules.dialogue_agent.providers.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="DeepSeek provider failed"):
        DeepSeekProvider().generate_with_metrics("中文短句", "你好", [], "casual_chat")

    assert captured_models == ["deepseek-v4-pro"]


def test_settings_panel_model_preference_affects_backend_route():
    client = TestClient(app)

    saved = client.post("/api/settings", json={"model_preference": "pro"})
    assert saved.status_code == 200
    route = select_model_route("casual_chat", "你好")
    assert route.selected_model == "deepseek-v4-pro"

    saved = client.post("/api/settings", json={"model_preference": "fast"})
    assert saved.status_code == 200
    route = select_model_route("elden_ring_boss_strategy", "详细讲 Margit 怎么打")
    assert route.selected_model == "deepseek-v4-flash"
