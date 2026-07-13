import asyncio
import logging
from unittest.mock import MagicMock

from agents.audit import FastPlotScreener
from backend.engine_narrative import NarrativeController
from models.beat_sheet import BeatSheet, BeatSheetItem

logging.basicConfig(level=logging.INFO)

async def test_beat_sheet_audit():
    print("--- Testing audit_beat_sheet ---")
    engine = MagicMock()
    nc = NarrativeController(engine)

    # Valid beat sheet
    bs = BeatSheet(
        items=[
            BeatSheetItem(beat_number=1, description="主人公が新しい魔法を開発する。それは強大な威力を持つ。", character_focus=["主人公"]),
            BeatSheetItem(beat_number=2, description="魔法の代償として魔力を全て消費し、一時的に気を失う。", character_focus=["主人公"])
        ],
        summary="新しい魔法の開発と代償"
    )

    # World rules without magic cost taboo
    rules = {"magic_cost_and_taboo": "なし"}
    is_ok, reason = await nc.audit_beat_sheet(bs, rules)
    print(f"Test 1 (No cost constraint): Passed={is_ok}, Reason={reason}")
    assert is_ok is True

    # World rules with magic cost taboo
    rules = {"magic_cost_and_taboo": "魔法を使うと命が削られる"}
    # Violating beat sheet
    bs_violate = BeatSheet(
        items=[
            BeatSheetItem(beat_number=1, description="ノーコストで無限に魔法を乱射し、敵を撃退する。", character_focus=["主人公"])
        ],
        summary="無双劇"
    )
    is_ok, reason = await nc.audit_beat_sheet(bs_violate, rules)
    print(f"Test 2 (Violating cost constraint): Passed={is_ok}, Reason={reason}")
    assert is_ok is False

def test_screener_pick_best():
    print("--- Testing FastPlotScreener.pick_best ---")
    engine = MagicMock()
    screener = FastPlotScreener(engine)

    # Mock variants
    mock_std = MagicMock()
    mock_std.detailed_blueprint = "標準的な展開のプロット。3000文字以上にするための長いテキスト..." * 100
    mock_std._eval_score = 70

    mock_twist = MagicMock()
    mock_twist.detailed_blueprint = "急展開のプロット。まさかの裏切り..." * 200
    mock_twist._eval_score = 75


    variants = {
        "Standard": mock_std,
        "Twist": mock_twist
    }

    best_name, best_p_data = screener.pick_best(variants)
    # Standard: 80 + 10 (length) = 90
    # Twist: 75 + 15 (twist bonus) + 10 (length) = 100 -> Twist should win!
    print(f"Best variant selected: {best_name}")
    assert best_name == "Twist"

async def main():
    await test_beat_sheet_audit()
    test_screener_pick_best()
    print("All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())

