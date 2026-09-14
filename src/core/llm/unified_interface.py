import time
import functools
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from typing import TypeVar, Type, cast, Callable, Any
from src.core.llm.types import LLMRequest, LLMResponse, StreamChunk

T = TypeVar("T")

def with_metrics(func: Callable):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        if isinstance(result, LLMResponse):
            result.latency_ms = (end - start) * 1000
        return result
    return wrapper

class IUnifiedLLMClient(ABC):
    @abstractmethod
    def generate(self, req: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    async def agenerate(self, req: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    def stream(self, req: LLMRequest) -> Iterator[StreamChunk]: ...

    @abstractmethod
    async def astream(self, req: LLMRequest) -> AsyncIterator[StreamChunk]: ...

    def generate_structured(self, req: LLMRequest, schema: Type[T]) -> T:
        req.json_mode = True
        req.response_schema = schema
        resp = self.generate(req)
        if resp.parsed_json is None:
            raise ValueError("No JSON parsed")
        return cast(T, resp.parsed_json)
