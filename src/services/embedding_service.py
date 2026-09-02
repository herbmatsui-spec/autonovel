"""テキスト埋め込み (Embedding) 取得サービスモジュール."""
from __future__ import annotations

import math
from typing import Any

from src.backend.config import settings
from src.backend.logging_config import get_logger

logger = get_logger("embedding_service")


class EmbeddingService:
    """OpenAI / 互換 API によるテキスト埋め込み生成サービス."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            if settings.OPENAI_API_KEY:
                from openai import OpenAI
                kwargs: dict[str, Any] = {"api_key": settings.OPENAI_API_KEY}
                if settings.OPENAI_BASE_URL:
                    kwargs["base_url"] = settings.OPENAI_BASE_URL
                self._client = OpenAI(**kwargs)
            else:
                self._client = None
        return self._client

    def get_embedding(self, text: str) -> list[float]:
        """指定されたテキストの 1536 次元ベクトルを取得する."""
        if not text or not text.strip():
            return [0.0] * 1536

        client = self._get_client()
        if client:
            try:
                response = client.embeddings.create(
                    input=text,
                    model=self.model_name,
                )
                return response.data[0].embedding
            except Exception as e:
                logger.warning("OpenAI Embedding API failed: %s. Using deterministic pseudo-embedding.", e)
                return self._generate_pseudo_embedding(text)
        else:
            return self._generate_pseudo_embedding(text)

    def _generate_pseudo_embedding(self, text: str, dimension: int = 1536) -> list[float]:
        """テストやAPIキー未設定環境用の決定論的疑似埋め込みベクトル (正規化済み)."""
        import hashlib
        # テキストのハッシュ値をシードにしてベクトルを生成
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        vec = []
        for i in range(dimension):
            val = math.sin(seed + i * 0.1)
            vec.append(val)
        # L2 正規化
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


embedding_service = EmbeddingService()

__all__ = ["EmbeddingService", "embedding_service"]
