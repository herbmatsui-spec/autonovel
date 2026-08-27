"""Phase 3 テスト: 基本トラッカー動作検証 (ステップ 32)"""

import os
import tempfile
import pytest
from novel_50ep.scene_model import EroticScene
from novel_50ep.continuity_tracker import ContinuityTracker


def test_tracker_feed_and_violations():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)

    scene1 = EroticScene(id="e1", start=0, end=10, characters=["凛", "セリア"])
    v1 = tracker.feed(scene1)
    assert v1 == []
    assert len(tracker.violations) == 0

    scene2 = EroticScene(id="e2", start=10, end=20, characters=["凛", "ガルド"])
    v2 = tracker.feed(scene2)
    assert len(v2) == 1
    assert v2[0]["field"] == "characters"
    assert v2[0]["msg"] == "キャラ不一致"
    assert len(tracker.violations) == 1

    report_str = tracker.report()
    assert "characters: キャラ不一致" in report_str

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        tracker.save(tmp_path)
        assert os.path.exists(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    tracker.reset()
    assert tracker.prev is None
    assert tracker.violations == []
