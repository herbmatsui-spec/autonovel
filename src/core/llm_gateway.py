from __future__ import annotations

from typing import Any, Callable, List, Optional

from src.core.llm_clients import BaseLLMClient, GeminiApiClient, OpenAIApiClient
from src.core.observability import StructuredLogger
from src.models import GenerateResult

logger = StructuredLogger(__name__)


def create_genai_client(api_key: str):
    """Gemini API クライアントを作成する"""
    from google import genai

    return genai.Client(api_key=api_key)


class LLMProviderFactory:
    """LLMプロバイダの抽象化"""

    def __init__(self, genai_client, cooldown):
        self.genai_client = genai_client
        self.cooldown = cooldown

    def get_client(self, provider: str = "gemini") -> BaseLLMClient:
        """モデル名から適切なAPIクライアントを返す。

        OpenRouter 等の OpenAI互換モデルID ("anthropic/claude-3.5-sonnet" 等)
        や、gpt/claude/llama 等のキーワードを含む場合は OpenAI 互換クライアントを返す。
        """
        from src.llm.model_router import is_openai_compatible

        if is_openai_compatible(provider):
            return OpenAIApiClient(cooldown=self.cooldown)

        provider_key = provider.split("-")[0] if "-" in provider else provider
        if provider_key == "gemini":
            return GeminiApiClient(client=self.genai_client, cooldown=self.cooldown)
        # デフォルトは Gemini
        return GeminiApiClient(client=self.genai_client, cooldown=self.cooldown)

    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        providers = []
        if self.genai_client:
            providers.append("gemini")
        try:
            import openai  # noqa: F401

            providers.append("openai")
        except ImportError:
            pass
        return providers


class SemanticCacheManager:
    """意味的キャッシュマネージャ"""

    def __init__(self, vector_store=None):
        self.vector_store = vector_store

    def get(self, key: str):
        try:
            if self.vector_store and hasattr(self.vector_store, "get"):
                return self.vector_store.get(key)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for key={key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        try:
            if self.vector_store and hasattr(self.vector_store, "set"):
                self.vector_store.set(key, value, ttl)
        except Exception as e:
            logger.warning(f"Cache set failed for key={key}: {e}")


class LLMGenerateResultProxy:
    """LLM生成結果のプロキシ"""

    def __init__(self, llm_factory=None, factory=None):
        self.llm_factory = llm_factory or factory

    def get_client(self, model_name: str = "gemini") -> BaseLLMClient:
        return self.llm_factory.get_client(model_name)

    @staticmethod
    def _normalize_response(response: Any) -> Any:
        class _Response:
            def __init__(
                self, success: bool, content: Any = None, metadata: Any = None, usage: Any = None
            ):
                self.success = success
                self.content = content
                self.metadata = metadata
                self.usage = usage

        if isinstance(response, tuple):
            if len(response) == 2:
                content, usage = response
                return _Response(success=True, content=content, usage=usage)
            if len(response) == 3:
                metadata, content, usage = response
                return _Response(success=True, content=content, metadata=metadata, usage=usage)
        return response

    @staticmethod
    def _usage_metric(usage: Any, key: str, default: int = 0) -> int:
        if usage is None:
            return default
        if isinstance(usage, dict):
            return usage.get(key, default)
        return getattr(usage, key, default)

    async def generate_json(
        self,
        purpose_or_request: Any = "writing",
        prompt: str = "",
        response_schema: Any = None,
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        model_name: Optional[str] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs: Any,
    ) -> GenerateResult:
        from src.llm.model_router import resolve_model
        from src.models.base import LLMRequestOptions

        if isinstance(purpose_or_request, LLMRequestOptions):
            req = purpose_or_request
            model = req.model_name
            prompt = req.prompt
            system_instruction = req.system_instruction
            response_schema = req.response_schema
            temp = req.temp
            stream_callback = req.stream_callback
        else:
            model = model_name or resolve_model(purpose_or_request)

        provider = self.get_client(model)
        response = await provider.generate_json(
            model_name=model,
            prompt=prompt,
            response_schema=response_schema,
            system_instruction=system_instruction,
            temp=temp,
            stream_callback=stream_callback,
        )
        response = self._normalize_response(response)
        return GenerateResult(
            success=response.success,
            metadata=response.metadata,
            story_content=response.content,
            token_usage={
                "prompt": LLMGenerateResultProxy._usage_metric(response.usage, "prompt_tokens", 0),
                "completion": LLMGenerateResultProxy._usage_metric(
                    response.usage, "completion_tokens", 0
                ),
                "calls": 1,
            },
        )

    async def generate_text(
        self,
        purpose_or_request: Any = "writing",
        prompt: str = "",
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        model_name: Optional[str] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs: Any,
    ) -> GenerateResult:
        from src.llm.model_router import select_model
        from src.models.base import LLMRequestOptions

        if isinstance(purpose_or_request, LLMRequestOptions):
            req = purpose_or_request
            model = req.model_name
            prompt = req.prompt
            system_instruction = req.system_instruction
            temp = req.temp
            stream_callback = req.stream_callback
        else:
            model = model_name or select_model(purpose_or_request)

        provider = self.get_client(model)
        response = await provider.generate_text(
            model_name=model,
            prompt=prompt,
            system_instruction=system_instruction,
            temp=temp,
            stream_callback=stream_callback,
        )
        response = self._normalize_response(response)
        return GenerateResult(
            success=response.success,
            metadata=getattr(response, "metadata", None) or {},
            story_content=response.content,
            token_usage={
                "prompt": LLMGenerateResultProxy._usage_metric(response.usage, "prompt_tokens", 0),
                "completion": LLMGenerateResultProxy._usage_metric(
                    response.usage, "completion_tokens", 0
                ),
                "calls": 1,
            },
        )

    def generate(self, *args, **kwargs):
        raise NotImplementedError(
            "generate() is deprecated. Use generate_text() or generate_json()."
        )


LLMGateway = LLMGenerateResultProxy
