"""
tests/workflows/test_review_graph.py - ReviewGraph 単体テスト
"""

import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

from src.backend.workflows.graphs.review_graph import compile_review_graph
from src.backend.workflows.state import ReviewGraphState
from src.core.llm.providers.base import LLMResponse


class TestReviewGraph(unittest.IsolatedAsyncioTestCase):

    async def test_review_graph_compilation(self):
        """ReviewGraph が正常に初期化・コンパイルできること"""
        graph = compile_review_graph()
        self.assertIsNotNone(graph)

    async def test_review_graph_execution_with_mock_llm(self):
        """モックLLMを用いた ReviewGraph の実行テスト"""
        mock_llm = MagicMock()

        # 1回目: Pacing 分析
        # 2回目: Character 一貫性チェック
        mock_llm.generate_json = AsyncMock(
            side_effect=[
                LLMResponse(
                    content='{"pacing_score": 0.88, "is_pacing_ok": true, "issues": [], "recommendations": []}',
                    success=True,
                ),
                LLMResponse(
                    content='{"character_score": 0.92, "is_character_ok": true, "inconsistencies": []}',
                    success=True,
                ),
            ]
        )

        app = compile_review_graph(llm_provider=mock_llm)

        initial_state: ReviewGraphState = {
            "ep_num": 1,
            "source_content": "第1話の本文内容です。主人公は仲間と共にギルドを出発した。",
        }

        result = await app.ainvoke(initial_state)

        self.assertIsNotNone(result)
        self.assertIn("pacing_analysis", result)
        self.assertIn("character_consistency", result)
        self.assertFalse(result.get("requires_revision"))


if __name__ == "__main__":
    unittest.main()
