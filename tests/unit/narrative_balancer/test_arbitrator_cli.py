"""Unit tests for the Global Narrative Balancer Arbitrator CLI."""

import json
from pathlib import Path

import pytest

from src.narrative_balancer.arbitrator.cli import main, parse_args
from src.narrative_balancer.models import Beat


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
        assert args.report is None

    def test_optional_args(self):
        args = parse_args([
            "-i", "in.json", "-o", "out.json", "-c", "cfg.yaml", "-r", "rep.json",
        ])
        assert args.config == "cfg.yaml"
        assert args.report == "rep.json"

    def test_missing_required_exits(self):
        with pytest.raises(SystemExit):
            parse_args(["--input", "in.json"])


class TestMainErrors:
    def test_input_not_found_returns_1(self, tmp_path: Path):
        rc = main([
            "--input", str(tmp_path / "missing.json"),
            "--output", str(tmp_path / "out.json"),
        ])
        assert rc == 1

    def test_invalid_format_returns_2(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"unexpected": "shape"}), encoding="utf-8")
        rc = main([
            "--input", str(bad),
            "--output", str(tmp_path / "out.json"),
        ])
        assert rc == 2

    def test_malformed_json_returns_2(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("{ not json", encoding="utf-8")
        rc = main([
            "--input", str(bad),
            "--output", str(tmp_path / "out.json"),
        ])
        assert rc == 2


class TestMainSuccess:
    def test_beats_list_input_writes_output(self, tmp_path: Path):
        inp = tmp_path / "in.json"
        inp.write_text(json.dumps([_make_beat(i) for i in range(1, 5)]), encoding="utf-8")
        out = tmp_path / "nested" / "out.json"

        rc = main(["--input", str(inp), "--output", str(out)])
        assert rc == 0
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 4

    def test_plot_state_dict_input_writes_output(self, tmp_path: Path):
        inp = tmp_path / "in.json"
        payload = {"total_episodes": 4, "beats": [_make_beat(i) for i in range(1, 5)]}
        inp.write_text(json.dumps(payload), encoding="utf-8")
        out = tmp_path / "out.json"

        rc = main(["--input", str(inp), "--output", str(out)])
        assert rc == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 4

    def test_report_flag_writes_report(self, tmp_path: Path):
        inp = tmp_path / "in.json"
        inp.write_text(json.dumps([_make_beat(i) for i in range(1, 5)]), encoding="utf-8")
        out = tmp_path / "out.json"
        rep = tmp_path / "report.json"

        rc = main(["--input", str(inp), "--output", str(out), "--report", str(rep)])
        assert rc == 0
        assert rep.exists()
        report = json.loads(rep.read_text(encoding="utf-8"))
        assert "balanced_beats" in report
        assert "balancer_results" in report
