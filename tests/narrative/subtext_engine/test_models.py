"""
Unit tests for data models (Step 2).
"""

import pytest
from src.narrative.subtext_engine.models import (
    DialogueBlock,
    RewriteResult,
    RewriteRuleModel,
    SubtextContext,
)


def test_dialogue_block_serialization():
    block = DialogueBlock(
        speaker="エレン",
        lines=["「どうして黙っているの？」", "「何か言ってよ」"],
        context={"emotion": "anxious"},
    )
    assert block.speaker == "エレン"
    assert len(block.lines) == 2
    assert block.raw_text() == "「どうして黙っているの？」\n「何か言ってよ」"

    cloned = block.clone()
    assert cloned.speaker == block.speaker
    assert cloned.lines == block.lines
    cloned.lines.append("「お願いだから」")
    assert len(block.lines) == 2
    assert len(cloned.lines) == 3


def test_subtext_context_defaults():
    ctx = SubtextContext(
        scene_id="scene_001",
        turn_index=2,
        speaker="カイン",
        target_speaker="リリア",
        emotion="betrayal",
        power_dynamic="inferior",
        relationship="former_ally",
    )
    assert ctx.scene_id == "scene_001"
    assert ctx.emotion == "betrayal"
    assert ctx.power_dynamic == "inferior"
    assert ctx.intensity == "medium"
    assert ctx.history_summary == []


def test_rewrite_rule_and_result_models():
    rule_model = RewriteRuleModel(
        id="test_rule",
        name="Test Rule",
        pattern=r"test",
        replacement="replaced",
        priority=50,
        final=True,
    )
    assert rule_model.id == "test_rule"
    assert rule_model.priority == 50
    assert rule_model.final is True

    block = DialogueBlock(speaker="A", lines=["test"])
    result = RewriteResult(success=True, modified=True, block=block, applied_rule_id="test_rule")
    assert result.success is True
    assert result.modified is True
    assert result.applied_rule_id == "test_rule"
