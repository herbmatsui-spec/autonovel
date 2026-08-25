from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple, Union, overload, cast

from src.core.llm.providers import LLMProviderFactory, LLMResponse
from src.core.llm.router import resolve_model, select_model
from src.core.observability import StructuredLogger
from src.models import GenerateResult
from src.models.base import LLMRequestOptions

logger = StructuredLogger(__name__)


class SemanticCacheManager:
    """意味的キャッシュマネージャ"""

    def __init__(self, vector_store: object = None):
        self.vector_store = vector_store

    def get(self, key: str) -> Optional[object]:
        try:
            if self.vector_store and hasattr(self.vector_store, "get"):
                return self.vector_store.get(key)
            return None
        except (AttributeError, TypeError, RuntimeError) as e:
            logger.warning(f"Cache get failed for key={key}: {e}")
            return None

    def set(self, key: str, value: object, ttl: int = 3600) -> None:
        try:
            if self.vector_store and hasattr(self.vector_store, "set"):
                self.vector_store.set(key, value, ttl)
        except (AttributeError, TypeError, RuntimeError) as e:
            logger.warning(f"Cache set failed for key={key}: {e}")


def create_genai_client(api_key: str):
    """Gemini API クライアントを作成する"""
    from google.genai import Client

    return Client(api_key=api_key)


class LLMGenerateResultProxy:
    """LLM生成結果のプロキシ"""

    def __init__(self, llm_factory: Optional[LLMProviderFactory] = None, *, factory: Optional[LLMProviderFactory] = None):
        self.llm_factory = llm_factory or factory

    @staticmethod
    def _usage_metric(usage: object, key: str, default: int = 0) -> int:
        """Extract a metric from usage object (dict or object with attributes)."""
        if usage is None:
            return default
        if isinstance(usage, dict):
            return cast(int, usage.get(key, default))
        return getattr(usage, key, default)

    @overload
    async def generate_json(
        self,
        purpose_or_request: LLMRequestOptions,
        prompt: str = "",
        response_schema: Any = None,
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        model_name: Optional[str] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs: Dict[str, object],
    ) -> GenerateResult: ...

    @overload
    async def generate_json(
        self,
        purpose_or_request: str = "writing",
        prompt: str = "",
        response_schema: Any = None,
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        model_name: Optional[str] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs: Dict[str, object],
    ) -> GenerateResult: ...

    async def generate_json(
        self,
        purpose_or_request: Union[str, LLMRequestOptions] = "writing",
        prompt: str = "",
        response_schema: Any = None,
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        model_name: Optional[str] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs: Any,
    ) -> GenerateResult:
        if self.llm_factory is None:
            raise ValueError("llm_factory is not set")

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

        provider = self.llm_factory.get_provider(model)
        response: LLMResponse = await provider.generate_json(
            model_name=model,
            prompt=prompt,
            response_schema=response_schema,
            system_instruction=system_instruction,
            temperature=temp,
            stream_callback=stream_callback,
        )

        return GenerateResult(
            success=response.success,
            metadata=response.metadata,
            story_content=response.content,
            token_usage={
                "prompt": self._usage_metric(response.usage, "prompt_tokens", 0),
                "completion": self._usage_metric(response.usage, "completion_tokens", 0),
                "calls": 1,
            },
        )

    @overload
    async def generate_text(
        self,
        purpose_or_request: LLMRequestOptions,
        prompt: str = "",
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        model_name: Optional[str] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs: Dict[str, object],
    ) -> GenerateResult: ...

    @overload
    async def generate_text(
        self,
        purpose_or_request: str = "writing",
        prompt: str = "",
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        model_name: Optional[str] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs: Dict[str, object],
    ) -> GenerateResult: ...

    async def generate_text(
        self,
        purpose_or_request: Union[str, LLMRequestOptions] = "writing",
        prompt: str = "",
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        model_name: Optional[str] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs: Dict[str, object],
    ) -> GenerateResult:
        if self.llm_factory is None:
            raise ValueError("llm_factory is not set")

        if isinstance(purpose_or_request, LLMRequestOptions):
            req = purpose_or_request
            model = req.model_name
            prompt = req.prompt
            system_instruction = req.system_instruction
            temp = req.temp
            stream_callback = req.stream_callback
        else:
            model = model_name or select_model(purpose_or_request)

        provider = self.llm_factory.get_provider(model)
        response: LLMResponse = await provider.generate_text(
            model_name=model,
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temp,
            stream_callback=stream_callback,
        )

        return GenerateResult(
            success=response.success,
            metadata=response.metadata,
            story_content=response.content,
            token_usage={
                "prompt": self._usage_metric(response.usage, "prompt_tokens", 0),
                "completion": self._usage_metric(response.usage, "completion_tokens", 0),
                "calls": 1,
            },
        )


LLMGateway = LLMGenerateResultProxy