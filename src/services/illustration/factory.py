import os

from .base import ImageGeneratorClient
from .dalle_client import DalleClient
from .mock_client import MockImageClient
from .sd_client import SDWebUIClient

_IMAGE_CLIENTS: dict[str, type[ImageGeneratorClient]] = {
    "mock": MockImageClient,
    "sd_webui": SDWebUIClient,
    "comfyui": lambda: None,
    "dalle3": DalleClient,
}


def get_image_client(provider: str | None = None) -> ImageGeneratorClient:
    if provider is None:
        provider = os.getenv("IMAGE_PROVIDER", "mock")
    if provider == "mock":
        return MockImageClient()
    elif provider == "sd_webui":
        base_url = os.getenv("SD_WEBUI_URL", "http://localhost:7860")
        return SDWebUIClient(base_url=base_url)
    elif provider == "dalle3":
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
        return DalleClient(api_key=api_key, base_url=base_url)
    else:
        raise ValueError(f"Unknown image provider: {provider}")


_cached_client: ImageGeneratorClient | None = None


def get_image_client_cached(provider: str | None = None) -> ImageGeneratorClient:
    global _cached_client
    if _cached_client is None:
        _cached_client = get_image_client(provider)
    return _cached_client