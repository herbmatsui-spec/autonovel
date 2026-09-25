"""Unit tests for the Grammar Narrative Balancer CLI and helpers."""

import json
from pathlib import Path

import pytest

from src.narrative_balancer.grammar.cli import main, parse_args


def _make_beat(ep: int, tension: float = 5.0, beat_type: str = "SETUP") -> dict:
    return {
        "episode": ep,
        "tension": tension,
        "beat_type": beat_type,
        "title": f"Ep{ep}",
        "summary": "",
        "characters": ["Protagonist"],
        "is_defeat": False,
        "foreshadowing_setup": [],
        "foreshadowing_payoff": [],
    }


class TestParseArgs:
    def test_required_input(self):
        args = parse_args(["--input", "in.json"])
        assert args.input == "in.json"
        assert args.output is None
        assert args.dot is None
        assert args.md is None

    def test_all_flags(self):
        args = parse_args(["-i", "in.json", "-o", "out.json", "--dot", "g.dot", "--md", "r.md"])
        assert args.output == "out.json"
        assert args.dot == "g.dot"
        assert args.md == "r.md"

    def test_missing_input_exits(self):
        with pytest.raises(SystemExit):
            parse_args([])


class TestMain:
    def test_input_not_found(self, tmp_path: Path):
        rc = main(["--input", str(tmp_path / "missing.json")])
        assert rc == 1

    def test_malformed_json(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("{{", encoding="utf-8")
        rc = main(["--input", str(bad)])
        assert rc == 2

    def test_dot_export(self, tmp_path: Path):
        inp = tmp_path / "in.json"
        inp.write_text(json.dumps([_make_beat(i) for i in range(1, 9)]), encoding="utf-8")
        dot = tmp_path / "forest.dot"

        rc = main(["--input", str(inp), "--dot", str(dot)])
        assert rc == 0
        assert dot.exists()
        content = dot.read_text(encoding="utf-8")
        assert content.startswith("digraph")

    def test_md_report_export(self, tmp_path: Path):
        inp = tmp_path / "in.json"
        inp.write_text(json.dumps([_make_beat(i) for i in range(1, 9)]), encoding="utf-8")
        md = tmp_path / "report.md"

        rc = main(["--input", str(inp), "--md", str(md)])
        assert rc == 0
        assert md.exists()
        assert "Cost" in md.read_text(encoding="utf-8") or "cost" in md.read_text(encoding="utf-8")

    def test_balance_output(self, tmp_path: Path):
        inp = tmp_path / "in.json"
        beats = [_make_beat(i, tension=2.0, beat_type="STAGNATION") for i in range(1, 9)]
        inp.write_text(json.dumps(beats), encoding="utf-8")
        out = tmp_path / "nested" / "out.json"

        rc = main(["--input", str(inp), "--output", str(out)])
        assert rc == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 8
