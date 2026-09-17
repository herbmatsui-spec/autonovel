"""画像生成アダプタ（DALL-E 3, fal.ai, 共通インターフェース）の単体テスト (v5.0 Step 1〜3)."""
import base64
import pytest
from unittest.mock import AsyncMock, MagicMock

import httpx

from src.services.illustration.adapters.base import (
    ImagePromptRequest,
    GeneratedImageResult,
    ImageGenerationAdapter,
)
from src.services.illustration.adapters.dalle3_adapter import Dalle3Adapter
from src.services.illustration.adapters.fal_adapter import FalAiAdapter


class TestImagePromptRequest:
    def test_request_defaults(self):
        req = ImagePromptRequest(prompt="ファンタジー勇者")
        assert req.prompt == "ファンタジー勇者"
        assert req.aspect_ratio == "1:1"
        assert req.width == 1024
        assert req.height == 1024
        assert req.steps == 25
        assert req.style == "anime"


class TestDalle3Adapter:
    def test_initialization_and_provider_name(self):
        adapter = Dalle3Adapter(api_key="sk-test-dalle")
        assert adapter.provider_name == "dalle3"
        assert adapter.base_url == "https://api.openai.com/v1"

    @pytest.mark.asyncio
    async def test_generate_image_square_success(self):
        dummy_png_bytes = b"fake-png-bytes-for-test"
        b64_str = base64.b64encode(dummy_png_bytes).decode("utf-8")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {
                    "b64_json": b64_str,
                    "revised_prompt": "A heroic fantasy warrior with a shining sword",
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        adapter = Dalle3Adapter(api_key="sk-test", client=mock_client)
        req = ImagePromptRequest(prompt="勇者", aspect_ratio="1:1")
        res = await adapter.generate_image(req)

        assert res.provider == "dalle3"
        assert res.format == "png"
        assert res.image_bytes == dummy_png_bytes
        assert res.cost_usd == 0.040
        assert "heroic fantasy warrior" in res.metadata.get("revised_prompt", "")

        # 検証: POST ペイロード
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["size"] == "1024x1024"
        assert payload["model"] == "dall-e-3"

    @pytest.mark.asyncio
    async def test_generate_image_horizontal_size(self):
        dummy_png_bytes = b"fake-horizontal-bytes"
        b64_str = base64.b64encode(dummy_png_bytes).decode("utf-8")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"b64_json": b64_str}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        adapter = Dalle3Adapter(api_key="sk-test", client=mock_client)
        req = ImagePromptRequest(prompt="パノラマ風景", aspect_ratio="16:9")
        res = await adapter.generate_image(req)

        assert res.image_bytes == dummy_png_bytes
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["size"] == "1792x1024"

    @pytest.mark.asyncio
    async def test_generate_image_vertical_size(self):
        dummy_png_bytes = b"fake-vertical-bytes"
        b64_str = base64.b64encode(dummy_png_bytes).decode("utf-8")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"b64_json": b64_str}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        adapter = Dalle3Adapter(api_key="sk-test", client=mock_client)
        req = ImagePromptRequest(prompt="立ち絵キャラクター", aspect_ratio="9:16")
        res = await adapter.generate_image(req)

        assert res.image_bytes == dummy_png_bytes
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["size"] == "1024x1792"


class TestFalAiAdapter:
    def test_initialization_and_provider_name(self):
        adapter = FalAiAdapter(api_key="fal-test-key")
        assert adapter.provider_name == "fal_ai"
        assert adapter.model_endpoint == "fal-ai/flux/schnell"

    @pytest.mark.asyncio
    async def test_generate_image_flux_schnell(self):
        img_content = b"fal-flux-image-bytes"

        submit_resp = MagicMock()
        submit_resp.json.return_value = {
            "images": [{"url": "https://fal.media/files/sample.png"}]
        }
        submit_resp.raise_for_status = MagicMock()

        img_resp = MagicMock()
        img_resp.content = img_content
        img_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = submit_resp
        mock_client.get.return_value = img_resp

        adapter = FalAiAdapter(api_key="fal-test", client=mock_client)
        req = ImagePromptRequest(prompt="未来都市のサイバーパンク", aspect_ratio="16:9")
        res = await adapter.generate_image(req)

        assert res.provider == "fal_ai"
        assert res.image_bytes == img_content
        assert res.cost_usd == 0.0035
        assert res.metadata.get("endpoint") == "fal-ai/flux/schnell"

        # 検証: POST ペイロード
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["image_size"] == "landscape_16_9"
        assert payload["num_inference_steps"] <= 10


# ── Step 4: MockImageAdapter ──

class TestMockImageAdapter:
    def test_mock_adapter_provider_name(self):
        from src.services.illustration.adapters.mock_adapter import MockImageAdapter
        adapter = MockImageAdapter()
        assert adapter.provider_name == "mock"

    @pytest.mark.asyncio
    async def test_mock_adapter_generate_image(self):
        from src.services.illustration.adapters.mock_adapter import MockImageAdapter
        adapter = MockImageAdapter()
        req = ImagePromptRequest(prompt="テスト挿絵", aspect_ratio="1:1", style="anime")
        res = await adapter.generate_image(req)

        assert res.provider == "mock"
        assert res.format == "png"
        assert res.cost_usd == 0.0
        assert len(res.image_bytes) > 0
        assert res.metadata["mock_prompt"] == "テスト挿絵"


# ── Step 5 & 6: get_image_adapter Factory ──

class TestImageFactory:
    def test_factory_returns_mock_default(self, monkeypatch):
        from src.services.illustration.factory import get_image_adapter
        monkeypatch.delenv("IMAGE_PROVIDER", raising=False)
        adapter = get_image_adapter()
        assert adapter.provider_name == "mock"

    def test_factory_returns_mock_on_unknown(self):
        from src.services.illustration.factory import get_image_adapter
        adapter = get_image_adapter("unknown_provider_xyz")
        assert adapter.provider_name == "mock"

    def test_factory_returns_dalle3(self, monkeypatch):
        from src.services.illustration.factory import get_image_adapter
        monkeypatch.setenv("OPENAI_API_KEY", "sk-factory-test")
        adapter = get_image_adapter("dalle3")
        assert adapter.provider_name == "dalle3"
        assert adapter.api_key == "sk-factory-test"

    def test_factory_returns_fal_ai(self, monkeypatch):
        from src.services.illustration.factory import get_image_adapter
        monkeypatch.setenv("FAL_KEY", "fal-factory-test")
        adapter = get_image_adapter("fal")
        assert adapter.provider_name == "fal_ai"
        assert adapter.api_key == "fal-factory-test"

