"""Phase 6 結合テスト: generator と tracker の探索シーン連携 (ステップ 55)"""

import os
import pytest
from novel_50ep.generator import NovelGenerator
from novel_50ep.continuity_tracker import ContinuityTracker
from novel_50ep.scene_model import ExplorationScene


def test_generator_exploration_integration():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)
    gen = NovelGenerator()

    # Generator で探索シーン生成
    s1 = gen.generate_exploration_scene(id="x1", start=0, end=100, location="ルクス東区", items=["光導器"])
    assert isinstance(s1, ExplorationScene)
    v1 = tracker.feed(s1)
    assert v1 == []

    # 次の探索シーンで場所が突如変化
    s2 = gen.generate_exploration_scene(id="x2", start=100, end=200, location="深層迷宮", items=["光導器"])
    v2 = tracker.feed(s2)
    assert any(v["field"] == "location" for v in v2)
