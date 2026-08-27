"""
tests/unit/test_commercial_scoring.py - カクヨム商業スコアリングノード単体テスト
"""

import unittest
from unittest.mock import AsyncMock, MagicMock

from src.backend.workflows.nodes.review_nodes import score_commercial_node
from src.backend.workflows.state import ReviewGraphState
from src.core.llm.providers.base import LLMResponse


class TestCommercialScoring(unittest.IsolatedAsyncioTestCase):

    async def test_commercial_scoring_success_parsing(self):
        """ルービック5項目が正しくパースされ state に格納されること"""
        mock_llm = MagicMock()
        mock_llm.generate_json = AsyncMock(
            return_value=LLMResponse(
                content="""{
                    "commercial_score": 0.89,
                    "is_commercial_ok": true,
                    "breakdown": {
                        "opening_hook": 0.95,
                        "cadence_pull": 0.85,
                        "emotional_amplitude": 0.90,
                        "mystery_foreshadowing": 0.80,
                        "cliffhanger_tension": 0.95
                    },
                    "advice": ["テンポ良好"]
                }""",
                success=True,
            )
        )

        state: ReviewGraphState = {
            "ep_num": 1,
            "source_content": "商業小説の冒頭サンプル。主人公は覚醒した。",
        }

        res = await score_commercial_node(state, llm_provider=mock_llm)

        self.assertEqual(res["status"], "commercial_scored")
        self.assertAlmostEqual(res["commercial_score"], 0.89)
        self.assertIn("commercial_breakdown", res)
        breakdown = res.get("commercial_breakdown", {})
        self.assertAlmostEqual(breakdown.get("opening_hook", 0.0), 0.95)
        self.assertAlmostEqual(breakdown.get("cliffhanger_tension", 0.0), 0.95)

    async def test_commercial_scoring_fallback_without_llm(self):
        """llm_provider=None 時に安全なデフォルトスコアが返ること"""
        state: ReviewGraphState = {
            "ep_num": 1,
            "source_content": "テスト本文",
        }

        res = await score_commercial_node(state, llm_provider=None)

        self.assertEqual(res["status"], "commercial_scored")
        self.assertGreaterEqual(res["commercial_score"], 0.7)


if __name__ == "__main__":
    unittest.main()
