"""Phase 5 テスト: 戦闘シーンのルール検証 (ステップ 46)"""

import os
import pytest
from novel_50ep.scene_model import CombatScene
from novel_50ep.continuity_tracker import ContinuityTracker


def test_combat_equipment_subset():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)

    # シーン1: 装備 [光刃, 盾]
    s1 = CombatScene(id="c1", start=0, end=10, hp=100, mp=50, equipment=["光刃", "盾"])
    tracker.feed(s1)

    # シーン2: 装備 [光刃, 盾, 弓] -> 前シーンにない装備が出現 (subset違反)
    s2 = CombatScene(id="c2", start=10, end=20, hp=90, mp=40, equipment=["光刃", "盾", "弓"])
    v2 = tracker.feed(s2)
    assert any(v["field"] == "equipment" for v in v2)


def test_combat_hp_no_increase():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)

    s1 = CombatScene(id="c1", start=0, end=10, hp=80, mp=50, equipment=["光刃"])
    tracker.feed(s1)

    # HPが80から90に不自然に増加
    s2 = CombatScene(id="c2", start=10, end=20, hp=90, mp=40, equipment=["光刃"])
    v2 = tracker.feed(s2)
    assert any(v["field"] == "hp" for v in v2)


def test_combat_mp_no_increase():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)

    s1 = CombatScene(id="c1", start=0, end=10, hp=80, mp=30, equipment=["光刃"])
    tracker.feed(s1)

    # MPが30から40に不自然に増加
    s2 = CombatScene(id="c2", start=10, end=20, hp=70, mp=40, equipment=["光刃"])
    v2 = tracker.feed(s2)
    assert any(v["field"] == "mp" for v in v2)
