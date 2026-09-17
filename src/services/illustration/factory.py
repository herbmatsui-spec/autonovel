"""画像生成クライアント＆アダプタファクトリ (v5.0 Step 5).

ComfyUIなどの自前常駐GPUサーバー依存を完全に撤廃し、
オンデマンドの外部従量APIアダプタ（fal.ai / DALL-E 3 / Mock）へ一本化する。
"""
from __future__ import annotations

import os
from typing import Optional

from .adapters.base import ImageGenerationAdapter
from .adapters.dalle3_adapter import Dalle3Adapter
from .adapters.fal_adapter import FalAiAdapter
from .adapters.mock_adapter import MockImageAdapter
from .base import ImageGeneratorClient
from .dalle_client import DalleClient
from .mock_client import MockImageClient
from .sd_client import SDWebUIClient


# ── v5.0 新画像生成アダプタファクトリ (外部従量API) ──

def get_image_adapter(provider: str | None = None) -> ImageGenerationAdapter:
    """外部従量APIベースの画像生成アダプタを取得する。

    自前GPU/ComfyUI常駐コンテナを廃止し、オンデマンドAPIへ一本化。
    指定プロバイダが不明な場合は安全にMockImageAdapterへフォールバックする。

    Args:
        provider: "mock", "dalle3" ("dalle", "openai"), "fal_ai" ("fal") など

    Returns:
        ImageGenerationAdapter 実装インスタンス
    """
    if provider is None:
        provider = os.getenv("IMAGE_PROVIDER", "mock").lower()
    else:
        provider = provider.lower()

    if provider == "mock":
        return MockImageAdapter()
    elif provider in ("dalle", "dalle3", "openai"):
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        return Dalle3Adapter(api_key=api_key, base_url=base_url)
    elif provider in ("fal", "fal_ai"):
        api_key = os.getenv("FAL_KEY", "") or os.getenv("FAL_AI_API_KEY", "")
        return FalAiAdapter(api_key=api_key)
    else:
        # 未知のプロバイダの場合は安全にMockへフォールバック
        return MockImageAdapter()


# ── 後方互換性レガシークライアント ──

def get_image_client(provider: str | None = None) -> ImageGeneratorClient:
    """旧インターフェース (ImageGeneratorClient) 互換用ファクトリ。"""
    if provider is None:
        provider = os.getenv("IMAGE_PROVIDER", "mock").lower()
    else:
        provider = provider.lower()

    if provider == "mock":
        return MockImageClient()
    elif provider == "sd_webui":
        base_url = os.getenv("SD_WEBUI_URL", "http://localhost:7860")
        return SDWebUIClient(base_url=base_url)
    elif provider in ("dalle", "dalle3"):
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
        return DalleClient(api_key=api_key, base_url=base_url)
    elif provider == "comfyui":
        # ComfyUI常駐サーバー廃止に伴いMockへフォールバック
        return MockImageClient()
    else:
        raise ValueError(f"Unknown image provider: {provider}")


_cached_client: ImageGeneratorClient | None = None


def get_image_client_cached(provider: str | None = None) -> ImageGeneratorClient:
    """旧インターフェース互換キャッシュ関数。"""
    global _cached_client
    if _cached_client is None:
        _cached_client = get_image_client(provider)
    return _cached_client
