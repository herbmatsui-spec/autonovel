"""
src/services/erotic_diversity_score.py
官能多様性スコアリングモジュール。

このモジュールは、テキスト内の官能語彙の多様性を評価するための関数を提供します。
"""
import math
from collections import Counter
from typing import List

from config.erotic_thresholds import (
    DIVERSITY_SCORE_PASS,
    DIVERSITY_SCORE_WARN,
)


def compute_diversity_score(text: str, vocabulary_bank: List[str]) -> float:
    """
    テキスト中のボキャブラリー使用の多様性をエントロピーで算出する。0.0-1.0。

    閾値:
        - 0.5以上: 良好 (pass)
        - 0.3-0.5: 要改善 (warn)
        - 0.3未満: 不合格 (fail)

    See Also:
        classify_diversity(): 閾値による分類を行うユーティリティ
    """
    if not text or not vocabulary_bank:
        return 0.0

    # テキストに含まれる語彙を抽出
    found = [word for word in vocabulary_bank if word in text]
    if not found:
        return 0.0

    # 各語彙の出現回数をカウント
    counts = Counter(found)
    total = sum(counts.values())
    if total <= 1:
        return 0.0

    # シャノンエントロピーを計算
    entropy = -sum((count / total) * math.log2(count / total) for count in counts.values() if count > 0)
    # 最大エントロピー（すべての語彙が同じ頻度で現れる場合）
    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
    # 正規化（0.0〜1.0の範囲に収める）
    diversity = entropy / max_entropy if max_entropy > 0 else 0.0
    return min(1.0, diversity)

def classify_diversity(score: float) -> str:
    """多様性スコアを閾値に基づいて分類する。"""
    if score >= DIVERSITY_SCORE_PASS:
        return "pass"
    elif score >= DIVERSITY_SCORE_WARN:
        return "warn"
    else:
        return "fail"

def check_diversity(text: str, vocabulary_bank: list) -> dict:
    """スコア計算と分類を一度に行うユーティリティ。"""
    score = compute_diversity_score(text, vocabulary_bank)
    classification = classify_diversity(score)
    warnings = check_repetition(text, vocabulary_bank, max_repeat=3)
    return {
        "score": score,
        "classification": classification,
        "warnings": warnings,
    }

def check_repetition(text: str, vocabulary_bank: List[str], max_repeat: int = 3) -> List[str]:
    """語彙の過度な繰り返しをチェックし、警告メッセージのリストを返す。

    Args:
        text: チェック対象のテキスト
        vocabulary_bank: チェックする語彙のリスト
        max_repeat: 許容される最大繰り返し回数（デフォルト: 3）

    Returns:
        繰り返しが多い語彙ごとの警告メッセージのリスト
    """
    warnings = []
    for word in vocabulary_bank:
        count = text.count(word)
        if count >= max_repeat:
            warnings.append(f"'{word}' が {count} 回繰り返されています（上限: {max_repeat}回）")
    return warnings
