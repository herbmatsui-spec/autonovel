"""Phase 6 テスト: 探索シーンのルール検証 (ステップ 53)"""

import os
import pytest
from novel_50ep.scene_model import ExplorationScene
from novel_50ep.continuity_tracker import ContinuityTracker


def test_exploration_items_subset():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)

    # シーン1: アイテム [光の鍵, 回復薬]
    s1 = ExplorationScene(id="x1", start=0, end=10, location="回廊", items=["光の鍵", "回復薬"])
    tracker.feed(s1)

    # シーン2: アイテムに新アイテム [魔導書] が突如出現 (subset違反)
    s2 = ExplorationScene(id="x2", start=10, end=20, location="回廊", items=["光の鍵", "回復薬", "魔導書"])
    v2 = tracker.feed(s2)
    assert any(v["field"] == "items" for v in v2)


def test_exploration_location_equals():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)

    s1 = ExplorationScene(id="x1", start=0, end=10, location="回廊入口", items=["光の鍵"])
    tracker.feed(s1)

    # 場所が説明なく変化
    s2 = ExplorationScene(id="x2", start=10, end=20, location="最深部", items=["光の鍵"])
    v2 = tracker.feed(s2)
    assert any(v["field"] == "location" for v in v2)
