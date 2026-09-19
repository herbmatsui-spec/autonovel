"""Command line interface for the Global Narrative Balancer Arbitrator."""

import argparse
import json
import sys
from pathlib import Path
from typing import List

from src.narrative_balancer.arbitrator.balancer import GlobalNarrativeBalancer
from src.narrative_balancer.arbitrator.config import load_arbitrator_config
from src.narrative_balancer.arbitrator.models import PlotState
from src.narrative_balancer.models import Beat


def parse_args(args: List[str] = None):
    parser = argparse.ArgumentParser(
        prog="global-balance",
        description="Global Narrative Balancer: unified orchestration of DSP, CSP, and Grammar engines.",
    )
    parser.add_argument("--input", "-i", required=True, help="Input plot/beats JSON file")
    parser.add_argument("--output", "-o", required=True, help="Output balanced plot JSON file")
    parser.add_argument("--config", "-c", default=None, help="Arbitrator YAML configuration file")
    parser.add_argument("--report", "-r", default=None, help="Optional path to output JSON arbitration report")
    return parser.parse_args(args)


def main(argv: List[str] = None) -> int:
    args = parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 1

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, dict) and "beats" in raw:
            plot_state = PlotState.model_validate(raw)
        elif isinstance(raw, list):
            beats = [Beat.model_validate(item) for item in raw]
            plot_state = PlotState.from_beats(beats)
        else:
            raise ValueError("Invalid format: expected array of beats or PlotState object")

    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        return 2

    config = load_arbitrator_config(args.config)
    balancer = GlobalNarrativeBalancer(config=config)

    integrated = balancer.orchestrate(plot_state)

    try:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump([b.model_dump() for b in integrated.balanced_beats], f, indent=2, ensure_ascii=False)

        print(f"Successfully balanced plot. Generated {len(integrated.balanced_beats)} beats in {out_path}")
        print(f"Conflicts resolved: {len(integrated.conflicts)}, Total time: {integrated.total_elapsed_ms}ms")

        if args.report:
            rep_path = Path(args.report)
            rep_path.parent.mkdir(parents=True, exist_ok=True)
            with open(rep_path, "w", encoding="utf-8") as f:
                json.dump(integrated.model_dump(), f, indent=2, ensure_ascii=False)
            print(f"Arbitration report written to {rep_path}")

        return 0
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
