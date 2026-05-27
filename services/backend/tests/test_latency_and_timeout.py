import time
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.modules.dialogue_agent.agent import DialogueAgent
from app.modules.dialogue_agent.providers import LLMResult, ProviderTimeoutError
from app.modules.memory.store import ConversationStore
from app.schemas.api import ChatRequest


class _CollectingBackgroundTasks:
    def __init__(self) -> None:
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))


class _SlowMemory:
    def extract_and_update(self, *args, **kwargs):
        time.sleep(0.2)

    def build_prompt_context_with_provenance(self):
        class Context:
            def as_prompt_text(self):
                return ""

        return Context()


class _TimeoutProvider:
    def generate(self, *args, **kwargs):
        raise ProviderTimeoutError("DeepSeek request timed out after 20s")

    def generate_with_metrics(self, *args, **kwargs):
        raise ProviderTimeoutError("DeepSeek request timed out after 20s")


class _FastProvider:
    def generate(self, *args, **kwargs):
        return "我在。"

    def generate_with_metrics(self, *args, **kwargs):
        return LLMResult(
            reply="我在。",
            selected_model="deepseek-v4-flash",
            thinking_enabled=False,
            reasoning_effort=None,
            prompt_tokens_estimate=42,
            llm_latency_ms=3,
        )


def test_memory_update_is_scheduled_without_blocking_chat_response(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.modules.dialogue_agent.agent.get_provider", lambda: _FastProvider())
    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    agent.memory = _SlowMemory()
    background_tasks = _CollectingBackgroundTasks()

    start = time.perf_counter()
    response = agent.chat(ChatRequest(message="你好", session_id="nonblocking"), background_tasks=background_tasks)
    elapsed = time.perf_counter() - start

    assert response.reply
    assert elapsed < 0.1
    assert len(background_tasks.tasks) == 1


def test_timeout_returns_clear_error(monkeypatch):
    monkeypatch.setattr("app.modules.dialogue_agent.agent.get_provider", lambda: _TimeoutProvider())
    client = TestClient(app)

    response = client.post("/api/chat", json={"message": "你好", "session_id": "timeout"})

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"]


def test_latency_log_fields_exist(monkeypatch, caplog, tmp_path: Path):
    monkeypatch.setattr("app.modules.dialogue_agent.agent.get_provider", lambda: _FastProvider())
    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")

    with caplog.at_level("INFO"):
        agent.chat(ChatRequest(message="你好", session_id="latency"))

    assert "chat latency intent=" in caplog.text
    assert "selected_model=" in caplog.text
    assert "thinking_enabled=" in caplog.text
    assert "reasoning_effort=" in caplog.text
    assert "prompt_tokens_estimate=" in caplog.text
    assert "llm_latency_ms=" in caplog.text
    assert "memory_latency_ms=" in caplog.text
    assert "total_latency_ms=" in caplog.text
