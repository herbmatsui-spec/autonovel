import json
from typing import Any, Callable, Dict, Optional, Tuple


class MockGeminiApiClient:
    """Mock for GeminiApiClient to be used in integration tests."""
    def __init__(self):
        self.call_history = []
        self.mock_json_responses = {}
        self.mock_text_responses = {}
        self.default_json_response = {"success": True, "result": "mock_json"}
        self.default_text_response = "アレンは静かに剣を置いた。ギルドマスターの冷酷な声が響く。「お前はクビだ」。アレンはただ黙って部屋を後にした。新たな伝説の始まりだった。これは十分な長さを持つテスト用のダミーテキストです。"
        self.models = MockModels(self)

    def add_json_response(self, model_name_or_prompt: str, response: Dict[str, Any]):
        self.mock_json_responses[model_name_or_prompt] = response

    def add_text_response(self, model_name_or_prompt: str, response: str):
        self.mock_text_responses[model_name_or_prompt] = response

    def add_exception(self, model_name_or_prompt: str, exception: Exception):
        if not hasattr(self, 'mock_exceptions'):
            self.mock_exceptions = {}
        self.mock_exceptions[model_name_or_prompt] = exception

    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Any = None,
        temp: float = 0.7,
        max_retries: int = 5,
        stream_callback: Optional[Callable[[str], None]] = None,
        retry_state: Optional[Any] = None,
        **kwargs
    ) -> Tuple[Dict[str, Any], str, Any]:

        # Check for mock exceptions
        if hasattr(self, 'mock_exceptions'):
            for k, v in self.mock_exceptions.items():
                if k in (model_name or "") or k in (prompt or ""):
                    raise v

        self.call_history.append({
            "method": "generate_json",
            "model_name": model_name,
            "prompt": prompt,
            "system_instruction": system_instruction,
            "response_schema": response_schema,
            "temp": temp
        })

        res = self.default_json_response
        for k, v in self.mock_json_responses.items():
            if (prompt and k in prompt) or k == model_name:
                res = v
                break

        class MockUsage:
            def __init__(self):
                self.prompt_token_count = 10
                self.candidates_token_count = 20

        # metadata, story, usage
        return res, json.dumps(res, ensure_ascii=False), MockUsage()

    async def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        max_retries: int = 5,
        stream_callback: Optional[Callable[[str], None]] = None,
        retry_state: Optional[Any] = None,
        **kwargs
    ) -> Tuple[str, Any]:

        # Check for mock exceptions
        if hasattr(self, 'mock_exceptions'):
            for k, v in self.mock_exceptions.items():
                if k in (model_name or "") or k in (prompt or ""):
                    raise v

        self.call_history.append({
            "method": "generate_text",
            "model_name": model_name,
            "prompt": prompt,
            "system_instruction": system_instruction,
            "temp": temp
        })

        res = self.default_text_response
        for k, v in self.mock_text_responses.items():
            if (prompt and k in prompt) or k == model_name:
                res = v
                break

        if stream_callback:
            import inspect
            if inspect.iscoroutinefunction(stream_callback):
                await stream_callback(res)
            else:
                ret = stream_callback(res)
                if inspect.iscoroutine(ret):
                    await ret

        class MockUsage:
            def __init__(self):
                self.prompt_token_count = 10
                self.candidates_token_count = 20

        # story, usage
        return res, MockUsage()


class MockResponse:
    def __init__(self, text, usage):
        self.text = text
        self.usage_metadata = usage


class MockModels:
    def __init__(self, client: MockGeminiApiClient):
        self.client = client

    def generate_content(self, model: str, contents: Any, config: Any = None):
        prompt = contents[0] if isinstance(contents, list) else contents
        is_json = False
        if config:
            is_json = getattr(config, "response_mime_type", None) == "application/json" or getattr(config, "response_schema", None) is not None

        class MockUsage:
            def __init__(self):
                self.prompt_token_count = 10
                self.candidates_token_count = 20

        if is_json:
            res = self.client.default_json_response
            for k, v in self.client.mock_json_responses.items():
                if k in prompt or k == model:
                    res = v
                    break
            text = json.dumps(res, ensure_ascii=False)
        else:
            res = self.client.default_text_response
            for k, v in self.client.mock_text_responses.items():
                if k in prompt or k == model:
                    res = v
                    break
            text = res

        self.client.call_history.append({
            "method": "generate_json" if is_json else "generate_text",
            "model_name": model,
            "prompt": prompt,
            "config": config
        })

        return MockResponse(text, MockUsage())

    async def generate_content_async(self, model: str, contents: Any, config: Any = None):
        return self.generate_content(model, contents, config)

    async def generate_content_stream_async(self, model: str, contents: Any, config: Any = None):
        res = self.generate_content(model, contents, config)
        class AsyncStream:
            def __init__(self, item):
                self.item = item
                self.done = False
            def __aiter__(self):
                return self
            async def __anext__(self):
                if self.done:
                    raise StopAsyncIteration
                self.done = True
                return self.item
        return AsyncStream(res)

    def generate_content_stream(self, model: str, contents: Any, config: Any = None):
        res = self.generate_content(model, contents, config)
        return [res]


from src.models import GenerateResult


class LLMGenerateResultMockProxy:
    def __init__(self, mock_llm):
        self.mock_llm = mock_llm

    async def generate_json(self, *args, **kwargs):
        if len(args) == 1 and hasattr(args[0], "prompt"):
            request = args[0]
            res, text, usage = await self.mock_llm.generate_json(
                model_name=request.model_name,
                prompt=request.prompt,
                system_instruction=request.system_instruction,
                response_schema=request.response_schema,
                temp=request.temp,
                **kwargs
            )
        else:
            res, text, usage = await self.mock_llm.generate_json(*args, **kwargs)
        return GenerateResult(success=True, metadata=res, story_content=text)

    async def generate_text(self, *args, **kwargs):
        if len(args) == 1 and hasattr(args[0], "prompt"):
            request = args[0]
            text, usage = await self.mock_llm.generate_text(
                model_name=getattr(request, "model_name", None) or getattr(request, "purpose", "writing"),
                prompt=request.prompt,
                system_instruction=request.system_instruction,
                temp=getattr(request, "temp", 0.7),
                **kwargs
            )
        else:
            purpose = kwargs.pop("purpose", None)
            if purpose and "model_name" not in kwargs:
                from src.llm.model_router import select_model
                kwargs["model_name"] = select_model(purpose)
            text, usage = await self.mock_llm.generate_text(*args, **kwargs)
        return GenerateResult(success=True, story_content=text)
