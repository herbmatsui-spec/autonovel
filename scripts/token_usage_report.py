#!/usr/bin/env python3
"""
Step 21: Token usage statistics and dictionary coverage report (PLAN_Y3).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.narrative.subtext_tokens.expander import TokenExpander
from src.narrative.subtext_tokens.parser import TokenParser


def generate_usage_report(
    sample_texts: list[str],
    dict_path: Path = Path("data/subtext/tokens.yaml"),
) -> dict:
    expander = TokenExpander(dict_path=dict_path)
    counts: dict[str, int] = {}
    total_tokens = 0

    for txt in sample_texts:
        tokens = TokenParser.find_tokens(txt)
        for t in tokens:
            total_tokens += 1
            counts[t.raw] = counts.get(t.raw, 0) + 1

    return {
        "total_tokens_detected": total_tokens,
        "unique_tokens_count": len(counts),
        "token_frequencies": counts,
    }


def main() -> int:
    samples = [
        "「何の話だ」[BEAT:pause:short]「答えてくれ」[ACTION:hide_hands:trembling]",
        "[SUBTEXT:irony]「そう、勝手にすればいい」[GLANCE:away]",
        "「わかった」[PAUSE:breath]「それでいい」[IRONY:cold_acceptance]",
    ]
    report = generate_usage_report(samples)
    print("=== Token Usage & Coverage Report ===")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
