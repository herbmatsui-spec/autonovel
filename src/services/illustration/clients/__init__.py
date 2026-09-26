"""画像生成クライアント境界（Client Adapters）。

- `base.py`   : `ImageClientProtocol` / `GeneratedImage` / 例外分類
- `factory.py`: モデルカタログからクライアントを組み立てる
- `gemini_image_client.py` : NanoBanana2Lite（既定）
- `legacy_imagen_client.py`: 既存 `ImageService` へのアダプタ（後方互換）
- `mock_client.py`         : 疑似生成（CI / オフライン）
"""

from src.services.illustration.clients.base import (
    GeneratedImage,
    ImageClientError,
    ImageClientProtocol,
    PermanentClientError,
    TransientClientError,
)
from src.services.illustration.clients.factory import (
    build_client,
    build_client_from_spec,
    resolve_reference_paths,
)
from src.services.illustration.clients.gemini_image_client import GeminiImageClient
from src.services.illustration.clients.legacy_imagen_client import LegacyImagenClient
from src.services.illustration.clients.mock_client import MockImageClient

__all__ = [
    "GeneratedImage",
    "GeminiImageClient",
    "ImageClientError",
    "ImageClientProtocol",
    "LegacyImagenClient",
    "MockImageClient",
    "PermanentClientError",
    "TransientClientError",
    "build_client",
    "build_client_from_spec",
    "resolve_reference_paths",
]
