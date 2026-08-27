"""Phase 7 テスト: foreshadow_manager と tracker の連携検証 (ステップ 59)"""

import os
import pytest
from novel_50ep.foreshadow_manager import ForeshadowManager
from novel_50ep.continuity_tracker import ContinuityTracker
from novel_50ep.scene_model import DialogueScene


def test_foreshadow_manager_link():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    fsm = ForeshadowManager()
    fsm.foreshadows = [
        {"id": "f1", "scene_type": "dialogue", "field": "topics"},
    ]

    expects = fsm.get_expects()
    assert len(expects) == 1
    assert expects[0]["type"] == "dialogue"
    assert expects[0]["field"] == "topics"

    tracker = ContinuityTracker(rules_dir=rules_dir, expects=expects)

    s1 = DialogueScene(id="d1", start=0, end=10, speakers=["凛", "セリア"], topics=["封印解除"])
    tracker.feed(s1)

    # topicsが不一致のシーン
    s2 = DialogueScene(id="d2", start=10, end=20, speakers=["凛", "セリア"], topics=["日常会話"])
    v = tracker.feed(s2)
    assert any(item["field"] == "topics" for item in v)
