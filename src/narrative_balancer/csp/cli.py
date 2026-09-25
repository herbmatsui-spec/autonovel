"""CLI for CSP/SAT Narrative Balancer."""

import argparse
import json
import sys
from pathlib import Path
from typing import List

from src.narrative_balancer.csp.balancer import CSPNarrativeBalancer
from src.narrative_balancer.csp.config import load_csp_config
from src.narrative_balancer.csp.partial_state import PartialPlotState
from src.narrative_balancer.models import Beat


def parse_args(args: List[str] = None):
    parser = argparse.ArgumentParser(
        prog="csp-balance",
        description="CSP/SAT-based story plot balancer using Google OR-Tools CP-SAT.",
    )
    parser.add_argument("--state", "-s", required=True, help="Path to partial plot state or beats JSON file")
    parser.add_argument("--output", "-o", required=True, help="Path to write solved/repaired beats JSON")
    parser.add_argument("--config", "-c", default=None, help="Path to YAML configuration file")
    return parser.parse_args(args)


def main(argv: List[str] = None) -> int:
    args = parse_args(argv)

    state_path = Path(args.state)
    if not state_path.exists():
        print(f"Error: File not found: {state_path}", file=sys.stderr)
        return 1

    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "confirmed_beats" in data:
            partial_state = PartialPlotState.model_validate(data)
        elif isinstance(data, list):
            beats = [Beat.model_validate(item) for item in data]
            partial_state = PartialPlotState.from_beats(beats)
        else:
            raise ValueError("Invalid format: expected array of beats or PartialPlotState JSON")

    except Exception as e:
        print(f"Error reading state: {e}", file=sys.stderr)
        return 2

    config = load_csp_config(args.config) if args.config else None
    balancer = CSPNarrativeBalancer(config=config)

    try:
        solved_beats = balancer.balance(partial_state)
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump([b.model_dump() for b in solved_beats], f, indent=2, ensure_ascii=False)

        print(f"Successfully balanced plot. Generated {len(solved_beats)} beats in {out_path}")
        return 0
    except Exception as e:
        print(f"Solver error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
