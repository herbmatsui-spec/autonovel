from typing import Any, Dict, Optional

from src.backend.engine_utils import AdaptiveCooldown
from src.core.exceptions import (
    LLMTokenLimitError,
    LLMUnrecoverableError,
    LLMTemporaryError,
)
from src.core.llm_clients.openai import OpenAIApiClient
from src.core.observability import track_llm_call
from src.core.llm.providers.base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    def __init__(self, cooldown: AdaptiveCooldown):
        self.internal_client = OpenAIApiClient(cooldown)

    @track_llm_call
    async def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        try:
            content, usage = await self.internal_client.generate_text(
                model_name=model_name,
                prompt=prompt,
                system_instruction=system_instruction,
                temp=temperature,
                **kwargs,
            )
            return LLMResponse(content=content, usage=self._parse_usage(usage), success=True)
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg:
                raise LLMTemporaryError(f"OpenAI API Rate Limit: {e}", original=e) from e
            if "401" in err_msg or "auth" in err_msg:
                raise LLMUnrecoverableError(f"OpenAI API Auth Error: {e}", original=e) from e
            if "400" in err_msg or "invalid" in err_msg:
                raise LLMUnrecoverableError(f"OpenAI API Invalid Request: {e}", original=e) from e
            if "filter" in err_msg or "blocked" in err_msg:
                raise LLMUnrecoverableError(f"OpenAI Content Filter: {e}", original=e) from e
            if "500" in err_msg or "internal" in err_msg:
                raise LLMUnrecoverableError(f"OpenAI Server Error: {e}", original=e) from e
            if "timeout" in err_msg:
                raise LLMTemporaryError(f"OpenAI Timeout: {e}", original=e) from e
            raise LLMUnrecoverableError(f"Unknown OpenAI Error: {e}", original=e) from e

    @track_llm_call
    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        response_schema: Optional[Any] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        try:
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
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg:
                raise LLMTemporaryError(f"OpenAI API Rate Limit: {e}", original=e) from e
            if "401" in err_msg or "auth" in err_msg:
                raise LLMUnrecoverableError(f"OpenAI API Auth Error: {e}", original=e) from e
            if "400" in err_msg or "invalid" in err_msg:
                raise LLMUnrecoverableError(f"OpenAI API Invalid Request: {e}", original=e) from e
            if "filter" in err_msg or "blocked" in err_msg:
                raise LLMUnrecoverableError(f"OpenAI Content Filter: {e}", original=e) from e
            if "500" in err_msg or "internal" in err_msg:
                raise LLMUnrecoverableError(f"OpenAI Server Error: {e}", original=e) from e
            if "timeout" in err_msg:
                raise LLMTemporaryError(f"OpenAI Timeout: {e}", original=e) from e
            raise LLMUnrecoverableError(f"Unknown OpenAI Error: {e}", original=e) from e

    def _parse_usage(self, usage_metadata: Any) -> Dict[str, int]:
        if not usage_metadata:
            return {}
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