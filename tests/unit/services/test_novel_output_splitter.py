"""Unit tests for NovelOutputSplitter."""

import pytest
from src.services.prose.novel_output_splitter import NovelOutputSplitter


def test_split_standard_metadata():
    """Test splitting standard [METADATA_JSON] block."""
    raw = (
        "第1章の本文がここに入ります。\n"
        "主人公は剣を抜いた。\n\n"
        "---\n"
        "[METADATA_JSON]\n"
        "{\n"
        '  "episode_number": 1,\n'
        '  "foreshadowings": [\n'
        "    {\n"
        '      "foreshadowing_id": 101,\n'
        '      "action": "resolved",\n'
        '      "rationale": "ペンダントの秘密が明かされた",\n'
        '      "excerpt": "ペンダントが砕け散った"\n'
        "    }\n"
        "  ],\n"
        '  "word_count_estimate": 1500,\n'
        '  "unresolved_notes": []\n'
        "}\n"
        "[/METADATA_JSON]"
    )

    prose, metadata = NovelOutputSplitter.split_novel_output(raw)
    assert "第1章の本文がここに入ります。" in prose
    assert "主人公は剣を抜いた。" in prose
    assert "[METADATA_JSON]" not in prose
    assert metadata is not None
    assert metadata.episode_number == 1
    assert len(metadata.foreshadowings) == 1
    assert metadata.foreshadowings[0].foreshadowing_id == 101
    assert metadata.foreshadowings[0].action == "resolved"


def test_split_with_markdown_codeblock():
    """Test splitting when LLM wraps json in ```json code block."""
    raw = (
        "エピソード本文。\n\n"
        "[METADATA_JSON]\n"
        "```json\n"
        "{\n"
        '  "episode_number": 2,\n'
        '  "foreshadowings": [],\n'
        '  "word_count_estimate": 2000,\n'
        '  "unresolved_notes": ["伏線未回収"]\n'
        "}\n"
        "```\n"
        "[/METADATA_JSON]"
    )

    prose, metadata = NovelOutputSplitter.split_novel_output(raw)
    assert prose == "エピソード本文。"
    assert metadata is not None
    assert metadata.episode_number == 2
    assert metadata.unresolved_notes == ["伏線未回収"]


def test_no_metadata_present():
    """Test when no metadata block is present in output."""
    raw = "純粋な小説本文のみが出力された場合。"
    prose, metadata = NovelOutputSplitter.split_novel_output(raw)
    assert prose == "純粋な小説本文のみが出力された場合。"
    assert metadata is None


def test_malformed_json_fallback():
    """Test graceful handling of invalid JSON in metadata block."""
    raw = (
        "壊れたJSONを持つ本文。\n\n"
        "[METADATA_JSON]\n"
        "{ this is not valid json }\n"
        "[/METADATA_JSON]"
    )
    prose, metadata = NovelOutputSplitter.split_novel_output(raw)
    assert prose == "壊れたJSONを持つ本文。"
    assert metadata is None


def test_empty_input():
    """Test empty input handling."""
    prose, metadata = NovelOutputSplitter.split_novel_output("")
    assert prose == ""
    assert metadata is None
