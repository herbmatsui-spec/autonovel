"""
erotic/curve.py - 官能カーブ生成モジュール
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.agents.erotic.parameters import EroticParameters


class EroticPoint(BaseModel):
    """官能カーブの1点を表すモデル"""

    position: float  # 0.0-1.0 (シーン内の相対位置)
    intensity: float  # 0.0-100.0 (官能強度)


class EroticCurve:
    """官能の時間経過による変化を表すカーブ"""

    def __init__(self, points: List[EroticPoint]):
        """
        Args:
            points: 官能カーブを構成する点のリスト（positionでソート済みであること）
        """
        if not points:
            raise ValueError("At least one point is required")

        # positionでソート
        self.points = sorted(points, key=lambda p: p.position)

        # 位置の�範�囲チェック
        for point in self.points:
            if not 0.0 <= point.position <= 1.0:
                raise ValueError(
                    f"Point position must be between 0.0 and 1.0, got {point.position}"
                )
            if not 0.0 <= point.intensity <= 100.0:
                raise ValueError(
                    f"Point intensity must be between 0.0 and 100.0, got {point.intensity}"
                )

    @classmethod
    def create_from_parameters(cls, params: "EroticParameters") -> "EroticCurve":
        """
        EroticParametersから官能カーブを生成するファクトリメソッド

        Args:
            params: パラメータオブジェクト

        Returns:
            生成されたEroticCurveインスタンス
        """
        # ここでは簡易的なカーブを生成
        # 実際の実装では、パラメータに基づいてより複�雑なカーブを生成する
        points = [
            EroticPoint(position=0.0, intensity=params.base_intensity * 0.3),
            EroticPoint(position=0.3, intensity=params.base_intensity * 0.7),
            EroticPoint(position=0.6, intensity=params.base_intensity),
            EroticPoint(position=1.0, intensity=params.base_intensity * 0.5),
        ]
        return cls(points)

    def get_intensity_at(self, position: float) -> float:
        """
        � 指定された位置での官能強度を線形補間で取得する

        Args:
            position: 0.0-1.0の相対位置

        Returns:
            その位置での官能強度 (0.0-100.0)
        """
        if not self.points:
            return 0.0

        if position <= self.points[0].position:
            return self.points[0].intensity
        if position >= self.points[-1].position:
            return self.points[-1].intensity

        # 線形補間
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            if p1.position <= position <= p2.position:
                # 線形補間
                ratio = (position - p1.position) / (p2.position - p1.position)
                return p1.intensity + ratio * (p2.intensity - p1.intensity)

        return self.points[-1].intensity  # フォールバック

    def get_peak_beat(self) -> Optional[EroticPoint]:
        """
        カーブのピーク（最高官能強度）点を取得する

        Returns:
            ピーク点、点が存在しない場合はNone
        """
        if not self.points:
            return None
        return max(self.points, key=lambda p: p.intensity)

    def get_average_intensity(self) -> float:
        """
        カーブの平均官能強度を取得する

        Returns:
            平均官能強度 (0.0-100.0)
        """
        if not self.points:
            return 0.0
        return sum(p.intensity for p in self.points) / len(self.points)


# 下位互�換性のためのエイリアス（将来的に�削除予定）
EroticCurveModel = EroticCurve
