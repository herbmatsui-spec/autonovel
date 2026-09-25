"""Integration tests for CSP CLI."""

import json
from pathlib import Path
import pytest
from src.narrative_balancer.csp.cli import main


def test_csp_cli_execution(tmp_path):
    input_file = tmp_path / "beats.json"
    output_file = tmp_path / "solved.json"

    beats = [
        {"episode": 1, "tension": 4.0, "beat_type": "SETUP"},
        {"episode": 10, "tension": 8.0, "beat_type": "MIDPOINT_DISASTER"},
        {"episode": 20, "tension": 9.0, "beat_type": "CLIMAX"},
    ]
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(beats, f)

    # Use a small 20-episode test config
    cfg_file = tmp_path / "cfg.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        f.write("n_episodes: 20\nmidpoint_episode: 10\nclimax_episode: 20\n")

    ret = main(["--state", str(input_file), "--output", str(output_file), "--config", str(cfg_file)])
    assert ret == 0
    assert output_file.exists()

    with open(output_file, "r", encoding="utf-8") as f:
        solved = json.load(f)
    assert len(solved) == 20
