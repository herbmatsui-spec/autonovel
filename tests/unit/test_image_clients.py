import base64
import pytest

from src.services.illustration.base import ImageGenerationRequest, ImageGenerationResult
from src.services.illustration.mock_client import MockImageClient
from src.services.illustration.sd_client import SDWebUIClient
from src.services.illustration.dalle_client import DalleClient
from src.services.illustration.factory import get_image_client


@pytest.mark.asyncio
async def test_mock_image_client_generates_image():
    """MockImageClient が画像を生成することを確認"""
    client = MockImageClient()
    req = ImageGenerationRequest(prompt="test prompt", width=64, height=64)
    result = await client.generate_image(req)
    assert isinstance(result, ImageGenerationResult)
    assert result.image_bytes.startswith(b"\x89PNG")
    assert result.format == "png"
    assert result.seed_used >= 0


@pytest.mark.asyncio
async def test_sd_webui_client_uses_http():
    """SDWebUIClient が HTTP 呼び出しを行うこと"""
    client = SDWebUIClient(base_url="http://localhost:9999", max_retries=1, timeout=0.1)
    req = ImageGenerationRequest(prompt="test prompt")
    with pytest.raises(RuntimeError):
        await client.generate_image(req)


@pytest.mark.asyncio
async def test_dalle_client_uses_http():
    """DalleClient が HTTP 呼び出しを行うこと"""
    client = DalleClient(base_url="http://localhost:9999", max_retries=1, timeout=0.1)
    req = ImageGenerationRequest(prompt="test prompt")
    with pytest.raises(RuntimeError):
        await client.generate_image(req)


@pytest.mark.asyncio
async def test_factory_returns_mock_client():
    """ファクトリが mock クライアントを返すこと"""
    client = get_image_client("mock")
    assert isinstance(client, MockImageClient)


@pytest.mark.asyncio
async def test_factory_rejects_unknown_provider():
    """ファクトリが未知のプロバイダを拒否すること"""
    with pytest.raises(ValueError):
        get_image_client("unknown")