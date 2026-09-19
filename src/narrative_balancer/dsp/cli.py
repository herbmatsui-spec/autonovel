"""Command Line Interface for DSP Tension Balancer."""

import argparse
import json
import sys
from pathlib import Path
from typing import List

from src.narrative_balancer.dsp.factory import create_dsp_balancer
from src.narrative_balancer.dsp.models import Beat


def parse_args(args: List[str] = None):
    parser = argparse.ArgumentParser(
        prog="dsp-balance",
        description="DSP-based story tension balancer: detects sag and injects disaster impulse.",
    )
    parser.add_argument("--input", "-i", required=True, help="Path to input beats JSON file")
    parser.add_argument("--output", "-o", required=True, help="Path to write balanced beats JSON file")
    parser.add_argument("--config", "-c", default=None, help="Path to YAML configuration file")
    return parser.parse_args(args)


def main(argv: List[str] = None) -> int:
    args = parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}", file=sys.stderr)
        return 1

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        if isinstance(raw_data, dict) and "beats" in raw_data:
            beat_items = raw_data["beats"]
        elif isinstance(raw_data, list):
            beat_items = raw_data
        else:
            raise ValueError("Input JSON must be an array of beats or an object with 'beats' key")

        beats = [Beat.model_validate(item) for item in beat_items]
    except Exception as e:
        print(f"Error reading beats input: {e}", file=sys.stderr)
        return 2

    balancer = create_dsp_balancer(args.config)
    corrected_beats = balancer.correct(beats)

    try:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([b.model_dump() for b in corrected_beats], f, indent=2, ensure_ascii=False)

        print(f"Successfully balanced {len(beats)} beats. Output written to {output_path}")
        return 0
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
