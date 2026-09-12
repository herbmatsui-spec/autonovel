from typing import Any
from src.core.llm.unified_interface import IUnifiedLLMClient
from src.core.llm.adapters.mock_unified_client import UnifiedMockLLMClient

def create_unified_llm_client(provider_name: str, **kwargs: Any) -> IUnifiedLLMClient:
    if provider_name == "mock":
        return UnifiedMockLLMClient(**kwargs)
    # Add more providers later
    raise ValueError(f"Unknown provider: {provider_name}")
