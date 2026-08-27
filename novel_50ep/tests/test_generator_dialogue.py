"""Phase 4 結合テスト: generator と tracker の会話シーン連携 (ステップ 40)"""

import os
import pytest
from novel_50ep.generator import NovelGenerator
from novel_50ep.continuity_tracker import ContinuityTracker
from novel_50ep.scene_model import DialogueScene


def test_generator_dialogue_integration():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)
    gen = NovelGenerator()

    # Generator で会話シーン生成
    s1 = gen.generate_dialogue_scene(id="d1", start=0, end=100, speakers=["凛", "セリア"], topics=["作戦"])
    assert isinstance(s1, DialogueScene)
    v1 = tracker.feed(s1)
    assert v1 == []

    # 次のシーンで話者が不連続に変わる
    s2 = gen.generate_dialogue_scene(id="d2", start=100, end=200, speakers=["凛", "ガルド"], topics=["作戦"])
    v2 = tracker.feed(s2)
    assert any(v["field"] == "speakers" for v in v2)
