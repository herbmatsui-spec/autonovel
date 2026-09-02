"""GenAI Image Provider Adapter."""

from __future__ import annotations

from typing import Any

from src.core.spi.interface import IImageProvider, ImageResult


class GenAIImageProvider(IImageProvider):
    """GenAI image generation adapter implementation."""

    def __init__(self, api_key: str = "", model_name: str = "imagen-3.0", **kwargs: Any) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.extra_config = kwargs

    def generate_image(self, prompt: str, **kwargs: Any) -> ImageResult:
        """Generate image via GenAI API."""
        return ImageResult(
            image_data=b"dummy_image_data",
            prompt=prompt,
            metadata={"model": self.model_name, **kwargs},
        )
