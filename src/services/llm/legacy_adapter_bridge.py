from typing import Any, AsyncIterator
from src.services.llm.base import BaseLLMAdapter
from src.core.llm.unified_interface import IUnifiedLLMClient
from src.core.llm.types import LLMRequest

class LegacyLLMBridge(BaseLLMAdapter):
    def __init__(self, client: IUnifiedLLMClient):
        self.client = client

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        req = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt or "",
            temperature=temperature,
            max_tokens=max_tokens,
            extra_params=kwargs
        )
        resp = await self.client.agenerate(req)
        return resp.content

    async def stream_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        req = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt or "",
            temperature=temperature,
            max_tokens=max_tokens,
            extra_params=kwargs
        )
        async for chunk in self.client.astream(req):
            yield chunk.text
