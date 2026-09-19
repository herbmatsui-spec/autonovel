"""CLI for Grammar Narrative Balancer."""

import argparse
import json
import sys
from pathlib import Path
from typing import List

from src.narrative_balancer.grammar.balancer import GrammarNarrativeBalancer
from src.narrative_balancer.grammar.report import generate_cost_report
from src.narrative_balancer.grammar.visualize import parse_forest_to_dot
from src.narrative_balancer.models import Beat


def parse_args(args: List[str] = None):
    parser = argparse.ArgumentParser(
        prog="grammar-balance",
        description="Grammar & DP based narrative plot balancer and analyzer.",
    )
    parser.add_argument("--input", "-i", required=True, help="Input beats JSON file")
    parser.add_argument("--output", "-o", default=None, help="Output balanced beats JSON file")
    parser.add_argument("--dot", default=None, help="Output GraphViz DOT file path")
    parser.add_argument("--md", default=None, help="Output Markdown report file path")
    return parser.parse_args(args)


def main(argv: List[str] = None) -> int:
    args = parse_args(argv)

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Error: Input file not found: {in_path}", file=sys.stderr)
        return 1

    try:
        with open(in_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        beats = [Beat.model_validate(item) for item in raw]
    except Exception as e:
        print(f"Error loading beats: {e}", file=sys.stderr)
        return 2

    balancer = GrammarNarrativeBalancer()

    # 1. DOT export
    if args.dot:
        from src.narrative_balancer.grammar.beat_mapping import beat_to_terminal
        forest = balancer.dp_engine.parser.parse_prefix([beat_to_terminal(b) for b in beats])
        dot_str = parse_forest_to_dot(forest)
        dot_path = Path(args.dot)
        dot_path.parent.mkdir(parents=True, exist_ok=True)
        dot_path.write_text(dot_str, encoding="utf-8")
        print(f"Exported DOT to {dot_path}")

    # 2. Markdown report
    if args.md:
        analysis = balancer.analyze_only(beats)
        report_md = generate_cost_report(analysis)
        md_path = Path(args.md)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(report_md, encoding="utf-8")
        print(f"Exported report to {md_path}")

    # 3. Balancing output
    if args.output:
        corrected = balancer.balance(beats)
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump([b.model_dump() for b in corrected], f, indent=2, ensure_ascii=False)
        print(f"Balanced beats written to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
