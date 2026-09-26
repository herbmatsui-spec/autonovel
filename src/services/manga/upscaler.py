"""【Deprecated Shim】統合アップスケーラへの委譲。

元: `src/services/manga/upscaler.py`
新: `src/services/illustration/upscaler.py`（全イラスト種別で共用）

旧 API（`MangaUpscaler.upscale(input, output_image_path=...)` と
出力先デフォルト `../upscaled/`）を保った薄いラッパ。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.services.illustration.upscaler import Upscaler as _UnifiedUpscaler

__all__ = ["MangaUpscaler"]


class MangaUpscaler:
    """旧 API 互換の超解像プロセッサ（内部は統合実装）。"""

    def __init__(
        self,
        scale_factor: int = 4,
        target_width: int = 4096,
        executable_path: Optional[str] = None,
    ):
        self.scale_factor = scale_factor
        self.target_width = target_width
        self.executable_path = executable_path
        self._upscaler = _UnifiedUpscaler(
            scale_factor=scale_factor,
            target_width=target_width,
            executable_path=executable_path,
        )

    def upscale(
        self,
        input_image_path: Path,
        output_image_path: Optional[Path] = None,
    ) -> Path:
        """旧既定（`raw_sheets/../upscaled/`）を維持したまま超解像する。"""
        input_path = Path(input_image_path)
        if output_image_path is None:
            output_image_path = (
                input_path.parent.parent / "upscaled" / f"upscaled_{input_path.name}"
            )
        return self._upscaler.upscale(input_path, output_image_path)


# 後方互換: 型名も公開しておく
Upscaler = MangaUpscaler
