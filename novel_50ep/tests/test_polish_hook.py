"""Phase 8 テスト: polish_tool と tracker のフック検証 (ステップ 64)"""

import os
import pytest
from novel_50ep.polish_tool import polish
from novel_50ep.continuity_tracker import ContinuityTracker
from novel_50ep.scene_model import CombatScene


def test_polish_hook_with_violations():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)

    # シーン1: 戦闘開始
    s1 = CombatScene(id="c1", start=0, end=10, hp=100, mp=50, equipment=["光刃"])
    tracker.feed(s1)

    # シーン2: HP不正回復 (違反発生)
    s2 = CombatScene(id="c2", start=10, end=20, hp=120, mp=40, equipment=["光刃"])

    raw_text = "光刃を構えて敵に立ち向かった。"
    result = polish(raw_text, scene=s2, tracker=tracker)

    assert "以下の矛盾を修正してください:" in result
    assert "hp: HPが回復行為なしで増加" in result
    assert "光刃を構えて敵に立ち向かった。" in result


def test_polish_hook_without_violations():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)

    s1 = CombatScene(id="c1", start=0, end=10, hp=100, mp=50, equipment=["光刃"])
    tracker.feed(s1)

    s2 = CombatScene(id="c2", start=10, end=20, hp=90, mp=40, equipment=["光刃"])
    raw_text = "光刃を構えて敵に立ち向かった。"
    result = polish(raw_text, scene=s2, tracker=tracker)

    assert "以下の矛盾を修正してください:" not in result
    assert "光刃を構えて敵に立ち向かった。" in result
