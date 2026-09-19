"""Integration tests for DSP CLI."""

import json
from pathlib import Path
import pytest
from src.narrative_balancer.dsp.cli import main


def test_cli_execution(tmp_path):
    input_file = tmp_path / "beats.json"
    output_file = tmp_path / "corrected.json"

    beats = [
        {"episode": i, "tension": 3.0 if 15 <= i <= 25 else 5.0, "beat_type": "SETUP"}
        for i in range(1, 41)
    ]
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(beats, f)

    ret = main(["--input", str(input_file), "--output", str(output_file)])
    assert ret == 0
    assert output_file.exists()

    with open(output_file, "r", encoding="utf-8") as f:
        corrected = json.load(f)
    assert len(corrected) == 40
