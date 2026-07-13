from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.llm_gateway import GeminiApiClient


@pytest.mark.asyncio
async def test_gemini_api_client_streaming_callback():
    # Mock setup
    mock_client = MagicMock()
    mock_cooldown = MagicMock()
    mock_cooldown.wait = AsyncMock()
    mock_cooldown.on_success = MagicMock()

    # Mock stream response (synchronous iterator, as actual code wraps in thread)
    class MockStreamResponse:
        def __init__(self):
            self._chunks = [MockChunk("Hello "), MockChunk("world!")]
            self._index = 0

        def __iter__(self):
            return self

        def __next__(self):
            if self._index < len(self._chunks):
                chunk = self._chunks[self._index]
                self._index += 1
                return chunk
            raise StopIteration

    class MockChunk:
        def __init__(self, text):
            self.text = text

    # GeminiApiClient uses generate_content_stream for streaming (synchronous, wrapped in thread)
    mock_client.models.generate_content_stream = MagicMock(return_value=MockStreamResponse())

    api_client = GeminiApiClient(client=mock_client, cooldown=mock_cooldown)

    # Callback to track streaming
    received_chunks = []
    def stream_callback(chunk):
        received_chunks.append(chunk)

    # Execute
    text, raw = await api_client.generate_text(
        model_name="test_model",
        prompt="Test prompt",
        stream_callback=stream_callback
    )

    # Assertions
    assert "Hello world!" in text
    assert received_chunks == ["Hello ", "world!"]
    mock_cooldown.wait.assert_called_once()
