"""画像プロバイダ共通抽象 (Step 16).

Imagen, DALL-E, SD WebUI, ComfyUI を統一的に扱うインターフェースを定義する。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ImageProviderProtocol(Protocol):
    """画像生成プロバイダ共通プロトコル.

    実装は ``async def generate_image(prompt: str, ...) -> str`` を満たし、
    生成した画像の URL またはローカルパスを返すこと。
    """

    name: str

    async def generate_image(
        self,
        prompt: str,
        *,
        width: int = 1024,
        height: int = 1024,
        style: str | None = None,
        negative_prompt: str | None = None,
        **options: Any,
    ) -> str:
        """画像を生成し、URL またはローカルファイルパスを返す。

        Args:
            prompt: 生成用プロンプト。
            width: 画像の幅 (px)。
            height: 画像の高さ (px)。
            style: スタイル指定（例: "watercolor"）。
            negative_prompt: ネガティブプロンプト。
            **options: プロバイダ固有の追加オプション。

        Returns:
            生成した画像の URL またはローカルパス。

        Raises:
            ImageProviderError: プロバイダが利用不可または生成失敗時。
        """
        ...

    def is_available(self) -> bool:
        """プロバイダが現在利用可能かどうか（API キー、サーバー接続等）。"""
        ...


class ImageProviderError(Exception):
    """画像プロバイダの共通例外。"""


class BaseImageProvider:
    """ImageProviderProtocol の標準実装基底クラス."""

    name: str = "base"

    def __init__(self, **config: Any) -> None:
        self.config = config

    async def generate_image(
        self,
        prompt: str,
        *,
        width: int = 1024,
        height: int = 1024,
        style: str | None = None,
        negative_prompt: str | None = None,
        **options: Any,
    ) -> str:
        """デフォルト実装: 未実装プロバイダとして例外を送出。"""
        raise ImageProviderError(
            f"Image provider '{self.name}' does not implement generate_image()"
        )

    def is_available(self) -> bool:
        """デフォルト実装: 利用不可。"""
        return False
