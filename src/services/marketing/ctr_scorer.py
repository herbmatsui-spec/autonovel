"""
CTRスコアリングエンジン
PLAN 01: タイトル＆あらすじCTR爆発エンジン
"""
from __future__ import annotations

from typing import Any

from src.config.kakuyomu_syntax_patterns import (
    CRITICAL_CTR_WORDS,
    OPTIMAL_LENGTH_MAX,
    OPTIMAL_LENGTH_MIN,
)
from src.services.marketing.trend_syntax_extractor import extract_syntax_features


def score_title_ctr(title: str) -> dict[str, Any]:
    """
    カクヨム読者のクリック傾向（CTR）に基づき、タイトルを0〜100点で採点する。

    採点要素:
    1. 文字数配分 (スマホ2行最適 35〜55字)
    2. パワーワード含有度
    3. 対比・カタルシス構造
    4. 記号装飾 (〜, 【】, …)
    """
    clean_title = title.strip()
    char_count = len(clean_title)
    features = extract_syntax_features(clean_title)

    score = 20.0  # ベーススコア

    # 1. 文字数スコア (最大30点)
    if OPTIMAL_LENGTH_MIN <= char_count <= OPTIMAL_LENGTH_MAX:
        length_score = 30.0
    elif 20 <= char_count < OPTIMAL_LENGTH_MIN or OPTIMAL_LENGTH_MAX < char_count <= 65:
        length_score = 15.0
    elif char_count < 20:
        length_score = 0.0
    else:  # 65字超
        length_score = max(0.0, 10.0 - (char_count - 65) * 0.8)

    score += length_score

    # 2. パワーワードスコア (最大25点)
    found_keywords = features["keywords"]
    keyword_score = min(25.0, len(found_keywords) * 10.0)
    score += keyword_score

    # 3. 対比・カタルシス構造スコア (最大20点)
    contrast_score = 20.0 if features["has_contrast"] else 5.0
    score += contrast_score

    # 4. 記号・可読性スコア (最大5点)
    symbol_score = 0.0
    if "〜" in clean_title or "～" in clean_title:
        symbol_score += 3.0
    if "【" in clean_title and "】" in clean_title:
        symbol_score += 2.0
    score += symbol_score

    # スコアの丸め (0.0 - 100.0)
    final_score = max(0.0, min(100.0, round(score, 1)))

    return {
        "title": clean_title,
        "score": final_score,
        "char_count": char_count,
        "is_optimal_length": features["is_optimal_length"],
        "syntax_type": features["syntax_type"],
        "hooks": found_keywords,
        "has_contrast": features["has_contrast"],
    }
