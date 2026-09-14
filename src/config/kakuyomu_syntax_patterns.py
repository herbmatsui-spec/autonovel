"""
カクヨム構文テンプレートおよびNG・パワーワード辞書
PLAN 01: タイトル＆あらすじCTR爆発エンジン
"""
from __future__ import annotations

# カクヨムで高CTRを叩き出す黄金構文テンプレート
KAKUYOMU_SYNTAX_TEMPLATES: list[str] = [
    "{disadvantage}と追放された{job}、実は{hidden_power}でした〜{benefit}で{happy_ending}〜",
    "【朗報】{disadvantage}で婚約破棄された私、{reversal}して幸せになりますので邪魔しないでください",
    "{loser_state}から始まる{unique_cheat}無双〜今更戻ってこいと言われてももう遅い〜",
    "Sランクパーティをクビになった{job}、拾われた先は{unexpected_group}でした",
    "無能だと処刑された元英雄、{reversal}して二度目の人生は好き勝手に生きる",
    "ただの{normal_job}ですが、なぜか周囲が{misunderstanding}して崇めてきます",
]

# CTR直撃パワーワード（タイトルに含まれるとクリック率が跳ね上がるキーワード）
CRITICAL_CTR_WORDS: list[str] = [
    "実は", "追放", "今更", "無自覚", "規格外", "ざまぁ", "チート", "万能",
    "神級", "クビ", "勘違い", "婚約破棄", "処刑", "役立たず", "最高峰", "世界唯一",
]

# カクヨム推奨文字数範囲（スマホ画面の2行表示に最適化: 30〜55字）
OPTIMAL_LENGTH_MIN: int = 30
OPTIMAL_LENGTH_MAX: int = 55
