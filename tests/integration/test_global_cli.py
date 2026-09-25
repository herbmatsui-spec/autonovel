"""Integration tests for global-balance CLI."""

import json
from pathlib import Path
import pytest

pytest.importorskip("ortools")

from src.narrative_balancer.arbitrator.cli import main


def test_global_cli_execution(tmp_path):
    input_file = tmp_path / "plot.json"
    output_file = tmp_path / "balanced.json"
    report_file = tmp_path / "report.json"

    beats = [
        {"episode": i, "tension": 3.0 if 15 <= i <= 25 else 5.0, "beat_type": "DAILY" if 15 <= i <= 25 else "SETUP"}
        for i in range(1, 41)
    ]
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(beats, f)

    ret = main([
        "--input", str(input_file),
        "--output", str(output_file),
        "--report", str(report_file),
    ])
    assert ret == 0
    assert output_file.exists()
    assert report_file.exists()

    with open(output_file, "r", encoding="utf-8") as f:
        balanced = json.load(f)
    assert len(balanced) == 40
