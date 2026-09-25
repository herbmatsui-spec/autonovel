"""Unit tests for src.core.llm_clients (GeminiApiClient / OpenAIApiClient).

Notes:
- Tests avoid real executor thread pools by patching executor_manager.run_io.
- Rate-limit retry paths are exercised through Gemini's _handle_error and
  OpenAI's direct error classification without triggering long backoff sleeps.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import LLMUnrecoverableError
from src.core.llm_clients.gemini import GeminiApiClient
from src.core.llm_clients.openai import OpenAIApiClient
from src.backend.engine_utils import AdaptiveCooldown
from pydantic import BaseModel


class SampleSchema(BaseModel):
    title: str
    score: int


class FakeUsage:
    def __init__(self, prompt=10, candidates=5):
        self.prompt_token_count = prompt
        self.candidates_token_count = candidates


def _make_cooldown() -> AdaptiveCooldown:
    return AdaptiveCooldown(base_sec=2.0, min_sec=1.0, max_sec=60.0)


@pytest.fixture
def fast_executor(monkeypatch):
    """Replace executor_manager.run_io with a direct async call to avoid real thread pools."""
    from src.core import executor_manager as em_module

    async def _run_io(func, *args, **kwargs):
        return func(*args, **kwargs)

    em = em_module.executor_manager
    monkeypatch.setattr(em, "run_io", _run_io)


def _patch_project_context(side_effect=None):
    return patch(
        "config.project_context.ProjectContext.get_setting",
        side_effect=side_effect or (lambda k, d=None: d),
    )


# ------------------------------------------------------------- GeminiApiClient
class TestGeminiConfig:
    def test_build_config_native(self):
        client = GeminiApiClient(MagicMock(), _make_cooldown())
        cfg = client.build_config("sys", 1.0, 0, None)
        assert cfg.system_instruction == "sys"
        assert cfg.temperature == pytest.approx(1.0)
        assert cfg.response_schema is None
        assert cfg.response_mime_type != "application/json"

    def test_build_config_temp_cooldown_by_attempt(self):
        client = GeminiApiClient(MagicMock(), _make_cooldown())
        cfg = client.build_config("sys", 1.0, 3, None)
        assert cfg.temperature == pytest.approx(max(0.0, 1.0 - 3 * 0.15))

    def test_build_config_nsfw_safety(self):
        client = GeminiApiClient(MagicMock(), _make_cooldown())
        cfg = client.build_config_for_mode("sys", 1.0, 0, None, "native", nsfw_mode=True)
        assert cfg.safety_settings is not None

    def test_build_config_native_schema(self):
        client = GeminiApiClient(MagicMock(), _make_cooldown())
        cfg = client.build_config("sys", 0.7, 0, SampleSchema)
        assert cfg.response_mime_type == "application/json"
        assert cfg.response_schema is SampleSchema

    def test_build_config_clean_dict_schema(self):
        client = GeminiApiClient(MagicMock(), _make_cooldown())
        cfg = client.build_config_for_mode("sys", 0.7, 0, SampleSchema, "clean_dict")
        assert cfg.response_mime_type == "application/json"
        assert isinstance(cfg.response_schema, dict)


class TestGeminiGenerateJson:
    def _mock_response(self, text: str) -> MagicMock:
        resp = MagicMock()
        resp.text = text
        resp.usage_metadata = FakeUsage()
        return resp

    def test_success_without_schema(self, fast_executor):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = self._mock_response('{"title": "T", "score": 5}')
        client = GeminiApiClient(mock_client, _make_cooldown())

        metadata, story, usage = _run(client.generate_json("gemini-pro", "prompt"))
        assert metadata["title"] == "T"
        assert metadata["score"] == 5
        assert usage is not None
        called_model = mock_client.models.generate_content.call_args.kwargs["model"]
        assert called_model == "models/gemini-pro"

    def test_success_with_models_prefix_not_duplicated(self, fast_executor):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = self._mock_response('{"a": 1}')
        client = GeminiApiClient(mock_client, _make_cooldown())

        _run(client.generate_json("models/gemini-pro", "prompt"))
        called_model = mock_client.models.generate_content.call_args.kwargs["model"]
        assert called_model == "models/gemini-pro"

    def test_success_with_schema_and_prompt_fallback(self, fast_executor):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = self._mock_response('{"title": "T", "score": 3}')
        client = GeminiApiClient(mock_client, _make_cooldown())

        metadata, story, _ = _run(
            client.generate_json("gemini-pro", "prompt", response_schema=SampleSchema)
        )
        assert metadata["title"] == "T"

    def test_stream_callback_mode(self, fast_executor):
        mock_client = MagicMock()
        chunk = MagicMock()
        chunk.text = '{"title": "S", "score": 1}'
        chunk.usage_metadata = FakeUsage()
        mock_client.models.generate_content_stream.return_value = [chunk]
        client = GeminiApiClient(mock_client, _make_cooldown())

        collected = []
        metadata, _, _ = _run(
            client.generate_json("gemini-pro", "p", stream_callback=collected.append)
        )
        assert metadata["title"] == "S"
        assert metadata["score"] == 1
        assert collected == ['{"title": "S", "score": 1}']

    def test_schema_error_falls_back_to_next_mode(self, fast_executor):
        mock_client = MagicMock()
        ok = self._mock_response('{"title": "OK", "score": 2}')
        mock_client.models.generate_content.side_effect = [
            ValueError("Invalid argument: schema additionalProperties not allowed"),
            ok,
        ]
        client = GeminiApiClient(mock_client, _make_cooldown())

        metadata, _, _ = _run(
            client.generate_json("gemini-pro", "p", response_schema=SampleSchema)
        )
        assert metadata["title"] == "OK"
        assert mock_client.models.generate_content.call_count == 2

    def test_unrecoverable_error_raises(self, fast_executor):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = ValueError("401 unauthorized invalid key")
        client = GeminiApiClient(mock_client, _make_cooldown())

        with pytest.raises(Exception):
            _run(client.generate_json("gemini-pro", "p"))

    def test_empty_response_raises(self, fast_executor):
        mock_client = MagicMock()
        resp = MagicMock()
        resp.text = None
        mock_client.models.generate_content.return_value = resp
        client = GeminiApiClient(mock_client, _make_cooldown())

        with pytest.raises(Exception):
            _run(client.generate_json("gemini-pro", "p"))


class TestGeminiHandleError:
    @pytest.mark.asyncio
    async def test_rate_limit_returns_true(self):
        client = GeminiApiClient(MagicMock(), _make_cooldown())
        result = await client._handle_error(ValueError("429 quota exceeded"), "m", 0, 5)
        assert result is True

    @pytest.mark.asyncio
    async def test_rate_limit_with_retry_hint(self):
        client = GeminiApiClient(MagicMock(), _make_cooldown())
        result = await client._handle_error(ValueError("429 please retry in 3.5 seconds"), "m", 0, 5)
        assert result is True

    @pytest.mark.asyncio
    async def test_unrecoverable_raises(self):
        client = GeminiApiClient(MagicMock(), _make_cooldown())
        with pytest.raises(LLMUnrecoverableError):
            await client._handle_error(ValueError("403 forbidden"), "m", 0, 5)

    @pytest.mark.asyncio
    async def test_unknown_error_returns_false(self):
        client = GeminiApiClient(MagicMock(), _make_cooldown())
        result = await client._handle_error(ValueError("something weird"), "m", 0, 5)
        assert result is False


# ------------------------------------------------------------- OpenAIApiClient
class TestOpenAIGenerateJson:
    def _setup_openai(self, content: str):
        usage = SimpleNamespace(prompt_tokens=11, completion_tokens=7)
        choice = SimpleNamespace(message=SimpleNamespace(content=content), usage=usage)
        response = SimpleNamespace(choices=[choice])
        return response

    def test_success_without_schema(self):
        response = self._setup_openai('{"title": "O", "score": 9}')
        mock_async = MagicMock()
        mock_async.chat.completions.create = AsyncMock(return_value=response)

        with patch("openai.AsyncOpenAI", return_value=mock_async), _patch_project_context():
            client = OpenAIApiClient(_make_cooldown())
            metadata, story, usage = _run(client.generate_json("gemma-3", "prompt"))

        assert metadata["title"] == "O"
        assert metadata["score"] == 9
        assert usage.prompt_token_count == 11
        assert usage.candidates_token_count == 7

    def test_success_with_system_instruction(self):
        response = self._setup_openai('{"a": 1}')
        mock_async = MagicMock()
        mock_async.chat.completions.create = AsyncMock(return_value=response)

        with patch("openai.AsyncOpenAI", return_value=mock_async), _patch_project_context():
            client = OpenAIApiClient(_make_cooldown())
            _run(client.generate_json("gemma-3", "prompt", system_instruction="be nice"))

        messages = mock_async.chat.completions.create.call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"

    def test_unrecoverable_error(self):
        mock_async = MagicMock()
        mock_async.chat.completions.create = AsyncMock(side_effect=ValueError("401 unauthorized"))

        with patch("openai.AsyncOpenAI", return_value=mock_async), _patch_project_context():
            client = OpenAIApiClient(_make_cooldown())
            with pytest.raises(LLMUnrecoverableError):
                _run(client.generate_json("gemma-3", "p"))


class TestOpenAIGenerateText:
    def test_generate_text_delegates_to_json(self):
        response = SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="plain story"),
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2),
            )]
        )
        mock_async = MagicMock()
        mock_async.chat.completions.create = AsyncMock(return_value=response)

        with patch("openai.AsyncOpenAI", return_value=mock_async), _patch_project_context():
            client = OpenAIApiClient(_make_cooldown())
            story, usage = _run(client.generate_text("gemma-3", "prompt"))

        assert isinstance(story, str)
        assert usage is not None
        # generate_text delegates internally to generate_json
        assert mock_async.chat.completions.create.call_count == 1


def _run(coro):
    """Run a coroutine to completion using a fresh event loop."""
    import asyncio

    return asyncio.run(coro)
