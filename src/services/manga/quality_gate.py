"""【Deprecated Shim】統合品質ゲートへの委譲。

元: `src/services/manga/quality_gate.py`
新: `src/services/illustration/quality_gate.py`（全イラスト種別で共用）

実装は統合エンジン側へ一本化し、このモジュールは旧 API
（`MangaQualityGate.evaluate()` / `manga.models.QualityCheckResult`）を
保つ薄いラッパ。既存テストは変更なしで PASS する。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.services.illustration.quality_gate import QualityGate as _UnifiedQualityGate
from src.services.manga.models import QualityCheckResult

__all__ = ["MangaQualityGate"]


class MangaQualityGate:
    """旧 API 互換の品質ゲート（内部は統合実装）。"""

    def __init__(
        self,
        min_grid_score: float = 0.50,
        min_sharpness_score: float = 0.25,
        max_color_bleed_score: float = 0.25,
    ):
        self.min_grid_score = min_grid_score
        self.min_sharpness_score = min_sharpness_score
        self.max_color_bleed_score = max_color_bleed_score
        self._gate = _UnifiedQualityGate()

    def evaluate(self, image_path: Path) -> QualityCheckResult:
        """旧署名のまま評価結果を返す。"""
        result = self._gate.evaluate(
            image_path,
            thresholds={
                "min_grid_score": self.min_grid_score,
                "min_sharpness": self.min_sharpness_score,
                "max_color_bleed": self.max_color_bleed_score,
                # 漫画シートは最低 512px を要求する（旧仕様を維持）
                "min_resolution": 512,
            },
        )
        return QualityCheckResult(
            is_valid=result.is_valid,
            grid_score=result.grid_score,
            line_sharpness_score=result.line_sharpness_score,
            color_bleed_score=result.color_bleed_score,
            reasons=list(result.reasons),
        )


# 後方互換: 型名も公開しておく
QualityGate = MangaQualityGate
