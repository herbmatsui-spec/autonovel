"""
test_opening_booster_cliffhanger.py - 序盤1〜3話のクリフハンガー評価およびリライト指令生成テスト
"""
from __future__ import annotations


from src.models.opening_booster import CliffhangerType
from src.services.narrative.opening_booster_service import OpeningBoosterService


def test_opening_booster_peaceful_tail() -> None:
    service = OpeningBoosterService(target_eps=[1, 2, 3])
    tail = "そして主人公たちは平和に暮らしましたとさ。めでたしめでたし。"
    eval_result = service.evaluate_tail(1, tail)

    assert eval_result.requires_rewrite is True
    assert eval_result.hook_type == CliffhangerType.PEACEFUL

    directive = service.generate_rewrite_directive(eval_result)
    assert "序盤クリフハンガー強制リライト指令" in directive


def test_opening_booster_crisis_tail() -> None:
    service = OpeningBoosterService(target_eps=[1, 2, 3])
    tail = "背後から迫る殺気に気づいた瞬間、首筋に冷たい刃物が突きつけられた。「そこまでだ、異世界人」"
    eval_result = service.evaluate_tail(1, tail)

    assert eval_result.requires_rewrite is False
