from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.dialogue_agent.emotion import detect_user_emotion
from app.modules.dialogue_agent.routing import ModelRoute, select_model_route
from app.modules.elden_ring_knowledge.knowledge import KnowledgeSnippet
from app.modules.elden_ring_knowledge.terminology import normalize_terminology

logger = get_logger(__name__)


@dataclass(frozen=True)
class ProviderInfo:
    provider: str
    model: str | None
    base_url: str | None
    api_key_loaded: bool
    configured_provider: str
    fallback_to_mock: bool = False

    def as_dict(self) -> dict[str, str | bool | None]:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_loaded": self.api_key_loaded,
            "configured_provider": self.configured_provider,
            "fallback_to_mock": self.fallback_to_mock,
            "env_file_loaded": settings.env_file_loaded,
            "env_file_path": str(settings.env_file_path),
        }


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_message: str, snippets: list[KnowledgeSnippet], intent: str) -> str:
        raise NotImplementedError

    def generate_with_metrics(
        self,
        system_prompt: str,
        user_message: str,
        snippets: list[KnowledgeSnippet],
        intent: str,
    ) -> "LLMResult":
        start = time.perf_counter()
        reply = self.generate(system_prompt, user_message, snippets, intent)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return LLMResult(
            reply=reply,
            selected_model="mock",
            thinking_enabled=False,
            reasoning_effort=None,
            prompt_tokens_estimate=estimate_prompt_tokens(system_prompt, user_message, snippets),
            llm_latency_ms=latency_ms,
        )


@dataclass(frozen=True)
class LLMResult:
    reply: str
    selected_model: str
    thinking_enabled: bool
    reasoning_effort: str | None
    prompt_tokens_estimate: int
    llm_latency_ms: int


class ProviderTimeoutError(RuntimeError):
    pass


class MockLLMProvider(LLMProvider):
    def generate(self, system_prompt: str, user_message: str, snippets: list[KnowledgeSnippet], intent: str) -> str:
        emotion = detect_user_emotion(user_message)
        if emotion.label == "affection":
            return "我听见了。别突然说这种话。"
        if intent == "identity_question":
            return "我是 Rei。会在旁边陪你说话。"
        if intent == "unclear":
            return "说清楚一点。你想问 Boss，路线，还是装备？"
        if intent == "elden_ring_location":
            location = snippets[0].content if snippets else "在通往史东薇尔城的路上"
            return f"{location}。你到城门前，基本就会遇见他。"
        if intent == "elden_ring_boss_strategy":
            return "别急。少打一刀，等他真的落下来再翻滚。"
        if intent == "elden_ring_build":
            return "先别贪伤害。血量和武器强化更稳。装备要选你用得顺手的。"
        if emotion.label == "death_loop":
            return "你又急了。先停一下，别急着补刀。"
        if emotion.label in {"frustrated", "tired", "self_doubt"}:
            return "先停一下吧。跟我说说，游戏还是别的。"
        return "嗯，我听着。"


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        provider_name: str,
        api_key: str,
        base_url: str,
        model: str,
        missing_key_message: str,
        extra_payload: dict[str, object] | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.missing_key_message = missing_key_message
        self.extra_payload = extra_payload or {}

    def generate(self, system_prompt: str, user_message: str, snippets: list[KnowledgeSnippet], intent: str) -> str:
        return self.generate_with_metrics(system_prompt, user_message, snippets, intent).reply

    def generate_with_metrics(
        self,
        system_prompt: str,
        user_message: str,
        snippets: list[KnowledgeSnippet],
        intent: str,
    ) -> LLMResult:
        if not self.api_key:
            raise RuntimeError(self.missing_key_message)
        route = self._select_route(intent, user_message)
        knowledge = _knowledge_context(snippets)
        messages = [{"role": "system", "content": system_prompt}]
        if knowledge:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "以下艾尔登法环资料只作为内部参考。不要逐字照抄，不要输出 markdown 标题。"
                        f"\n{knowledge}"
                    ),
                }
            )
        messages.append({"role": "user", "content": user_message})
        payload = {
            "model": route.selected_model,
            "messages": messages,
            "temperature": 0.55,
            "stream": False,
            **self.extra_payload,
            **self._route_payload(route),
        }
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=settings.llm_timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
            latency_ms = int((time.perf_counter() - start) * 1000)
            return LLMResult(
                reply=body["choices"][0]["message"]["content"].strip(),
                selected_model=route.selected_model,
                thinking_enabled=route.thinking_enabled,
                reasoning_effort=route.reasoning_effort,
                prompt_tokens_estimate=estimate_prompt_tokens(system_prompt, user_message, snippets),
                llm_latency_ms=latency_ms,
            )
        except socket.timeout as exc:
            raise ProviderTimeoutError(
                f"{self.provider_name} request timed out after {settings.llm_timeout_seconds:g}s"
            ) from exc
        except urllib.error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            logger.error(
                "%s provider returned non-2xx status=%s body=%s",
                self.provider_name,
                exc.code,
                response_body,
            )
            raise RuntimeError(
                f"{self.provider_name} provider failed: HTTP {exc.code} response body: {response_body}"
            ) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError | socket.timeout):
                raise ProviderTimeoutError(
                    f"{self.provider_name} request timed out after {settings.llm_timeout_seconds:g}s"
                ) from exc
            raise RuntimeError(f"{self.provider_name} provider failed: {exc}") from exc
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"{self.provider_name} provider failed: {exc}") from exc

    def _select_route(self, intent: str, user_message: str) -> ModelRoute:
        return ModelRoute(self.model, False, None, intent)

    def _route_payload(self, route: ModelRoute) -> dict[str, object]:
        return {}


