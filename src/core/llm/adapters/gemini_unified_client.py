import os
from typing import Any, AsyncIterator, Iterator
from google import genai
from google.genai import types

from src.core.llm.unified_interface import IUnifiedLLMClient
from src.core.llm.types import LLMRequest, LLMResponse, StreamChunk, LLMUsage

class GeminiUnifiedClient(IUnifiedLLMClient):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def _build_config(self, req: LLMRequest) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            temperature=req.temperature,
            max_output_tokens=req.max_tokens,
            system_instruction=req.system_prompt
        )

    def generate(self, req: LLMRequest) -> LLMResponse:
        response = self.client.models.generate_content(
            model=req.model or self.model,
            contents=req.prompt,
            config=self._build_config(req)
        )
        usage = LLMUsage(
            prompt_tokens=response.usage_metadata.prompt_token_count or 0,
            completion_tokens=response.usage_metadata.candidates_token_count or 0,
            total_tokens=response.usage_metadata.total_token_count or 0
        )
        return LLMResponse(
            content=response.text or "",
            model=req.model or self.model,
            usage=usage
        )

    async def agenerate(self, req: LLMRequest) -> LLMResponse:
        # Note: google-genai SDK does not have async methods, so we use run_in_executor
        import asyncio
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: self.client.models.generate_content(
                model=req.model or self.model,
                contents=req.prompt,
                config=self._build_config(req)
            )
        )
        usage = LLMUsage(
            prompt_tokens=response.usage_metadata.prompt_token_count or 0,
            completion_tokens=response.usage_metadata.candidates_token_count or 0,
            total_tokens=response.usage_metadata.total_token_count or 0
        )
        return LLMResponse(
            content=response.text or "",
            model=req.model or self.model,
            usage=usage
        )

    def stream(self, req: LLMRequest) -> Iterator[StreamChunk]:
        response_stream = self.client.models.generate_content_stream(
            model=req.model or self.model,
            contents=req.prompt,
            config=self._build_config(req)
        )
        for chunk in response_stream:
            if chunk.text:
                yield StreamChunk(text=chunk.text)
        yield StreamChunk(text="", is_final=True)

    async def astream(self, req: LLMRequest) -> AsyncIterator[StreamChunk]:
        import asyncio
        loop = asyncio.get_running_loop()
        
        # Generator wrapper for run_in_executor
        def _get_stream():
            return self.client.models.generate_content_stream(
                model=req.model or self.model,
                contents=req.prompt,
                config=self._build_config(req)
            )

        stream = await loop.run_in_executor(None, _get_stream)
        
        for chunk in stream:
            if chunk.text:
                yield StreamChunk(text=chunk.text)
        yield StreamChunk(text="", is_final=True)
