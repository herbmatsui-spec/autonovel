"""
tests/workflows/test_writing_graph.py - WritingGraph 単体テスト
"""

import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

from src.backend.workflows.graphs.writing_graph import compile_writing_graph
from src.backend.workflows.state import WritingGraphState
from src.core.llm.providers.base import LLMResponse


class TestWritingGraph(unittest.IsolatedAsyncioTestCase):

    async def test_writing_graph_compilation(self):
        """WritingGraph が正常に初期化・コンパイルできること"""
        graph = compile_writing_graph()
        self.assertIsNotNone(graph)

    async def test_writing_graph_execution_with_mock_llm(self):
        """モックLLMを用いた WritingGraph の Actor-Critic 実行テスト"""
        mock_llm = MagicMock()

        # ドラフト生成テキスト
        mock_llm.generate_text = AsyncMock(
            return_value=LLMResponse(
                content="これは第1話のテスト本文です。主人公は静かに歩き始めた。風が草木を揺らし、遠くの街並みが夕暮れに染まっていく。新たな冒険の予感が胸を満たしていた。",
                success=True,
            )
        )


        # 監査JSONレスポンス
        mock_llm.generate_json = AsyncMock(
            return_value=LLMResponse(
                content='{"is_integrity_ok": true, "is_causal_ok": true, "score": 0.95, "failures": []}',
                success=True,
            )
        )

        app = compile_writing_graph(llm_provider=mock_llm)

        initial_state: WritingGraphState = {
            "ep_num": 1,
            "passion": 0.8,
            "is_easy_mode": False,
            "sys_inst": "テストシステムプロンプト",
            "fw_prompt": "第1話本文",
            "max_ac_iter": 2,
        }

        result = await app.ainvoke(initial_state)

        self.assertIsNotNone(result)
        self.assertIn("draft_content", result)
        self.assertTrue(result.get("is_integrity_ok"))
        self.assertTrue(result.get("is_causal_ok"))
        self.assertGreaterEqual(result.get("quality_score", 0.0), 0.75)


if __name__ == "__main__":
    unittest.main()