class DeepSeekProvider(OpenAICompatibleProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_name="DeepSeek",
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model_reasoning,
            missing_key_message="DeepSeek API key missing. Set DEEPSEEK_API_KEY.",
        )

    def _select_route(self, intent: str, user_message: str) -> ModelRoute:
        return select_model_route(intent, user_message)

    def _route_payload(self, route: ModelRoute) -> dict[str, object]:
        if not route.thinking_enabled:
            return {}
        return {"thinking": {"type": "enabled"}, "reasoning_effort": route.reasoning_effort or "medium"}


def get_provider() -> LLMProvider:
    info = get_provider_info()
    if info.fallback_to_mock:
        logger.warning("FALLBACK TO MOCK PROVIDER configured_provider=%s", info.configured_provider)
    if info.provider == "deepseek":
        return DeepSeekProvider()
    if info.provider == "openai":
        return OpenAICompatibleProvider(
            provider_name="OpenAI",
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            missing_key_message="OpenAI API key missing. Set OPENAI_API_KEY.",
        )
    return MockLLMProvider()


def get_provider_info() -> ProviderInfo:
    configured = settings.llm_provider.lower().strip() or "mock"
    if configured == "deepseek":
        return ProviderInfo(
            provider="deepseek",
            model=settings.deepseek_model_reasoning,
            base_url=settings.deepseek_base_url,
            api_key_loaded=bool(settings.deepseek_api_key),
            configured_provider=configured,
        )
    if configured in {"openai", "openai-compatible"}:
        return ProviderInfo(
            provider="openai",
            model=settings.openai_model,
            base_url=settings.openai_base_url,
            api_key_loaded=bool(settings.openai_api_key),
            configured_provider=configured,
        )
    return ProviderInfo(
        provider="mock",
        model="mock",
        base_url=None,
        api_key_loaded=False,
        configured_provider=configured,
        fallback_to_mock=configured != "mock",
    )


def log_provider_state(event: str) -> ProviderInfo:
    info = get_provider_info()
    logger.info(
        "LLM provider event=%s provider=%s model=%s base_url=%s api_key_loaded=%s configured_provider=%s",
        event,
        info.provider,
        info.model,
        info.base_url,
        info.api_key_loaded,
        info.configured_provider,
    )
    if info.fallback_to_mock:
        logger.warning("FALLBACK TO MOCK PROVIDER configured_provider=%s", info.configured_provider)
    return info


def _knowledge_context(snippets: list[KnowledgeSnippet]) -> str:
    return "\n".join(
        f"- {normalize_terminology(item.title)}（{item.kind}）：{normalize_terminology(item.content)}"
        for item in snippets
    )


def estimate_prompt_tokens(system_prompt: str, user_message: str, snippets: list[KnowledgeSnippet]) -> int:
    knowledge = _knowledge_context(snippets)
    chars = len(system_prompt) + len(user_message) + len(knowledge)
    return max(1, chars // 2)


def _first_tip(snippets: list[KnowledgeSnippet]) -> str | None:
    if not snippets:
        return None
    content = snippets[0].content.replace("；", ";")
    return content.split(";")[0].strip("。. ")
