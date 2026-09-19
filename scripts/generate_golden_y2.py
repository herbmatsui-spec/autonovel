"""
Generate 50 golden samples for Subtext Template Library (PLAN_Y2 Step 21).
"""

import json
from pathlib import Path

GOLDEN_DIR = Path("tests/golden/templates")
GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

categories = ["betrayal", "grief", "power_play", "romance", "comedy", "action"]

emotions = [
    ("betrayal", "betrayal", "former_ally", "inferior"),
    ("grief", "grief", "lover", "equal"),
    ("contempt", "power_play", "rival", "superior"),
    ("affection", "romance", "partner", "equal"),
    ("tension", "comedy", "friend", "equal"),
    ("resolve", "action", "enemy", "equal"),
    ("anger", "betrayal", "enemy", "superior"),
    ("sadness", "grief", "family", "inferior"),
    ("pride", "power_play", "subordinate", "superior"),
    ("longing", "romance", "friend", "equal"),
]

test_cases = []
for i in range(50):
    emotion, exp_cat, rel, power = emotions[i % len(emotions)]
    cid = f"golden_template_{i+1:02d}"
    tc = {
        "id": cid,
        "context": {
            "scene_id": f"scene_{i // 5 + 1:03d}",
            "turn_index": i % 5,
            "speaker": f"Character_{i % 4}",
            "emotion": emotion,
            "relationship": rel,
            "power_dynamic": power,
            "intensity": "high" if i % 2 == 0 else "medium",
        },
        "expected_category": exp_cat,
    }
    test_cases.append(tc)

for tc in test_cases:
    fp = GOLDEN_DIR / f"{tc['id']}.json"
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(tc, f, ensure_ascii=False, indent=2)

print(f"Generated {len(test_cases)} golden template samples in {GOLDEN_DIR}")
