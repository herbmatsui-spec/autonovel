"""Mock Image Provider Adapter."""

from __future__ import annotations

from typing import Any

from src.core.spi.interface import IImageProvider, ImageResult


class MockImageProvider(IImageProvider):
    """Mock image provider for testing."""

    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs

    def generate_image(self, prompt: str, **kwargs: Any) -> ImageResult:
        """Generate a mock image result."""
        return ImageResult(
            image_data=b"mock_image_bytes",
            prompt=prompt,
            metadata={"mock": True, **kwargs},
        )
