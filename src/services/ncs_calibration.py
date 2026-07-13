"""
src/services/ncs_calibration.py
Narrative Coherence Scorer (NCS) モジュール。
"""
from typing import Any, Dict, List


class NarrativeCoherenceScorer:
    """ナラティブコヒーレンススコアラー。

    ストーリーの一貫性、キャラクターの連続性、テーマの統一性を評価し、
    官能コンテンツの多様性スコアの閾値をキャリブレーションする。
    """

    # 重みの合計は1.0になるように設定
    weights = {
        "plot_continuity": 0.4,
        "character_consistency": 0.3,
        "theme_unity": 0.3,
    }

    def calculate_ncs(self, plot_score: float, char_score: float, theme_score: float) -> float:
        """NCSスコアを計算する。

        Args:
            plot_score: プロット連続性スコア (0.0-1.0)
            char_score: キャラクター連続性スコア (0.0-1.0)
            theme_score: テーマ統一性スコア (0.0-1.0)

        Returns:
            重み付き平均のNCSスコア (0.0-1.0)
        """
        return (
            self.weights["plot_continuity"] * plot_score +
            self.weights["character_consistency"] * char_score +
            self.weights["theme_unity"] * theme_score
        )

    def calibrate_diversity_threshold(self, training_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """erotic_diversity_score の閾値を人間評価データから校正する。

        Args:
            training_data: List of {"score": float, "rating": int} where rating is 1-5 human rating

        Returns:
            {"threshold_pass": float, "threshold_warn": float}
        """
        if not training_data:
            return {"threshold_pass": 0.5, "threshold_warn": 0.3}

        # 人間評価が4以上のデータを "良好" とする
        good_scores = [d["score"] for d in training_data if d.get("rating", 0) >= 4]
        bad_scores = [d["score"] for d in training_data if d.get("rating", 0) < 4]

        if good_scores and bad_scores:
            # good と bad の境界線を閾値とする
            threshold_pass = (max(good_scores) + min(bad_scores)) / 2
            threshold_warn = threshold_pass * 0.6  # warn は pass の60%地点
        elif good_scores:
            threshold_pass = min(good_scores)
            threshold_warn = threshold_pass * 0.6
        else:
            threshold_pass = 0.5
            threshold_warn = 0.3

        return {
            "threshold_pass": threshold_pass,
            "threshold_warn": threshold_warn,
        }
