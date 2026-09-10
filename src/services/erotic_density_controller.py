"""
src/services/erotic_density_controller.py
官能描写密度・強度制御コントローラー。

エピソード進行度に応じた官能強度の動的調整、連続ピーク抑制、平均強度管理を提供します。
"""

from __future__ import annotations

import logging
from typing import Sequence

logger = logging.getLogger(__name__)


class EroticDensityController:
    """官能シーンの配置頻度・強度・連続ピークを制御するクラス。"""

    def __init__(self, peak_threshold: int = 4, max_consecutive_peaks: int = 2) -> None:
        self.peak_threshold = peak_threshold
        self.max_consecutive_peaks = max_consecutive_peaks

    def should_allow_peak(
        self,
        history: Sequence[int],
        max_consecutive_peaks: int | None = None,
    ) -> bool:
        """直前のエピソード履歴から、新たなピーク（強度 >= peak_threshold）の配置を許可するか判定する。

        直近に連続してピークが発生している場合は過剰刺激・物語の緩急喪失を防ぐため False を返す。
        """
        limit = max_consecutive_peaks if max_consecutive_peaks is not None else self.max_consecutive_peaks
        if not history or limit <= 0:
            return True

        consecutive_peaks = 0
        for val in reversed(history):
            if val >= self.peak_threshold:
                consecutive_peaks += 1
            else:
                break

        return consecutive_peaks < limit

    def recommend_intensity(
        self,
        current_ep: int,
        total_eps: int,
        base_intensity: int = 3,
    ) -> int:
        """エピソードの物語進行度（序盤・中盤・終盤）に応じて推奨される官能強度を計算する。

        序盤（進行度 < 30%）: キャラクター関係構築前のため抑えめ (<= 2)
        終盤（進行度 > 75%）: クライマックスに向けて高強度推薦 (>= 4)
        中盤: ベース強度を中心とした調整
        """
        if total_eps <= 0:
            return max(0, min(5, base_intensity))

        progress = current_ep / total_eps

        if progress <= 0.3:
            # 序盤は低強度（最大2）
            recommended = min(base_intensity, 2)
        elif progress >= 0.75:
            # 終盤は高強度（最低4、最大5）
            recommended = max(base_intensity + 1, 4)
        else:
            recommended = base_intensity

        return max(0, min(5, recommended))

    def compute_avg_intensity(self, intensities: Sequence[int | float]) -> float:
        """エピソード群の平均官能強度を計算する。"""
        if not intensities:
            return 0.0
        return float(sum(intensities) / len(intensities))
