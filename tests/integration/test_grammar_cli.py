"""Integration tests for Grammar CLI."""

import json
from pathlib import Path
import pytest
from src.narrative_balancer.grammar.cli import main


def test_grammar_cli_execution(tmp_path):
    input_file = tmp_path / "beats.json"
    output_file = tmp_path / "balanced.json"
    dot_file = tmp_path / "forest.dot"
    md_file = tmp_path / "report.md"

    beats = [
        {"episode": i, "tension": 3.0, "beat_type": "DAILY"} for i in range(1, 21)
    ]
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(beats, f)

    ret = main([
        "--input", str(input_file),
        "--output", str(output_file),
        "--dot", str(dot_file),
        "--md", str(md_file),
    ])
    assert ret == 0
    assert output_file.exists()
    assert dot_file.exists()
    assert md_file.exists()

    with open(output_file, "r", encoding="utf-8") as f:
        balanced = json.load(f)
    assert len(balanced) == 20
