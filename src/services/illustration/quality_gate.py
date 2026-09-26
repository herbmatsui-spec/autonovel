"""統合イラスト生成向け品質ゲート。

`src/services/manga/quality_gate.py` を一般化して、全イラスト種別で使う
形式に拡張した。依存は **Pillow のみ**（`numpy` / `cv2` は使わない）。

重要な契約:
- 本ゲートは「品質を記録する」役割であり、**生成失敗を意味しない**。
- Pillow が無い環境では `skipped=True, is_valid=True` を返し縮退する。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class QualityEvaluation:
    """品質評価結果。"""

    is_valid: bool
    grid_score: float = 0.0
    line_sharpness_score: float = 0.0
    color_bleed_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    skipped: bool = False
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "grid_score": round(self.grid_score, 4),
            "line_sharpness_score": round(self.line_sharpness_score, 4),
            "color_bleed_score": round(self.color_bleed_score, 4),
            "reasons": list(self.reasons),
            "skipped": self.skipped,
            "metrics": dict(self.metrics),
        }


# 複数コマ（漫画シート）として扱う種別
MULTI_PANEL_TYPES = {"yonkoma", "manga_24panel"}


class QualityGate:
    """生成画像の品質を lightweight に評価する。"""

    def __init__(self, thresholds: Optional[Dict[str, float]] = None) -> None:
        self.thresholds: Dict[str, float] = {
            "min_grid_score": 0.0,
            "min_sharpness": 0.15,
            "max_color_bleed": 0.35,
            "min_resolution": 256,
        }
        if thresholds:
            self.thresholds.update(thresholds)

    def evaluate(
        self,
        image_path: Path | str,
        thresholds: Optional[Dict[str, float]] = None,
    ) -> QualityEvaluation:
        """画像を評価する。判定NGでも例外は投げない（呼び出し側で記録する）。"""
        limits = dict(self.thresholds)
        if thresholds:
            limits.update(thresholds)

        path = Path(image_path)
        if not path.exists() or path.stat().st_size == 0:
            return QualityEvaluation(
                is_valid=False,
                reasons=["Image file does not exist or is empty."],
                metrics={"path": str(path)},
            )

        try:
            from PIL import Image, ImageStat
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pillow unavailable; quality gate skipped (%s).", exc)
            return QualityEvaluation(
                is_valid=True,
                skipped=True,
                reasons=[f"Quality gate skipped (Pillow unavailable): {exc}"],
                metrics={"path": str(path)},
            )

        try:
            with Image.open(path) as img:
                width, height = img.size
                mode = img.mode

                # --- 解像度 ---
                min_res = int(limits.get("min_resolution", 256))
                if width < min_res or height < min_res:
                    return QualityEvaluation(
                        is_valid=False,
                        reasons=[f"Resolution too low: {width}x{height} (< {min_res})"],
                        metrics={"width": width, "height": height},
                    )

                # --- 色彩のにじみ（白黒マンガなら R≒G≒B） ---
                color_bleed = 0.0
                if mode in ("RGB", "RGBA"):
                    stat = ImageStat.Stat(img)
                    if len(stat.mean) >= 3:
                        r, g, b = stat.mean[0], stat.mean[1], stat.mean[2]
                        diff = (abs(r - g) + abs(g - b) + abs(b - r)) / 3.0
                        color_bleed = min(1.0, diff / 50.0)

                # --- 線画シャープネス / コントラスト ---
                grayscale = img.convert("L")
                stat_l = ImageStat.Stat(grayscale)
                std_dev = stat_l.stddev[0] if stat_l.stddev else 0.0
                sharpness = min(1.0, std_dev / 80.0)

                # --- グリッド構造スコア（簡易・区画ごとの明暗分散） ---
                grid_score = self._estimate_grid_score(grayscale)

        except Exception as exc:  # noqa: BLE001
            logger.warning("Quality check failed (%s). Permitting fallback.", exc)
            return QualityEvaluation(
                is_valid=True,
                reasons=[f"Checked with fallback: {exc}"],
                metrics={"path": str(path)},
            )

        reasons: List[str] = []
        if grid_score < float(limits.get("min_grid_score", 0.0)):
            reasons.append(f"Grid structure weak ({grid_score:.2f})")
        if sharpness < float(limits.get("min_sharpness", 0.0)):
            reasons.append(
                f"Sharpness/Contrast too low ({sharpness:.2f} < {limits['min_sharpness']})"
            )
        if color_bleed > float(limits.get("max_color_bleed", 1.0)):
            reasons.append(
                f"Color bleed too high ({color_bleed:.2f} > {limits['max_color_bleed']})"
            )

        return QualityEvaluation(
            is_valid=len(reasons) == 0,
            grid_score=grid_score,
            line_sharpness_score=sharpness,
            color_bleed_score=color_bleed,
            reasons=reasons,
            metrics={"width": width, "height": height, "mode": mode},
        )

    @staticmethod
    def _estimate_grid_score(grayscale_img: Any) -> float:
        """4x6 区画ごとにコントラスト変動があるかを見てグリッド構造スコアを出す。

        全コマに描画がある（標準偏差が十分にある）ほど 1.0 に近づく。
        依存を増やさないため Pillow のみを使う簡易版とする。
        """
        from PIL import ImageStat

        width, height = grayscale_img.size
        if width < 8 or height < 8:
            return 0.5
        cols, rows = 4, 6
        cell_w, cell_h = max(1, width // cols), max(1, height // rows)
        stds: List[float] = []
        for r in range(rows):
            for c in range(cols):
                box = (
                    c * cell_w,
                    r * cell_h,
                    min((c + 1) * cell_w, width),
                    min((r + 1) * cell_h, height),
                )
                cell = grayscale_img.crop(box)
                stat = ImageStat.Stat(cell)
                if stat.stddev:
                    stds.append(stat.stddev[0])
        if not stds:
            return 0.0
        # 全コマに描画がある = グリッドとして構造的に整っている
        populated = sum(1 for s in stds if s > 5.0) / len(stds)
        return round(populated, 4)


__all__ = ["MULTI_PANEL_TYPES", "QualityEvaluation", "QualityGate"]
