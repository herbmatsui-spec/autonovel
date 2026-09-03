"""Image Provider Factory."""

from __future__ import annotations

from typing import Any, Optional

from src.core.spi.image.genai_adapter import GenAIImageProvider
from src.core.spi.image.mock_adapter import MockImageProvider
from src.core.spi.interface import IImageProvider


class ImageProviderFactory:
    """Factory for creating image provider instances."""

    def __init__(self, **kwargs: Any) -> None:
        self.default_kwargs = kwargs

    def create(self, provider_type: str = "mock", **kwargs: Any) -> IImageProvider:
        """Create an image provider instance."""
        merged_kwargs = {**self.default_kwargs, **kwargs}
        if provider_type.lower() in ("genai", "imagen"):
            return GenAIImageProvider(**merged_kwargs)
        return MockImageProvider(**merged_kwargs)
