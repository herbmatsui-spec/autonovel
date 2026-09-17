"""
erotic/density_controller.py - 官能描写密度の動的コントロール
"""

from __future__ import annotations


class EroticDensityController:
    """読者離脱防止のための官能描写密度コントロールクラス。"""

    def __init__(self, base_density: float = 0.3):
        self.base_density = base_density

    def get_target_density(self, current_chapter: int, reader_drop_risk: float) -> float:
        """
        現在の章と読者離脱リスクに基づいて目標密度を算出する。
        離脱リスクが高い場合、密度を引き上げる。
        """
        if reader_drop_risk > 0.5:
            adjustment = (reader_drop_risk - 0.5) * 0.5
            return min(1.0, self.base_density + adjustment)
        return self.base_density
