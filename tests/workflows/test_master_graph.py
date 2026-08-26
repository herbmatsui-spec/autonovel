"""
tests/workflows/test_master_graph.py - MasterGraph 結合テスト
"""

import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

from src.backend.workflows.graphs.master_graph import compile_master_graph
from src.backend.workflows.state import MasterGraphState
from src.core.llm.providers.base import LLMResponse


class TestMasterGraph(unittest.IsolatedAsyncioTestCase):

    async def test_master_graph_compilation(self):
        """MasterGraph が正常に初期化・コンパイルできること"""
        graph = compile_master_graph()
        self.assertIsNotNone(graph)

    async def test_master_graph_full_pipeline_execution(self):
        """MasterGraph (Plot -> Writing -> Review) フルパイプラインの統合実行テスト"""
        mock_llm = MagicMock()

        # プロット生成 / 評価レスポンス
        mock_llm.generate_json = AsyncMock(
            side_effect=[
                # Plot initial
                LLMResponse(
                    content='[{"ep_num": 1, "title": "覚醒", "summary": "能力の覚醒", "next_hook": "敵の影"}]',
                    success=True,
                ),
                # Plot eval
                LLMResponse(
                    content='{"is_approved": true, "score": 0.95, "issues": [], "suggestions": []}',
                    success=True,
                ),
                # Writing audit
                LLMResponse(
                    content='{"is_integrity_ok": true, "is_causal_ok": true, "score": 0.90, "failures": []}',
                    success=True,
                ),
                # Review pacing
                LLMResponse(
                    content='{"pacing_score": 0.88, "is_pacing_ok": true, "issues": [], "recommendations": []}',
                    success=True,
                ),
                # Review character
                LLMResponse(
                    content='{"character_score": 0.92, "is_character_ok": true, "inconsistencies": []}',
                    success=True,
                ),
            ]
        )

        # 執筆テキスト生成
        mock_llm.generate_text = AsyncMock(
            return_value=LLMResponse(
                content="静寂を破るように雷鳴が轟いた。主人公の手のひらに未知の光が集い、世界を変える力が目覚めようとしていた。",
                success=True,
            )
        )

        mock_reporter = MagicMock()
        mock_reporter.report = AsyncMock()

        app = compile_master_graph(llm_provider=mock_llm, reporter=mock_reporter)

        initial_state: MasterGraphState = {
            "task_id": "test-task-123",
            "mode": "full_pipeline",
            "book_id": 1,
            "branch_id": 1,
            "target_start_ep": 1,
            "target_end_ep": 1,
            "metadata": {"genre": "バトルファンタジー", "theme": "覚醒"},
        }

        result = await app.ainvoke(initial_state)

        self.assertIsNotNone(result)
        self.assertIn("plot_result", result)
        self.assertIn("writing_results", result)
        self.assertIn("review_results", result)
        self.assertEqual(result.get("overall_progress"), 1.0)
        self.assertEqual(result.get("status"), "completed")


if __name__ == "__main__":
    unittest.main()
