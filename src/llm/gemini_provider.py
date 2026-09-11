from typing import Any

from google import genai

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
from src.core.llm_clients.gemini import GeminiApiClient
from src.core.observability import track_llm_call
from src.llm.base import LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    """
    Google Gemini API へのアダプター。
    内部的に GeminiApiClient を利用して低レベル通信とリトライを管理する。
    """

    def __init__(self, client: genai.Client, cooldown: AdaptiveCooldown):
        self.internal_client = GeminiApiClient(client, cooldown)

    def _map_exception(self, e: Exception) -> Exception:
        """Gemini SDK / google-api-core 例外および汎用例外をプロジェクトの LLM 例外にマッピングする。"""
        try:
            from google.api_core import exceptions as g_exceptions

            if isinstance(e, g_exceptions.ResourceExhausted):
                return LLMRateLimitError(f"Gemini API Rate Limit: {e}", original=e)
            if isinstance(e, (g_exceptions.Unauthenticated, g_exceptions.PermissionDenied)):
                return LLMAuthenticationError(f"Gemini API Auth Error: {e}", original=e)
            if isinstance(e, g_exceptions.InvalidArgument):
                return LLMInvalidRequestError(f"Gemini API Invalid Request: {e}", original=e)
            if isinstance(e, g_exceptions.DeadlineExceeded):
                return LLMTimeoutError(f"Gemini Timeout: {e}", original=e)
            if isinstance(e, (g_exceptions.InternalServerError, g_exceptions.ServiceUnavailable)):
                return LLMServerError(f"Gemini Server Error: {e}", original=e)
        except ImportError:
            pass

        err_msg = str(e).lower()
        if "429" in err_msg or "rate limit" in err_msg:
            return LLMRateLimitError(f"Gemini API Rate Limit: {e}", original=e)
        if "401" in err_msg or "auth" in err_msg or "permission" in err_msg:
            return LLMAuthenticationError(f"Gemini API Auth Error: {e}", original=e)
        if "400" in err_msg or "invalid" in err_msg:
            return LLMInvalidRequestError(f"Gemini API Invalid Request: {e}", original=e)
        if "safety" in err_msg or "blocked" in err_msg:
            return LLMContentFilterError(f"Gemini Content Filter: {e}", original=e)
        if "500" in err_msg or "internal" in err_msg:
            return LLMServerError(f"Gemini Server Error: {e}", original=e)
        if "timeout" in err_msg:
            return LLMTimeoutError(f"Gemini Timeout: {e}", original=e)

        return LLMUnknownError(f"Unknown Gemini Error: {e}", original=e)

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
            # GeminiApiClient.generate_text は Tuple[str, Any] を返す
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
            # GeminiApiClient.generate_json は Tuple[Dict, str, Any] を返す
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
        """Gemini SDK の usage メタデータを共通形式に変換"""
        if not usage_metadata:
            return {}

        # usage_metadata の属性に基づいた抽出
        return {
            "prompt_tokens": getattr(usage_metadata, "prompt_token_count", 0),
            "completion_tokens": getattr(usage_metadata, "candidates_token_count", 0),
            "total_tokens": getattr(usage_metadata, "total_token_count", 0),
        }
