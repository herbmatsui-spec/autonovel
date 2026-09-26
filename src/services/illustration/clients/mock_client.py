"""疑似画像生成クライアント（CI / オフライン検証用）。

実 API を一切叩かずに PNG バイト列を返す。`UnifiedIllustrationGenerator` の
テスト・E2E では既定でこちらが選ばれるため、ネットワーク遮断下でも
生成経路の全体を検証できる。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from src.services.illustration.clients.base import GeneratedImage
from src.services.illustration.clients.gemini_image_client import _MOCK_PNG

logger = logging.getLogger(__name__)


class MockImageClient:
    """常に成功するダミークライアント。

    `name` は差し替え元のクライアント種別を名乗る（契約テストで
    「どのバックエンドが選ばれたか」を判定できるようにするため）。
    """

    def __init__(self, model_id: str = "mock", name: str = "mock") -> None:
        self.model_id = model_id
        self.name = name
        self.calls: list[dict] = []

    async def generate(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        aspect_ratio: str = "3:4",
        reference_images: Sequence[Path] = (),
        seed: int | None = None,
    ) -> GeneratedImage:
        self.calls.append(
            {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "aspect_ratio": aspect_ratio,
                "reference_count": len(reference_images),
                "seed": seed,
            }
        )
        return GeneratedImage(
            data=_MOCK_PNG,
            meta={
                "model_id": self.model_id,
                "client": self.name,
                "mock": True,
                "aspect_ratio": aspect_ratio,
                "prompt": prompt,
            },
        )


__all__ = ["MockImageClient"]
