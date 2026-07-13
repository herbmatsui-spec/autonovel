from typing import Any, Dict, Optional

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
from src.core.llm_gateway import GeminiApiClient
from src.core.observability import track_llm_call
from src.llm.base import LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    """
    Google Gemini API へのアダプター。
    内部的に GeminiApiClient を利用して低レベル通信とリトライを管理する。
    """
    def __init__(self, client: genai.Client, cooldown: AdaptiveCooldown):
        self.internal_client = GeminiApiClient(client, cooldown)

    @track_llm_call
    async def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        try:
            # GeminiApiClient.generate_text は Tuple[str, Any] を返す
            content, usage = await self.internal_client.generate_text(
                model_name=model_name,
                prompt=prompt,
                system_instruction=system_instruction,
                temp=temperature,
                **kwargs
            )
            return LLMResponse(
                content=content,
                usage=self._parse_usage(usage),
                success=True
            )
        except Exception as e:
            # 例外のマッピング
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg:
                raise LLMRateLimitError(f"Gemini API Rate Limit: {e}", e) from e
            if "401" in err_msg or "auth" in err_msg:
                raise LLMAuthenticationError(f"Gemini API Auth Error: {e}", e) from e
            if "400" in err_msg or "invalid" in err_msg:
                raise LLMInvalidRequestError(f"Gemini API Invalid Request: {e}", e) from e
            if "safety" in err_msg or "blocked" in err_msg:
                raise LLMContentFilterError(f"Gemini Content Filter: {e}", e) from e
            if "500" in err_msg or "internal" in err_msg:
                raise LLMServerError(f"Gemini Server Error: {e}", e) from e
            if "timeout" in err_msg:
                raise LLMTimeoutError(f"Gemini Timeout: {e}", e) from e

            raise LLMUnknownError(f"Unknown Gemini Error: {e}", e) from e

    @track_llm_call
    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        response_schema: Optional[Any] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        try:
            # GeminiApiClient.generate_json は Tuple[Dict, str, Any] を返す
            metadata, content, usage = await self.internal_client.generate_json(
                model_name=model_name,
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction,
                temp=temperature,
                **kwargs
            )
            return LLMResponse(
                content=content,
                metadata=metadata,
                usage=self._parse_usage(usage),
                success=True
            )
        except Exception as e:
            # 例外のマッピング
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg:
                raise LLMRateLimitError(f"Gemini API Rate Limit: {e}", e) from e
            if "401" in err_msg or "auth" in err_msg:
                raise LLMAuthenticationError(f"Gemini API Auth Error: {e}", e) from e
            if "400" in err_msg or "invalid" in err_msg:
                raise LLMInvalidRequestError(f"Gemini API Invalid Request: {e}", e) from e
            if "safety" in err_msg or "blocked" in err_msg:
                raise LLMContentFilterError(f"Gemini Content Filter: {e}", e) from e
            if "500" in err_msg or "internal" in err_msg:
                raise LLMServerError(f"Gemini Server Error: {e}", e) from e
            if "timeout" in err_msg:
                raise LLMTimeoutError(f"Gemini Timeout: {e}", e) from e

            raise LLMUnknownError(f"Unknown Gemini Error: {e}", e) from e

    def _parse_usage(self, usage_metadata: Any) -> Dict[str, int]:
        """Gemini SDK の usage メタデータを共通形式に変換"""
        if not usage_metadata:
            return {}

        # usage_metadata の属性に基づいた抽出
        return {
            "prompt_tokens": getattr(usage_metadata, "prompt_token_count", 0),
            "completion_tokens": getattr(usage_metadata, "candidates_token_count", 0),
            "total_tokens": getattr(usage_metadata, "total_token_count", 0),
        }
