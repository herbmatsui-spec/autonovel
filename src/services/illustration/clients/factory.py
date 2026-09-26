"""画像生成クライアントの組み立て（ClientFactory）。

モデルカタログ（`config/image_models.py`）の `client` フィールドに従い、
適切な `ImageClientProtocol` 実装を組み立てる。モデル差し替えはこの
ファクトリの選択のみで完結し、エンジン本体は影響を受けない。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config.image_models import (
    CLIENT_GEMINI_IMAGE,
    CLIENT_LEGACY_IMAGEN,
    CLIENT_MOCK,
    ImageModelSpec,
    get_image_model_spec,
)
from src.services.illustration.clients.base import ImageClientProtocol
from src.services.illustration.clients.gemini_image_client import GeminiImageClient
from src.services.illustration.clients.legacy_imagen_client import LegacyImagenClient
from src.services.illustration.clients.mock_client import MockImageClient

logger = logging.getLogger(__name__)


def build_client(
    model_key: str,
    *,
    api_key: str | None = None,
    mock_mode: bool = False,
    image_service: Any | None = None,
    client: Any | None = None,
) -> ImageClientProtocol:
    """モデルキーからクライアントを組み立てる。

    Args:
        model_key: `config.image_models` のカタログキー。
        api_key: Gemini 系 API キー（無ければ環境変数から解決）。
        mock_mode: 疑似生成を強制する。
        image_service: 既存の `ImageService`（Legacy 経路で使う）。
        client: テスト用に差し込む SDK クライアント。

    Returns:
        `ImageClientProtocol` を満たすクライアント。
    """
    spec: ImageModelSpec = get_image_model_spec(model_key)

    # 疑似生成時は、差し替え元クライアントの「名前」を保ったモックを返す
    # （契約テストが「どのバックエンドが選ばれたか」を判定できるようにする）。
    # mock 専用エントリ（`model_key="mock"`）のみ素の Mock になる。
    if spec.client == CLIENT_MOCK:
        return MockImageClient(model_id=spec.model_id)
    if mock_mode:
        return MockImageClient(model_id=spec.model_id, name=spec.client)

    if spec.client == CLIENT_LEGACY_IMAGEN:
        return LegacyImagenClient(image_service=image_service, model_id=spec.model_id)

    if spec.client == CLIENT_GEMINI_IMAGE:
        return GeminiImageClient(
            model_id=spec.model_id,
            api_key=api_key,
            mock_mode=mock_mode,
            client=client,
        )

    logger.warning(
        "Unknown client type %r for model key %r; using MockImageClient.",
        spec.client,
        spec.key,
    )
    return MockImageClient(model_id=spec.model_id, name=spec.client)


def build_client_from_spec(
    spec: ImageModelSpec,
    *,
    api_key: str | None = None,
    mock_mode: bool = False,
    image_service: Any | None = None,
    client: Any | None = None,
) -> ImageClientProtocol:
    """カタログ仕様オブジェクトからクライアントを組み立てる。"""
    return build_client(
        spec.key,
        api_key=api_key,
        mock_mode=mock_mode,
        image_service=image_service,
        client=client,
    )


def resolve_reference_paths(book_id: int, characters: list[str], ref_dir: Path) -> list[Path]:
    """キャラクター参照画像のパスを解決する（存在するものだけ返す）。"""
    found: list[Path] = []
    for name in characters or []:
        safe = str(name).strip().replace("/", "_").replace("\\", "_")
        if not safe:
            continue
        candidate = Path(ref_dir) / str(book_id) / f"{safe}.png"
        if candidate.exists():
            found.append(candidate)
    return found


__all__ = [
    "build_client",
    "build_client_from_spec",
    "resolve_reference_paths",
]
