"""Step 16 検証テスト: ImageProviderProtocol の単体テスト。"""

from __future__ import annotations

import asyncio

import pytest

from src.interfaces.image_provider import (
    BaseImageProvider,
    ImageProviderError,
    ImageProviderProtocol,
)


class FakeProvider(BaseImageProvider):
    name = "fake"

    def __init__(self, available: bool = True, **config: object) -> None:
        super().__init__(**config)
        self._available = available

    async def generate_image(self, prompt: str, **options: object) -> str:
        return f"data:image/png;base64,generated_for:{prompt}"

    def is_available(self) -> bool:
        return self._available


class TestImageProviderProtocol:
    def test_fake_provider_satisfies_protocol(self):
        provider = FakeProvider()
        assert isinstance(provider, ImageProviderProtocol)

    def test_protocol_defines_generate_image(self):
        assert hasattr(ImageProviderProtocol, "generate_image")
        assert hasattr(ImageProviderProtocol, "is_available")

    def test_generate_image_returns_url_or_path(self):
        provider = FakeProvider()
        result = asyncio.run(provider.generate_image("a cat in a garden"))
        assert "a cat in a garden" in result

    def test_generate_image_with_options(self):
        provider = FakeProvider()
        result = asyncio.run(
            provider.generate_image("castle", width=512, height=512, style="watercolor")
        )
        assert "castle" in result

    def test_base_provider_is_unavailable(self):
        provider = BaseImageProvider()
        assert provider.is_available() is False

    def test_base_provider_generate_raises(self):
        provider = BaseImageProvider()
        with pytest.raises(ImageProviderError):
            asyncio.run(provider.generate_image("test"))

    def test_provider_availability_toggles(self):
        provider = FakeProvider(available=False)
        assert provider.is_available() is False
        provider._available = True
        assert provider.is_available() is True
