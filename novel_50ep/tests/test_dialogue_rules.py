"""Phase 4 テスト: 会話シーンのルール検証 (ステップ 38)"""

import os
import pytest
from novel_50ep.scene_model import DialogueScene
from novel_50ep.continuity_tracker import ContinuityTracker


def test_dialogue_speakers_rule():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)

    # シーン1: 凛とセリア
    s1 = DialogueScene(id="d1", start=0, end=10, speakers=["凛", "セリア"], topics=["作戦会議"])
    v1 = tracker.feed(s1)
    assert v1 == []

    # シーン2: 凛とセリア (OK)
    s2 = DialogueScene(id="d2", start=10, end=20, speakers=["凛"], topics=["作戦会議"])
    v2 = tracker.feed(s2)
    assert v2 == []

    # シーン3: 前シーンにいないガルドが登場 (NG)
    s3 = DialogueScene(id="d3", start=20, end=30, speakers=["凛", "ガルド"], topics=["作戦会議"])
    v3 = tracker.feed(s3)
    assert any(v["field"] == "speakers" for v in v3)


def test_dialogue_topics_rule():
    rules_dir = os.path.join(os.path.dirname(__file__), "..", "continuity_rules")
    tracker = ContinuityTracker(rules_dir=rules_dir)

    s1 = DialogueScene(id="d1", start=0, end=10, speakers=["凛", "セリア"], topics=["潜入計画"])
    tracker.feed(s1)

    s2 = DialogueScene(id="d2", start=10, end=20, speakers=["凛", "セリア"], topics=["宴会"])
    v2 = tracker.feed(s2)
    assert any(v["field"] == "topics" for v in v2)
