from typing import Any

from src.backend.engine_utils import AdaptiveCooldown
from src.core.exceptions import (
    LLMAuthenticationError,
    LLMContentFilterError,
    LLMInvalidRequestError,
    LLMRateLimitError,
    LLMServerError,
    LLMTimeoutError,
    LLMUnknownError,
)
from src.core.llm_clients.openai import OpenAIApiClient
from src.core.observability import track_llm_call
from src.llm.base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """
    OpenAI互換API (vLLM, OpenRouter, Together AI等) へのアダプター。
    内部的に OpenAIApiClient を利用して低レベル通信とリトライを管理する。
    """

    def __init__(self, cooldown: AdaptiveCooldown):
        self.internal_client = OpenAIApiClient(cooldown)

    def _map_exception(self, e: Exception) -> Exception:
        """OpenAI SDK 例外および汎用例外をプロジェクトの LLM 例外にマッピングする。"""
        try:
            import openai

            if isinstance(e, openai.RateLimitError):
                return LLMRateLimitError(f"OpenAI API Rate Limit: {e}", original=e)
            if isinstance(e, openai.AuthenticationError):
                return LLMAuthenticationError(f"OpenAI API Auth Error: {e}", original=e)
            if isinstance(e, openai.BadRequestError):
                return LLMInvalidRequestError(f"OpenAI API Invalid Request: {e}", original=e)
            if isinstance(e, openai.APITimeoutError):
                return LLMTimeoutError(f"OpenAI Timeout: {e}", original=e)
            if isinstance(e, openai.InternalServerError):
                return LLMServerError(f"OpenAI Server Error: {e}", original=e)
        except ImportError:
            pass

        err_msg = str(e).lower()
        if "429" in err_msg or "rate limit" in err_msg:
            return LLMRateLimitError(f"OpenAI API Rate Limit: {e}", original=e)
        if "401" in err_msg or "auth" in err_msg:
            return LLMAuthenticationError(f"OpenAI API Auth Error: {e}", original=e)
        if "400" in err_msg or "invalid" in err_msg:
            return LLMInvalidRequestError(f"OpenAI API Invalid Request: {e}", original=e)
        if "filter" in err_msg or "blocked" in err_msg:
            return LLMContentFilterError(f"OpenAI Content Filter: {e}", original=e)
        if "500" in err_msg or "internal" in err_msg:
            return LLMServerError(f"OpenAI Server Error: {e}", original=e)
        if "timeout" in err_msg:
            return LLMTimeoutError(f"OpenAI Timeout: {e}", original=e)

        return LLMUnknownError(f"Unknown OpenAI Error: {e}", original=e)

    @track_llm_call
    async def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        try:
            # OpenAIApiClient.generate_text は Tuple[str, Any] を返す
            content, usage = await self.internal_client.generate_text(
                model_name=model_name,
                prompt=prompt,
                system_instruction=system_instruction,
                temp=temperature,
                **kwargs,
            )
            return LLMResponse(content=content, usage=self._parse_usage(usage), success=True)
        except Exception as e:
            mapped = self._map_exception(e)
            raise mapped from e

    @track_llm_call
    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        response_schema: Any | None = None,
        system_instruction: str | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        try:
            # OpenAIApiClient.generate_json は Tuple[Dict, str, Any] を返す
            metadata, content, usage = await self.internal_client.generate_json(
                model_name=model_name,
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction,
                temp=temperature,
                **kwargs,
            )
            return LLMResponse(
                content=content, metadata=metadata, usage=self._parse_usage(usage), success=True
            )
        except Exception as e:
            mapped = self._map_exception(e)
            raise mapped from e

    def _parse_usage(self, usage_metadata: Any) -> dict[str, int]:
        """OpenAI SDK の usage メタデータを共通形式に変換"""
        if not usage_metadata:
            return {}

        # usage_metadata が MockUsage 等の場合の対応
        return {
            "prompt_tokens": getattr(
                usage_metadata, "prompt_token_count", getattr(usage_metadata, "prompt_tokens", 0)
            ),
            "completion_tokens": getattr(
                usage_metadata,
                "candidates_token_count",
                getattr(usage_metadata, "completion_tokens", 0),
            ),
            "total_tokens": getattr(usage_metadata, "total_token_count", 0),
        }
