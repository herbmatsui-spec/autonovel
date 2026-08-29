from typing import Any, Dict, Optional

from google import genai

from src.backend.engine_utils import AdaptiveCooldown
from src.core.exceptions import (
    LLMTemporaryError,
    LLMUnrecoverableError,
)
from src.core.llm.providers.base import LLMProvider, LLMResponse
from src.core.llm_clients.gemini import GeminiApiClient
from src.core.observability import track_llm_call


class GeminiProvider(LLMProvider):
    def __init__(self, client: genai.Client, cooldown: AdaptiveCooldown):
        self.internal_client = GeminiApiClient(client, cooldown)

    @track_llm_call
    async def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        nsfw_mode: bool = False,
        **kwargs,
    ) -> LLMResponse:
        try:
            content, usage = await self.internal_client.generate_text(
                model_name=model_name,
                prompt=prompt,
                system_instruction=system_instruction,
                temp=temperature,
                nsfw_mode=nsfw_mode,
                **kwargs,
            )
            return LLMResponse(content=content, usage=self._parse_usage(usage), success=True)
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg or "resource_exhausted" in err_msg:
                raise LLMTemporaryError(f"Gemini API Rate Limit: {e}", original=e) from e
            if "401" in err_msg or "auth" in err_msg or "permission" in err_msg:
                raise LLMUnrecoverableError(f"Gemini API Auth Error: {e}", original=e) from e
            if "400" in err_msg or "invalid" in err_msg:
                raise LLMUnrecoverableError(f"Gemini API Invalid Request: {e}", original=e) from e
            if "safety" in err_msg or "blocked" in err_msg:
                raise LLMUnrecoverableError(f"Gemini Content Filter: {e}", original=e) from e
            if any(k in err_msg for k in ["500", "502", "503", "504", "internal", "unavailable", "overloaded"]):
                raise LLMTemporaryError(f"Gemini Server Error (Temporary): {e}", original=e) from e
            if "timeout" in err_msg or "deadline" in err_msg:
                raise LLMTemporaryError(f"Gemini Timeout: {e}", original=e) from e
            raise LLMUnrecoverableError(f"Unknown Gemini Error: {e}", original=e) from e


    @track_llm_call
    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        response_schema: Optional[Any] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        nsfw_mode: bool = False,
        **kwargs,
    ) -> LLMResponse:
        try:
            metadata, content, usage = await self.internal_client.generate_json(
                model_name=model_name,
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction,
                temp=temperature,
                nsfw_mode=nsfw_mode,
                **kwargs,
            )
            return LLMResponse(
                content=content, metadata=metadata, usage=self._parse_usage(usage), success=True
            )
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg or "resource_exhausted" in err_msg:
                raise LLMTemporaryError(f"Gemini API Rate Limit: {e}", original=e) from e
            if "401" in err_msg or "auth" in err_msg or "permission" in err_msg:
                raise LLMUnrecoverableError(f"Gemini API Auth Error: {e}", original=e) from e
            if "400" in err_msg or "invalid" in err_msg:
                raise LLMUnrecoverableError(f"Gemini API Invalid Request: {e}", original=e) from e
            if "safety" in err_msg or "blocked" in err_msg:
                raise LLMUnrecoverableError(f"Gemini Content Filter: {e}", original=e) from e
            if any(k in err_msg for k in ["500", "502", "503", "504", "internal", "unavailable", "overloaded"]):
                raise LLMTemporaryError(f"Gemini Server Error (Temporary): {e}", original=e) from e
            if "timeout" in err_msg or "deadline" in err_msg:
                raise LLMTemporaryError(f"Gemini Timeout: {e}", original=e) from e
            raise LLMUnrecoverableError(f"Unknown Gemini Error: {e}", original=e) from e

    def _parse_usage(self, usage_metadata: Any) -> Dict[str, int]:

        if not usage_metadata:
            return {}
        return {
            "prompt_tokens": getattr(usage_metadata, "prompt_token_count", 0),
            "completion_tokens": getattr(usage_metadata, "candidates_token_count", 0),
            "total_tokens": getattr(usage_metadata, "total_token_count", 0),
        }
