"""Gemini 画像生成クライアント（既定: NanoBanana2Lite = gemini-3.1-flash-lite-image）。

`google.genai` による画像生成。1 枚生成・ネガティブプロンプト・縦横比・
キャラクター参照画像に対応する。API キーが無い／`mock_mode` の場合は
疑似 PNG を返して、オフライン検証（CI）まで含めて生成経路を成立させる。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Sequence

from src.services.illustration.clients.base import (
    GeneratedImage,
    PermanentClientError,
    TransientClientError,
)

logger = logging.getLogger(__name__)

# 疑似 PNG の最小バイト列（RGBA 1x1）
_MOCK_PNG = bytes(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class GeminiImageClient:
    """NanoBanana2Lite（既定モデル）用の画像生成クライアント。"""

    name = "gemini_image"

    def __init__(
        self,
        model_id: str = "gemini-3.1-flash-lite-image",
        api_key: str | None = None,
        mock_mode: bool = False,
        client: Any | None = None,
    ) -> None:
        self.model_id = model_id
        self.mock_mode = mock_mode
        self._api_key = api_key or self._resolve_api_key()
        self._client = client

    @staticmethod
    def _resolve_api_key() -> str:
        return (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_GENAI_API_KEY")
            or os.getenv("NANOBANANA_API_KEY")
            or ""
        )

    @property
    def client(self) -> Any | None:
        """`genai.Client` を遅延生成する。キーが無ければ mock へ自動的に退避する。"""
        if self._client is not None:
            return self._client
        if self.mock_mode or not self._api_key:
            logger.info("GeminiImageClient: no API key or mock_mode; using mock generation.")
            self.mock_mode = True
            return None
        try:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not initialize genai.Client (%s). Falling back to mock.", exc)
            self.mock_mode = True
            self._client = None
        return self._client

    async def generate(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        aspect_ratio: str = "3:4",
        reference_images: Sequence[Path] = (),
        seed: int | None = None,
    ) -> GeneratedImage:
        client = self.client
        if self.mock_mode or client is None:
            return self._generate_mock(prompt, aspect_ratio)

        try:
            from google.genai import types

            config_kwargs: dict[str, Any] = {
                "number_of_images": 1,
                "aspect_ratio": aspect_ratio,
            }
            if negative_prompt:
                config_kwargs["negative_prompt"] = negative_prompt
            if seed is not None:
                config_kwargs["seed"] = seed
            config_kwargs.update(self._build_reference_config(types, reference_images))

            config = types.GenerateImagesConfig(**config_kwargs)
            response = client.models.generate_images(
                model=self.model_id,
                prompt=prompt,
                config=config,
            )
        except Exception as exc:  # noqa: BLE001
            raise self._classify(exc) from exc

        if not getattr(response, "generated_images", None):
            raise TransientClientError("No images returned from the image model.")

        image = response.generated_images[0]
        data = getattr(getattr(image, "image", None), "image_bytes", None)
        if not data:
            raise TransientClientError("Response contained an empty image payload.")

        return GeneratedImage(
            data=data,
            meta={
                "model_id": self.model_id,
                "client": self.name,
                "aspect_ratio": aspect_ratio,
                "reference_count": len(reference_images),
            },
        )

    def _build_reference_config(self, types: Any, reference_images: Sequence[Path]) -> dict[str, Any]:
        """参照画像を SDK が対応する場合だけ設定へ足す（未対応は警告して無視）。"""
        existing = [p for p in reference_images if p and Path(p).exists()]
        if not existing:
            return {}
        try:
            ref_type = getattr(types, "ReferenceImage", None)
            ref_cfg_type = getattr(types, "ReferenceImageConfig", None)
            if ref_type is None or ref_cfg_type is None:
                raise AttributeError("ReferenceImage types are unavailable in this SDK version")
            items = [
                ref_type(
                    image=types.Image.from_file(str(p)),
                    config=ref_cfg_type(subject_type="character"),
                )
                for p in existing
            ]
            return {"reference_images": items}
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "reference_images are unsupported by the installed SDK (%s). "
                "Continuing without character consistency hints.",
                exc,
            )
            return {}

    @staticmethod
    def _classify(exc: Exception) -> Exception:
        """SDK 例外をリトライ可否で分類する。"""
        text = str(exc).lower()
        permanent_markers = (
            "invalid argument",
            "invalid_argument",
            "permission",
            "unauthenticated",
            "api key",
            "not found",
            "unsupported",
            "safety",
        )
        if any(marker in text for marker in permanent_markers):
            return PermanentClientError(str(exc))
        return TransientClientError(str(exc))

    def _generate_mock(self, prompt: str, aspect_ratio: str) -> GeneratedImage:
        logger.info("[MockMode] GeminiImageClient generating placeholder image.")
        return GeneratedImage(
            data=_MOCK_PNG,
            meta={
                "model_id": self.model_id,
                "client": self.name,
                "mock": True,
                "aspect_ratio": aspect_ratio,
                "prompt_chars": len(prompt),
            },
        )


__all__ = ["GeminiImageClient"]
