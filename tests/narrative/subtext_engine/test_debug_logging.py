"""
Unit tests for debug logging and diff visualizer (Step 16).
"""

import json
import pytest
from pathlib import Path
from src.narrative.subtext_engine.engine import SubtextEngine
from src.narrative.subtext_engine.models import DialogueBlock


def test_debug_logging_to_jsonl(tmp_path):
    log_file = tmp_path / "subtext_debug.jsonl"
    engine = SubtextEngine.create_default(debug_mode=True)
    engine.debug_log_path = str(log_file)

    blocks = [
        DialogueBlock(speaker="キャラA", lines=["「私は悲しい」"]),
        DialogueBlock(speaker="キャラB", lines=["「絶対に殺してやる」"]),
    ]
    engine.process(blocks)

    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2

    record1 = json.loads(lines[0])
    assert record1["speaker"] == "キャラA"
    assert "diff" in record1
    assert "rules_applied" in record1
    assert "rule_02_emotion_to_action" in record1["rules_applied"]
