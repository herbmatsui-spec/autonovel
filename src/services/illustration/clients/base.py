"""画像生成クライアントの抽象境界。

モデル差し替え（NanoBanana2Lite ⇄ Imagen ⇄ モック）による生成の違いを
ここに閉じ込めるための Protocol 定義。統合エンジン本体
（`UnifiedIllustrationGenerator`）はこの境界だけを書き、モデル ID を
直接持たない。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Protocol, Sequence, runtime_checkable


class ImageClientError(Exception):
    """画像生成クライアントの基底エラー。"""


class TransientClientError(ImageClientError):
    """一時的な失敗（ネットワーク・レート制限・5xx）。リトライ対象。"""


class PermanentClientError(ImageClientError):
    """恒久的な失敗（不正なプロンプト・認証・モデル未対応）。リトライ不要。"""


@dataclass
class GeneratedImage:
    """生成済み画像。

    Attributes:
        data: PNG バイト列。
        meta: クライアントごとの補足情報（model_id / url / mock フラグ 等）。
        source_path: クライアントが既にファイルへ書き出していた場合の元パス。
    """

    data: bytes = b""
    meta: Dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None

    @property
    def is_empty(self) -> bool:
        return not self.data and self.source_path is None


@runtime_checkable
class ImageClientProtocol(Protocol):
    """全クライアント実装が満たすべき契約。"""

    name: str
    model_id: str

    async def generate(
        self,
        prompt: str,
        *,
        negative_prompt: str = "",
        aspect_ratio: str = "3:4",
        reference_images: Sequence[Path] = (),
        seed: int | None = None,
    ) -> GeneratedImage:
        """1 枚の画像を生成する。

        Args:
            prompt: 生成プロンプト。
            negative_prompt: ネガティブプロンプト（未対応なら空文字を渡す）。
            aspect_ratio: "3:4" 等の縦横比。
            reference_images: キャラクター参照画像（未対応なら空のタプル）。
            seed: 再現性のためのシード（未対応なら None）。

        Raises:
            TransientClientError: リトライ価値のある失敗。
            PermanentClientError: リトライしても改善しない失敗。
        """
        ...


__all__ = [
    "GeneratedImage",
    "ImageClientError",
    "ImageClientProtocol",
    "PermanentClientError",
    "TransientClientError",
]
