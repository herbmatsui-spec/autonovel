from typing import Any
from src.core.spi.llm.interface import ILLMProvider
from src.core.llm.unified_interface import IUnifiedLLMClient
from src.core.llm.types import LLMRequest

class LegacySPIBridge(ILLMProvider):
    def __init__(self, client: IUnifiedLLMClient):
        self.client = client

    def generate(self, prompt: str, **kwargs: Any) -> str:
        req = LLMRequest(prompt=prompt, extra_params=kwargs)
        resp = self.client.generate(req)
        return resp.content

    async def agenerate(self, prompt: str, **kwargs: Any) -> str:
        req = LLMRequest(prompt=prompt, extra_params=kwargs)
        resp = await self.client.agenerate(req)
        return resp.content
