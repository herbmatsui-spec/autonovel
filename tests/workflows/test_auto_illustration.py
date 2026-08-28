"""
tests/workflows/test_auto_illustration.py - 感情ピーク自動イラスト生成ワークフローテスト
"""

import unittest
from unittest.mock import AsyncMock, MagicMock

from src.backend.workflows.graphs.writing_graph import compile_writing_graph
from src.backend.workflows.state import WritingGraphState
from src.core.llm.providers.base import LLMResponse
from src.models.illustration import IllustrationResult


class TestAutoIllustrationWorkflow(unittest.IsolatedAsyncioTestCase):

    async def test_auto_illustration_triggered_on_peak(self):
        """感情ピークが検出された際に auto_illustration_node が実行され、イラストが追加されること"""
        mock_llm = MagicMock()
        long_text = "決戦の時が来た。主人公は聖剣を構え、暗黒竜の心臓を貫いた。" * 100

        mock_llm.generate_text = AsyncMock(
            return_value=LLMResponse(content=long_text, success=True)
        )

        mock_llm.generate_json = AsyncMock(
            return_value=LLMResponse(
                content="""{
                    "is_integrity_ok": true,
                    "is_causal_ok": true,
                    "is_foreshadow_resolved": true,
                    "event_density": 0.9,
                    "score": 0.95,
                    "failures": [],
                    "detected_peaks": [
                        {
                            "scene_highlight": "主人公は聖剣を構え、暗黒竜の心臓を貫いた。",
                            "peak_reason": "暗黒竜との決戦と勝利",
                            "intensity": 0.95
                        }
                    ]
                }""",
                success=True,
            )
        )

        mock_illustration_agent = MagicMock()
        mock_illustration_result = IllustrationResult(
            request=MagicMock(),
            image_url="http://storage.example.com/illustrations/boss_fight.png",
            prompt="Epic dragon battle scene",
            model_used="imagen-3",
            generation_time_ms=500,
        )
        mock_illustration_agent.run = AsyncMock(
            return_value={"status": "success", "result": mock_illustration_result}
        )

        app = compile_writing_graph(
            llm_provider=mock_llm,
            illustration_agent=mock_illustration_agent,
        )

        initial_state: WritingGraphState = {
            "ep_num": 10,
            "passion": 1.0,
            "sys_inst": "テスト作家",
            "fw_prompt": "クライマックス第10話",
            "max_ac_iter": 1,
        }

        result = await app.ainvoke(initial_state)

        self.assertIsNotNone(result)
        self.assertIn("generated_illustrations", result)
        self.assertEqual(len(result["generated_illustrations"]), 1)
        self.assertEqual(
            result["generated_illustrations"][0]["image_url"],
            "http://storage.example.com/illustrations/boss_fight.png",
        )
        self.assertEqual(
            result["generated_illustrations"][0]["peak_reason"],
            "暗黒竜との決戦と勝利",
        )
        mock_illustration_agent.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
