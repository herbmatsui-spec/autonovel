"""Unit tests for the CSP/SAT Narrative Balancer CLI."""

import json
from pathlib import Path

import pytest

from src.narrative_balancer.csp.cli import main, parse_args


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
        args = parse_args(["--state", "state.json", "--output", "out.json"])
        assert args.state == "state.json"
        assert args.output == "out.json"
        assert args.config is None

    def test_missing_required_exits(self):
        with pytest.raises(SystemExit):
            parse_args(["--state", "state.json"])


class TestMainErrors:
    def test_state_file_not_found(self, tmp_path: Path):
        rc = main([
            "--state", str(tmp_path / "missing.json"),
            "--output", str(tmp_path / "out.json"),
        ])
        assert rc == 1

    def test_invalid_format(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"unexpected": True}), encoding="utf-8")
        rc = main([
            "--state", str(bad),
            "--output", str(tmp_path / "out.json"),
        ])
        assert rc == 2

    def test_malformed_json(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json at all", encoding="utf-8")
        rc = main([
            "--state", str(bad),
            "--output", str(tmp_path / "out.json"),
        ])
        assert rc == 2


CFG_4 = (
    "n_episodes: 4\nmidpoint_episode: 2\nmidpoint_min_tension: 6\n"
    "all_is_lost_episode: 30\nall_is_lost_max_tension: 4\n"
    "climax_episode: 4\nclimax_min_tension: 6\n"
    "min_defeats: 0\nmax_defeats: 4\nmax_payoff_distance: 3\n"
    "weights:\n  smoothness: 1\n  char_balance: 1\n  quarter_target: 1\n"
    "solver:\n  max_time_seconds: 3.0\n  num_search_workers: 2\n"
)


class TestMainSuccess:
    def test_beats_list_input(self, tmp_path: Path):
        inp = tmp_path / "state.json"
        inp.write_text(json.dumps([_make_beat(i) for i in range(1, 5)]), encoding="utf-8")
        out = tmp_path / "out.json"
        cfg = tmp_path / "csp.yaml"
        cfg.write_text(CFG_4, encoding="utf-8")

        rc = main(["--state", str(inp), "--output", str(out), "--config", str(cfg)])
        assert rc == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 4

    def test_partial_state_dict_input(self, tmp_path: Path):
        inp = tmp_path / "state.json"
        payload = {"total_episodes": 4, "confirmed_beats": {"1": _make_beat(1)}, "unconfirmed_episodes": [2, 3, 4]}
        inp.write_text(json.dumps(payload), encoding="utf-8")
        out = tmp_path / "out.json"
        cfg = tmp_path / "csp.yaml"
        cfg.write_text(CFG_4, encoding="utf-8")

        rc = main(["--state", str(inp), "--output", str(out), "--config", str(cfg)])
        assert rc == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 4

    def test_solver_error_returns_3(self, tmp_path: Path):
        """Default config requires 40 episodes; a 4-beat input is infeasible -> rc 3."""
        inp = tmp_path / "state.json"
        inp.write_text(json.dumps([_make_beat(i) for i in range(1, 5)]), encoding="utf-8")
        out = tmp_path / "out.json"

        rc = main(["--state", str(inp), "--output", str(out)])
        assert rc == 3
