#!/usr/bin/env python3
"""
Step 21: Analyze subtext rewrite rules for potential conflicts across sample dialogues.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.narrative.subtext_engine.engine import SubtextEngine
from src.narrative.subtext_engine.models import DialogueBlock


def get_sample_dialogues() -> list[DialogueBlock]:
    return [
        DialogueBlock(speaker="エレン", lines=["「私は悲しい。どうしてこんなことに……」"]),
        DialogueBlock(speaker="カイン", lines=["「絶対に殺してやる。なぜなら君が裏切ったからだ」"]),
        DialogueBlock(speaker="リリア", lines=["「はい。仰せの通りにいたします」"]),
        DialogueBlock(speaker="従者", lines=["「ごめんなさい、独り言さ」"]),
        DialogueBlock(speaker="敵将", lines=["「言いたいことはそれだけか？ 見ないでよ！」"]),
    ]


def main() -> int:
    engine = SubtextEngine.create_default()
    samples = get_sample_dialogues()
    conflicts = engine.detect_conflicts(samples)

    print(f"=== Subtext Rewrite Rule Conflict Analysis ===")
    print(f"Total test blocks analyzed: {len(samples)}")
    print(f"Total conflicts detected: {len(conflicts)}")

    for i, c in enumerate(conflicts, 1):
        print(f"\n[{i}] Speaker: {c['speaker']}")
        print(f"    Text: {c['text']}")
        print(f"    Conflicting Rules: {', '.join(c['matching_rules'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
