"""
Generate 40 golden samples for Subtext Token Expansion (PLAN_Y3 Step 17).
"""

import json
from pathlib import Path

GOLDEN_DIR = Path("tests/golden/token_expansion")
GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

test_cases = [
    {
        "id": "token_case_01",
        "raw": "「わかったよ」[BEAT:pause:short]「君の言う通りにする」",
        "expected_not_contains": ["[BEAT:pause:short]"],
        "expected_contains": ["「わかったよ」", "「君の言う通りにする」"],
    },
    {
        "id": "token_case_02",
        "raw": "「……」[ACTION:hide_hands:trembling]",
        "expected_not_contains": ["[ACTION:hide_hands:trembling]"],
        "expected_any": ["隠した", "押し込んだ"],
    },
    {
        "id": "token_case_03",
        "raw": "[SUBTEXT:irony]「それで、何用かしら？」",
        "expected_not_contains": ["[SUBTEXT:irony]"],
        "expected_contains": ["「……"],
    },
    {
        "id": "token_case_04",
        "raw": "「お前など[GLANCE:away]顔も見たくない」",
        "expected_not_contains": ["[GLANCE:away]"],
        "expected_any": ["逸らす", "横を向"],
    },
    {
        "id": "token_case_05",
        "raw": "「もう終わりだ」[PAUSE:breath]",
        "expected_not_contains": ["[PAUSE:breath]"],
        "expected_any": ["深く息を吐く", "静かに息を呑む"],
    },
    {
        "id": "token_case_06",
        "raw": "「承知しました」[IRONY:cold_acceptance]",
        "expected_not_contains": ["[IRONY:cold_acceptance]"],
        "expected_contains": ["「……"],
    },
    {
        "id": "token_case_07",
        "raw": "「絶対に許さない」[INTERNAL:suppressed_rage]",
        "expected_not_contains": ["[INTERNAL:suppressed_rage]"],
        "expected_contains": ["（胸の奥で煮え滾る怒気を必死に抑え込む）"],
    },
]

# Add systematic variations to reach 40 cases
for i in range(8, 41):
    tokens = [
        "[BEAT:pause:short]",
        "[BEAT:pause:long]",
        "[ACTION:hide_hands:trembling]",
        "[GLANCE:away]",
        "[PAUSE:breath]",
        "[SUBTEXT:irony]",
    ]
    tok = tokens[i % len(tokens)]
    tc = {
        "id": f"token_case_{i:02d}",
        "raw": f"「テスト発言 {i}」{tok}「続く発言」",
        "expected_not_contains": [tok],
        "expected_contains": [f"「テスト発言 {i}」"],
    }
    test_cases.append(tc)

for tc in test_cases:
    fp = GOLDEN_DIR / f"{tc['id']}.json"
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(tc, f, ensure_ascii=False, indent=2)

print(f"Generated {len(test_cases)} golden token samples in {GOLDEN_DIR}")
