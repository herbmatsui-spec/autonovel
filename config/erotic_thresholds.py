"""
config/erotic_thresholds.py
官能関連のスコア閾値を定義する。
閾値は人間評価との照合により定期校正される。
"""
from typing import Final

# 多様性スコア閾値（erotic_diversity_score 戻り値 0.0-1.0）
DIVERSITY_SCORE_PASS: Final[float] = 0.5   # この値以上就是「良好」
DIVERSITY_SCORE_WARN: Final[float] = 0.3   # この値以上0.5未満は「要改善」
DIVERSITY_SCORE_FAIL: Final[float] = 0.3  # この値未満は「不合格」

# 強度閾値
INTENSITY_R15: Final[int] = 3           # R15相当（官能A）の下限
INTENSITY_SAFE_MAX: Final[int] = 2      # セーフティ範囲の上限
INTENSITY_EXTREME: Final[int] = 5       # 過激表現の下限

# afterglow 品質閾値
AFTERGLOW_MIN_PARAGRAPHS: Final[int] = 2    # 最低段落数
AFTERGLOW_MIN_CHARS: Final[int] = 400      # 最低文字数

# 衣装整合性閾値
MAX_CONSECUTIVE_PEAK_EPISODES: Final[int] = 2  # 連続ピーク話数の上限

__all__ = [
    "DIVERSITY_SCORE_PASS",
    "DIVERSITY_SCORE_WARN",
    "DIVERSITY_SCORE_FAIL",
    "INTENSITY_R15",
    "INTENSITY_SAFE_MAX",
    "INTENSITY_EXTREME",
    "AFTERGLOW_MIN_PARAGRAPHS",
    "AFTERGLOW_MIN_CHARS",
    "MAX_CONSECUTIVE_PEAK_EPISODES",
]
