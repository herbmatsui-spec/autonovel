"""
Unit tests for Report Generation (Step 22).
"""

import pytest
from src.narrative.subtext_engine.engine import SubtextEngine
from src.narrative.subtext_engine.models import DialogueBlock


def test_detailed_report_generation():
    engine = SubtextEngine.create_default()
    blocks = [
        DialogueBlock(speaker="アリス", lines=["「ごめんなさい」"]),
        DialogueBlock(speaker="ボブ", lines=["「独り言さ」"]),
        DialogueBlock(speaker="チャーリー", lines=["ただの地の文です。"]),
    ]
    engine.process(blocks)
    report = engine.generate_report()

    assert report["total_blocks_processed"] == 3
    assert report["modified_blocks_count"] == 2
    assert report["modification_rate"] == pytest.approx(2 / 3, 0.01)
    assert report["rule_application_counts"]["rule_08_apology_deflection"] == 1
    assert report["rule_application_counts"]["rule_14_monologue_cutoff"] == 1
    assert "processing_time_ms" in report
    assert report["processing_time_ms"] >= 0.0
