"""既存 Imagen 経路のクライアントアダプタ（後方互換 / 切替候補）。

`src/services/image_service.py:ImageService` を内部に委譲するだけで
`ImageClientProtocol` を満たす。`IllustrationAgent(image_service=...)` の
旧コンストラクタ呼び出し（既存テスト・DI が使用）を壊さないために存在する。

generated image は既にファイルとして保存されているため、`GeneratedImage`
は `source_path` を保持し、`data` は空でもよい。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Sequence

from src.services.illustration.clients.base import (
    GeneratedImage,
    PermanentClientError,
    TransientClientError,
)

logger = logging.getLogger(__name__)


class LegacyImagenClient:
    """`ImageService` を包む Imagen クライアント。"""

    name = "legacy_imagen"

    def __init__(
        self,
        image_service: Any | None = None,
        model_id: str = "imagen-4.0-fast-generate-001",
    ) -> None:
        self._image_service = image_service
        self.model_id = model_id
        if image_service is not None:
            resolved = getattr(image_service, "default_model", None)
            if isinstance(resolved, str) and resolved:
                self.model_id = resolved

    @property
    def image_service(self) -> Any:
        """未注入なら既定の `ImageService` を遅延構築する。"""
        if self._image_service is None:
            from src.services.image_service import ImageService

            self._image_service = ImageService()
            if isinstance(self._image_service.default_model, str):
                self.model_id = self._image_service.default_model
        return self._image_service

    async def generate(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        aspect_ratio: str = "3:4",
        reference_images: Sequence[Path] = (),
        seed: int | None = None,
    ) -> GeneratedImage:
        # 参照画像と seed は ImageService の API 非対応のため渡さない。
        try:
            image_url = await self.image_service.generate(
                prompt=prompt,
                model=self.model_id,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
            )
        except Exception as exc:  # noqa: BLE001
            text = str(exc).lower()
            if any(m in text for m in ("invalid", "permission", "api key", "unsupported")):
                raise PermanentClientError(str(exc)) from exc
            raise TransientClientError(str(exc)) from exc

        path = self._url_to_path(image_url)
        return GeneratedImage(
            data=path.read_bytes() if path and path.exists() else b"",
            source_path=path,
            meta={
                "model_id": self.model_id,
                "client": self.name,
                "url": image_url,
            },
        )

    @staticmethod
    def _url_to_path(image_url: str | None) -> Path | None:
        """/static/illustrations/x.png 形式をローカル Path に変換する。"""
        if not image_url:
            return None
        raw = str(image_url).lstrip("/")
        if raw.startswith("static/"):
            return Path(raw)
        candidate = Path("static") / raw
        if candidate.exists():
            return candidate
        return Path(raw)


__all__ = ["LegacyImagenClient"]
