"""
tests/unit/test_plot_variants.py - プロット複数案生成と選抜単体テスト
"""

import unittest
from unittest.mock import AsyncMock, MagicMock

from src.backend.workflows.nodes.plot_nodes import (
    evaluate_plot_node,
    generate_initial_plot_node,
    refine_plot_node,
)
from src.backend.workflows.state import PlotGraphState
from src.core.llm.providers.base import LLMResponse


class TestPlotVariants(unittest.IsolatedAsyncioTestCase):

    async def test_generate_multiple_plot_variants(self):
        """num_variants=2 で2回の生成呼び出しが行われ、plot_variants に2案保持されること"""
        mock_llm = MagicMock()
        mock_llm.generate_json = AsyncMock(
            side_effect=[
                LLMResponse(content='[{"ep_num": 1, "title": "案A"}]', success=True),
                LLMResponse(content='[{"ep_num": 1, "title": "案B"}]', success=True),
            ]
        )

        state: PlotGraphState = {
            "genre": "SF",
            "theme": "時間跳躍",
            "target_episodes": 1,
            "num_variants": 2,
        }

        res = await generate_initial_plot_node(state, llm_provider=mock_llm)

        self.assertEqual(mock_llm.generate_json.call_count, 2)
        self.assertEqual(len(res["plot_variants"]), 2)
        self.assertEqual(res["plot_variants"][0][0]["title"], "案A")
        self.assertEqual(res["plot_variants"][1][0]["title"], "案B")

    async def test_evaluate_and_select_highest_scoring_variant(self):
        """2案の評価でより高いスコア（案B: 0.92 > 案A: 0.70）が選抜され parsed_plots にセットされること"""
        mock_llm = MagicMock()
        mock_llm.generate_json = AsyncMock(
            side_effect=[
                # 案Aの評価: 0.70
                LLMResponse(content='{"is_approved": false, "score": 0.70, "issues": [], "suggestions": []}', success=True),
                # 案Bの評価: 0.92
                LLMResponse(content='{"is_approved": true, "score": 0.92, "issues": [], "suggestions": []}', success=True),
            ]
        )

        state: PlotGraphState = {
            "parsed_plots": [{"ep_num": 1, "title": "案A"}],
            "plot_variants": [
                [{"ep_num": 1, "title": "案A", "next_hook": "引きA"}],
                [{"ep_num": 1, "title": "案B(最高)", "next_hook": "引きB"}],
            ],
            "genre": "SF",
        }

        res = await evaluate_plot_node(state, llm_provider=mock_llm)

        self.assertEqual(mock_llm.generate_json.call_count, 2)
        self.assertEqual(res["parsed_plots"][0]["title"], "案B(最高)")
        self.assertEqual(res["quality_score"], 0.92)
        self.assertTrue(res["is_approved"])
        self.assertIn("alternative_ideas", res)
        self.assertEqual(len(res["alternative_ideas"]), 1)
        self.assertEqual(res["alternative_ideas"][0]["variant_num"], 1)

    async def test_refine_plot_incorporates_alternative_ideas(self):
        """他案のアイデアが refine_plot_node のプロンプトに統合されること"""
        mock_llm = MagicMock()
        mock_llm.generate_json = AsyncMock(
            return_value=LLMResponse(
                content='[{"ep_num": 1, "title": "案B(改良版)", "summary": "他案の引きを融合"}]',
                success=True,
            )
        )

        state: PlotGraphState = {
            "parsed_plots": [{"ep_num": 1, "title": "案B(最高)"}],
            "critique_feedback": "- テンポを改善してください。",
            "alternative_ideas": [
                {"variant_num": 1, "highlights": [{"ep": 1, "title": "案A", "hook": "強力な引きA"}]}
            ],
            "current_iteration": 1,
        }

        res = await refine_plot_node(state, llm_provider=mock_llm)

        mock_llm.generate_json.assert_called_once()
        call_prompt = mock_llm.generate_json.call_args[1]["prompt"]
        self.assertIn("他の生成案のアイデア", call_prompt)
        self.assertIn("強力な引きA", call_prompt)
        self.assertEqual(res["status"], "refined")
        self.assertEqual(res["parsed_plots"][0]["title"], "案B(改良版)")


if __name__ == "__main__":
    unittest.main()
