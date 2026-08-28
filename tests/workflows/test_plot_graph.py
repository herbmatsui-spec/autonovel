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

    async def test_plot_graph_with_unresolved_foreshadows(self):
        """未回収伏線（unresolved_foreshadows）をプロットに割り当てられることのテスト"""
        mock_llm = MagicMock()

        mock_llm.generate_json = AsyncMock(
            side_effect=[
                LLMResponse(
                    content='[{"ep_num": 1, "title": "光の石の謎", "summary": "石の秘密が明かされる", "next_hook": "敵の強襲", "assigned_foreshadows": ["胸元の光の石"]}]',
                    success=True,
                ),
                LLMResponse(
                    content='{"is_approved": true, "score": 0.9, "issues": [], "suggestions": []}',
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
            "unresolved_foreshadows": [
                {"id": "f-01", "ep": 1, "text": "胸元の光の石が突如として不吉な黒に染まる", "status": "未回収"}
            ],
        }

        result = await app.ainvoke(initial_state)

        self.assertIsNotNone(result)
        parsed = result.get("parsed_plots", [])
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].get("assigned_foreshadows"), ["胸元の光の石"])
        
        # プロンプトに未回収伏線が含まれていることを確認
        call_args_list = mock_llm.generate_json.call_args_list
        prompt_arg = call_args_list[0].kwargs.get("prompt")
        self.assertIn("胸元の光の石が突如として不吉な黒に染まる", prompt_arg)


if __name__ == "__main__":
    unittest.main()
