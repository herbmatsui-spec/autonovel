"""Vector Store Provider Factory."""

from __future__ import annotations

from typing import Any, Optional

from src.core.spi.vector_store.chroma_adapter import ChromaVectorProvider
from src.core.spi.vector_store.interface import IVectorStoreProvider
from src.core.spi.vector_store.mock_adapter import MockVectorProvider


class VectorStoreFactory:
    """Factory for creating vector store provider instances."""

    def __init__(self, **kwargs: Any) -> None:
        self.default_kwargs = kwargs

    def create(self, provider_type: str = "mock", **kwargs: Any) -> IVectorStoreProvider:
        """Create a vector store provider instance."""
        merged_kwargs = {**self.default_kwargs, **kwargs}
        if provider_type.lower() == "chroma":
            return ChromaVectorProvider(**merged_kwargs)
        return MockVectorProvider(**merged_kwargs)
