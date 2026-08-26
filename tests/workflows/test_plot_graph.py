"""
tests/workflows/test_plot_graph.py - PlotGraph 単体テスト (unittest/pytest 兼用)
"""

import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

from src.backend.workflows.graphs.plot_graph import compile_plot_graph, create_plot_graph
from src.backend.workflows.state import PlotGraphState
from src.core.llm.providers.base import LLMResponse


class TestPlotGraph(unittest.IsolatedAsyncioTestCase):

    async def test_plot_graph_compilation(self):
        """PlotGraph が正常に初期化・コンパイルできること"""
        graph = compile_plot_graph()
        self.assertIsNotNone(graph)

    async def test_plot_graph_execution_with_mock_llm(self):
        """モックLLMを用いた PlotGraph の自己修正ループの実行テスト"""
        mock_llm = MagicMock()

        # 1回目: 初期プロット生成
        # 2回目: 評価 (score: 0.95, is_approved: True)
        mock_llm.generate_json = AsyncMock(
            side_effect=[
                LLMResponse(
                    content='[{"ep_num": 1, "title": "プロローグ", "summary": "旅の始まり", "next_hook": "謎の少女が現れる"}]',
                    success=True,
                ),
                LLMResponse(
                    content='{"is_approved": true, "score": 0.95, "issues": [], "suggestions": []}',
                    success=True,
                ),
            ]
        )

        app = compile_plot_graph(llm_provider=mock_llm)

        initial_state: PlotGraphState = {
            "genre": "ハイファンタジー",
            "theme": "英雄譚",
            "target_episodes": 1,
            "max_iterations": 2,
        }

        result = await app.ainvoke(initial_state)

        self.assertIsNotNone(result)
        self.assertEqual(len(result.get("parsed_plots", [])), 1)
        self.assertTrue(result.get("is_approved"))
        self.assertGreaterEqual(result.get("quality_score", 0.0), 0.8)


if __name__ == "__main__":
    unittest.main()
