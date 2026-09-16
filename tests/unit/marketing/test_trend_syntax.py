"""
PLAN 01 - Step 2: トレンド構文抽出器の単体テスト
"""
from __future__ import annotations


from src.services.marketing.trend_syntax_extractor import extract_syntax_features


def test_extract_syntax_features_exile():
    """追放ざまぁパターンの抽出テスト"""
    title = "役立たずと追放された付与術師、実は世界唯一の神級エンチャンターでした"
    features = extract_syntax_features(title)
    assert features["syntax_type"] == "追放ざまぁ"
    assert "追放" in features["keywords"]
    assert features["char_count"] == len(title)
    assert features["has_contrast"] is True


def test_extract_syntax_features_misunderstanding():
    """勘違い無双パターンの抽出テスト"""
    title = "ただの田舎貴族ですが、なぜか周囲が世界最強の黒幕だと勘違いして崇めてきます"
    features = extract_syntax_features(title)
    assert features["syntax_type"] == "勘違い無双"
    assert "勘違い" in features["keywords"]
    assert features["has_contrast"] is True


def test_extract_syntax_features_optimal_length():
    """カクヨム推奨文字数 (35〜55字) の判定テスト"""
    title = "Sランク冒険者をクビになったので、辺境でスローライフを始めます〜実は万能料理スキル持ちでした〜"
    features = extract_syntax_features(title)
    assert 35 <= features["char_count"] <= 55
    assert features["is_optimal_length"] is True
