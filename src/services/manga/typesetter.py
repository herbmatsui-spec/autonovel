"""【Deprecated Shim】統合写植处理器への委譲。

元: `src/services/manga/typesetter.py`
新: `src/services/illustration/typesetter.py`（全イラスト種別で共用）

旧 API（`MangaTypesetter(config=...)` / `apply_typesetting(...)` と
出力先デフォルト `../finalized/`）を保った薄いラッパ。
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

from src.services.illustration.typesetter import Typesetter as _UnifiedTypesetter
from src.services.manga.config import MangaPipelineConfig
from src.services.manga.models import SpeechBubble

__all__ = ["MangaTypesetter"]


class MangaTypesetter:
    """旧 API 互換の写植レンダラ（内部は統合実装）。"""

    def __init__(self, config: Optional[MangaPipelineConfig] = None):
        self.config = config or MangaPipelineConfig()
        self._typesetter = _UnifiedTypesetter(
            grid_cols=self.config.grid_cols,
            grid_rows=self.config.grid_rows,
            font_size=self.config.font_size,
            default_font_name=self.config.default_font_name,
        )

    def apply_typesetting(
        self,
        image_path: Path,
        dialogues: Sequence[SpeechBubble],
        output_path: Optional[Path] = None,
    ) -> Path:
        """指定セリフを該当コマに写植する。セリフ無しならコピーを返す。"""
        input_path = Path(image_path)
        if output_path is None:
            output_path = (
                input_path.parent.parent / "finalized" / f"typeset_{input_path.name}"
            )
        return self._typesetter.apply(input_path, dialogues, output_path)


# 後方互換: 型名も公開しておく
Typesetter = MangaTypesetter
