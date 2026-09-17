"""
PLAN 01 - Step 5: CTRスコアリングエンジンの単体テスト
"""
from __future__ import annotations


from src.services.marketing.ctr_scorer import score_title_ctr


def test_score_title_ctr_high_score():
    """追放ざまぁ＋対比＋最適文字数で高得点 (80点以上) になること"""
    title = "役立たずと追放された付与術師、実は世界唯一の神級エンチャンターでした"
    result = score_title_ctr(title)
    assert result["score"] >= 80.0
    assert result["char_count"] == len(title)
    assert "追放" in result["hooks"]
    assert "神級" in result["hooks"]
    assert result["is_optimal_length"] is True


def test_score_title_ctr_too_short():
    """短すぎるタイトルは減点されること"""
    title = "最強の勇者"
    result = score_title_ctr(title)
    assert result["score"] < 50.0
    assert result["is_optimal_length"] is False


def test_score_title_ctr_too_long():
    """長すぎるタイトル（80字超）は減点されること"""
    title = "俺はただの村人だったはずなのに気がついたら魔王を倒してしまっていて周囲の美少女たちから求婚されまくって困っている件について誰か助けてくれませんか本当に困っています"
    result = score_title_ctr(title)
    assert result["char_count"] > 70
    assert result["score"] < 65.0
