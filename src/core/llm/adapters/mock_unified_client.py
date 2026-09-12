from typing import Iterator, AsyncIterator
from src.core.llm.types import LLMRequest, LLMResponse, StreamChunk
from src.core.llm.unified_interface import IUnifiedLLMClient, with_metrics

class UnifiedMockLLMClient(IUnifiedLLMClient):
    def __init__(self, response_text: str = "Mock response"):
        self.response_text = response_text

    @with_metrics
    def generate(self, req: LLMRequest) -> LLMResponse:
        return LLMResponse(content=self.response_text, model="mock-model")

    async def agenerate(self, req: LLMRequest) -> LLMResponse:
        return self.generate(req)

    def stream(self, req: LLMRequest) -> Iterator[StreamChunk]:
        yield StreamChunk(text=self.response_text, is_final=True)

    async def astream(self, req: LLMRequest) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(text=self.response_text, is_final=True)
        return
