import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from google.genai import types

from src.services.llm.gemini_adapter import GeminiAdapter
from src.services.image_service import ImageService


@pytest.mark.asyncio
async def test_gemini_adapter_unified_genai_call():
    """Verify GeminiAdapter correctly uses google.genai Client."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Generated novel text."
    
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    adapter = GeminiAdapter(api_key="dummy-key")
    adapter._client = mock_client

    result = await adapter.generate_text(
        prompt="Write a scene.",
        system_prompt="You are a novelist.",
        temperature=0.7,
    )

    assert result == "Generated novel text."
    assert mock_client.aio.models.generate_content.called


@pytest.mark.asyncio
async def test_image_service_unified_genai_call():
    """Verify ImageService correctly uses google.genai Client for Imagen."""
    mock_client = MagicMock()
    mock_img_item = MagicMock()
    mock_img_item.image.image_bytes = b"fake_png_data"
    mock_response = MagicMock()
    mock_response.generated_images = [mock_img_item]
    mock_client.models.generate_images.return_value = mock_response

    with patch.object(ImageService, "_save_image", return_value="/static/illustrations/img_test.png"):
        service = ImageService(api_key="dummy-key")
        service.client = mock_client

        url = await service.generate(prompt="A beautiful fantasy cover")

        assert url == "/static/illustrations/img_test.png"
        assert mock_client.models.generate_images.called
