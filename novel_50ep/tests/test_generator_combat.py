"""Phase 5 結合テスト: generator と tracker の戦闘シーン連携 (ステップ 48)"""

import os
import pytest
from novel_50ep.generator import NovelGenerator
from novel_50ep.continuity_tracker import ContinuityTracker
from novel_50ep.scene_model import CombatScene


def test_generator_combat_integration():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)
    gen = NovelGenerator()

    # Generator で戦闘シーン生成
    s1 = gen.generate_combat_scene(id="c1", start=0, end=100, hp=100, mp=50, equipment=["光刃", "光の盾"])
    assert isinstance(s1, CombatScene)
    v1 = tracker.feed(s1)
    assert v1 == []

    # 次の戦闘シーンでHPが不正に増加
    s2 = gen.generate_combat_scene(id="c2", start=100, end=200, hp=120, mp=40, equipment=["光刃", "光の盾"])
    v2 = tracker.feed(s2)
    assert any(v["field"] == "hp" for v in v2)
