"""
トレンド構文抽出ロジック
PLAN 01: タイトル＆あらすじCTR爆発エンジン
"""
from __future__ import annotations

from typing import Any

from src.config.kakuyomu_syntax_patterns import (
    CRITICAL_CTR_WORDS,
    OPTIMAL_LENGTH_MAX,
    OPTIMAL_LENGTH_MIN,
)

EXILE_PATTERNS: list[str] = ["追放", "役立たず", "クビ", "追放された", "ゴミ扱い", "婚約破棄", "無能扱い"]
REVERSAL_PATTERNS: list[str] = ["実は", "本当は", "覚醒", "世界唯一", "規格外", "神級", "万能", "チート"]
MISUNDERSTANDING_PATTERNS: list[str] = ["勘違い", "崇め", "黒幕", "なぜか", "勝手に"]


def extract_syntax_features(title: str) -> dict[str, Any]:
    """タイトル文字列から構文パターン・キーワード・対比構造・最適文字数を抽出する."""
    char_count = len(title)
    is_optimal_length = OPTIMAL_LENGTH_MIN <= char_count <= OPTIMAL_LENGTH_MAX

    found_keywords = [w for w in CRITICAL_CTR_WORDS if w in title]

    has_exile = any(p in title for p in EXILE_PATTERNS)
    has_reversal = any(p in title for p in REVERSAL_PATTERNS)
    has_misunderstanding = any(p in title for p in MISUNDERSTANDING_PATTERNS)

    if has_exile and (has_reversal or "ざまぁ" in title or "〜" in title or "神級" in title):
        syntax_type = "追放ざまぁ"
    elif has_misunderstanding:
        syntax_type = "勘違い無双"
    elif has_reversal:
        syntax_type = "無自覚無双"
    else:
        syntax_type = "一般"

    has_contrast = (
        (has_exile and has_reversal)
        or has_misunderstanding
        or ("〜" in title and ("実は" in title or "今更" in title))
    )

    return {
        "syntax_type": syntax_type,
        "keywords": found_keywords,
        "char_count": char_count,
        "is_optimal_length": is_optimal_length,
        "has_contrast": has_contrast,
    }
