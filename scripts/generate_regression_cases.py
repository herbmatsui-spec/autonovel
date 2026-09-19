"""Generate regression cases for DSP balancer."""

import json
from pathlib import Path


def generate_regression_cases(output_dir: str = "tests/fixtures/regression"):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Normal curve
    normal_beats = [
        {"episode": i, "tension": 4.0 + (i % 5) * 1.2, "beat_type": "SETUP"}
        for i in range(1, 41)
    ]
    with open(out / "normal_40ep.json", "w", encoding="utf-8") as f:
        json.dump(normal_beats, f, indent=2)

    # 2. Midpoint sag curve
    sag_beats = [
        {"episode": i, "tension": 3.0 if 15 <= i <= 25 else 6.0, "beat_type": "DAILY" if 15 <= i <= 25 else "BATTLE"}
        for i in range(1, 41)
    ]
    with open(out / "sag_20_30ep.json", "w", encoding="utf-8") as f:
        json.dump(sag_beats, f, indent=2)


if __name__ == "__main__":
    generate_regression_cases()
    print("Regression fixtures generated successfully.")
