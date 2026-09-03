"""SPI (Service Provider Interface) base interfaces and data models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ImageResult:
    """Result of image generation."""

    image_data: bytes
    prompt: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class IImageProvider(ABC):
    """Interface for image generation providers."""

    @abstractmethod
    def generate_image(self, prompt: str, **kwargs: Any) -> ImageResult:
        """Generate an image from prompt."""
        ...
