"""Unit tests for the DSP Tension Balancer CLI."""

import json
from pathlib import Path

import pytest

from src.narrative_balancer.dsp.cli import main, parse_args


def _make_beat(ep: int, tension: float = 5.0) -> dict:
    return {
        "episode": ep,
        "tension": tension,
        "beat_type": "SETUP",
        "title": f"Ep{ep}",
        "summary": "",
        "characters": ["Protagonist"],
        "is_defeat": False,
        "foreshadowing_setup": [],
        "foreshadowing_payoff": [],
    }


class TestParseArgs:
    def test_required_args(self):
        args = parse_args(["--input", "in.json", "--output", "out.json"])
        assert args.input == "in.json"
        assert args.output == "out.json"
        assert args.config is None

    def test_missing_required_exits(self):
        with pytest.raises(SystemExit):
            parse_args(["--output", "out.json"])


class TestMainErrors:
    def test_input_not_found(self, tmp_path: Path):
        rc = main([
            "--input", str(tmp_path / "missing.json"),
            "--output", str(tmp_path / "out.json"),
        ])
        assert rc == 1

    def test_invalid_shape(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"no_beats_key": 1}), encoding="utf-8")
        rc = main([
            "--input", str(bad),
            "--output", str(tmp_path / "out.json"),
        ])
        assert rc == 2

    def test_malformed_json(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("}}}", encoding="utf-8")
        rc = main([
            "--input", str(bad),
            "--output", str(tmp_path / "out.json"),
        ])
        assert rc == 2


class TestMainSuccess:
    def test_beats_list_input(self, tmp_path: Path):
        inp = tmp_path / "in.json"
        inp.write_text(json.dumps([_make_beat(i) for i in range(1, 9)]), encoding="utf-8")
        out = tmp_path / "nested" / "out.json"

        rc = main(["--input", str(inp), "--output", str(out)])
        assert rc == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 8

    def test_object_with_beats_key(self, tmp_path: Path):
        inp = tmp_path / "in.json"
        payload = {"beats": [_make_beat(i) for i in range(1, 9)]}
        inp.write_text(json.dumps(payload), encoding="utf-8")
        out = tmp_path / "out.json"

        rc = main(["--input", str(inp), "--output", str(out)])
        assert rc == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 8

    def test_config_path_used(self, tmp_path: Path):
        inp = tmp_path / "in.json"
        inp.write_text(json.dumps([_make_beat(i, tension=2.0) for i in range(1, 9)]), encoding="utf-8")
        out = tmp_path / "out.json"
        cfg = tmp_path / "dsp.yaml"
        cfg.write_text(
            "window_size: 4\nflatness_threshold: 0.5\nlow_freq_ratio_threshold: 0.5\n",
            encoding="utf-8",
        )

        rc = main(["--input", str(inp), "--output", str(out), "--config", str(cfg)])
        assert rc == 0
