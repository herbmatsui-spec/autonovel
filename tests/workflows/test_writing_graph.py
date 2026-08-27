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

        # ドラフト生成テキスト (1500文字以上)
        long_text = (
            "これは第1話のテスト本文です。主人公は静かに歩き始めた。風が草木を揺らし、遠くの街並みが夕暮れに染まっていく。新たな冒険の予感が胸を満たしていた。"
        ) * 40

        mock_llm.generate_text = AsyncMock(
            return_value=LLMResponse(
                content=long_text,
                success=True,
            )
        )

        # 監査JSONレスポンス
        mock_llm.generate_json = AsyncMock(
            return_value=LLMResponse(
                content='{"is_integrity_ok": true, "is_causal_ok": true, "event_density": 0.85, "score": 0.95, "failures": []}',
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
        self.assertGreaterEqual(result.get("event_density", 0.0), 0.5)
        self.assertGreaterEqual(result.get("quality_score", 0.0), 0.75)

    async def test_low_event_density_triggers_regeneration(self):
        """密度不足（event_density < 0.5）時に再生成ループが発動することを確認"""
        mock_llm = MagicMock()
        long_text = "事件密度の検証用テキストです。主人公が行動を開始します。" * 60

        mock_llm.generate_text = AsyncMock(
            side_effect=[
                LLMResponse(content=long_text, success=True),  # 初回ドラフト
                LLMResponse(content=long_text + "展開と緊張感を追加しました。", success=True),  # 再ドラフト
            ]
        )

        mock_llm.generate_json = AsyncMock(
            side_effect=[
                # 初回: 密度不足 (0.3)
                LLMResponse(
                    content='{"is_integrity_ok": true, "is_causal_ok": true, "event_density": 0.3, "score": 0.85, "failures": [{"category":"Density","description":"事件展開が希薄"}]}',
                    success=True,
                ),
                # 2回目: 密度合格 (0.8)
                LLMResponse(
                    content='{"is_integrity_ok": true, "is_causal_ok": true, "event_density": 0.8, "score": 0.90, "failures": []}',
                    success=True,
                ),
            ]
        )

        app = compile_writing_graph(llm_provider=mock_llm)
        initial_state: WritingGraphState = {
            "ep_num": 1,
            "passion": 0.8,
            "max_ac_iter": 2,
            "sys_inst": "テスト",
            "fw_prompt": "第1話",
        }

        result = await app.ainvoke(initial_state)

        self.assertEqual(mock_llm.generate_text.call_count, 2)
        self.assertEqual(mock_llm.generate_json.call_count, 2)
        self.assertGreaterEqual(result.get("event_density", 0.0), 0.5)
        self.assertEqual(result.get("ac_iter"), 2)


if __name__ == "__main__":
    unittest.main()
