import openai
from typing import Any, AsyncIterator, Iterator
from src.core.llm.unified_interface import IUnifiedLLMClient
from src.core.llm.types import LLMRequest, LLMResponse, StreamChunk, LLMUsage

class OpenAIUnifiedClient(IUnifiedLLMClient):
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.sync_client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, req: LLMRequest) -> LLMResponse:
        response = self.sync_client.chat.completions.create(
            model=req.model or "gpt-4o",
            messages=[
                {"role": "system", "content": req.system_prompt},
                {"role": "user", "content": req.prompt}
            ],
            temperature=req.temperature,
            max_tokens=req.max_tokens
        )
        usage = LLMUsage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens
        )
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage=usage
        )

    async def agenerate(self, req: LLMRequest) -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=req.model or "gpt-4o",
            messages=[
                {"role": "system", "content": req.system_prompt},
                {"role": "user", "content": req.prompt}
            ],
            temperature=req.temperature,
            max_tokens=req.max_tokens
        )
        usage = LLMUsage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens
        )
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage=usage
        )

    def stream(self, req: LLMRequest) -> Iterator[StreamChunk]:
        response = self.sync_client.chat.completions.create(
            model=req.model or "gpt-4o",
            messages=[
                {"role": "system", "content": req.system_prompt},
                {"role": "user", "content": req.prompt}
            ],
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            stream=True
        )
        for chunk in response:
            content = chunk.choices[0].delta.content or ""
            yield StreamChunk(text=content)
        yield StreamChunk(text="", is_final=True)

    async def astream(self, req: LLMRequest) -> AsyncIterator[StreamChunk]:
        response = await self.client.chat.completions.create(
            model=req.model or "gpt-4o",
            messages=[
                {"role": "system", "content": req.system_prompt},
                {"role": "user", "content": req.prompt}
            ],
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            stream=True
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content or ""
            yield StreamChunk(text=content)
        yield StreamChunk(text="", is_final=True)
