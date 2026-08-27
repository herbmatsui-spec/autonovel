"""
tests/unit/test_density_rubric.py - 事件密度・文字数ルービック単体テスト
"""

import unittest
from unittest.mock import AsyncMock, MagicMock

from src.backend.workflows.edges.writing_edges import check_audit_results
from src.backend.workflows.nodes.writing_nodes import MIN_DRAFT_CHARS, self_audit_node
from src.backend.workflows.state import WritingGraphState


class TestDensityRubric(unittest.IsolatedAsyncioTestCase):

    def test_min_draft_chars_constant(self):
        """MIN_DRAFT_CHARS が 1500 文字以上であること"""
        self.assertGreaterEqual(MIN_DRAFT_CHARS, 1500)

    async def test_short_draft_fails_without_llm(self):
        """1500文字未満の短ドラフトは LLM 呼び出しを行わず即座に audit_failed と判定されること"""
        mock_llm = MagicMock()
        mock_llm.generate_json = AsyncMock()

        state: WritingGraphState = {
            "ep_num": 1,
            "draft_content": "短すぎるドラフトです。",
        }

        res = await self_audit_node(state, llm_provider=mock_llm)

        mock_llm.generate_json.assert_not_called()
        self.assertEqual(res["status"], "audit_failed")
        self.assertFalse(res["is_integrity_ok"])
        self.assertFalse(res["is_causal_ok"])

    def test_density_edge_routing(self):
        """密度不足（< 0.5）時は再生成、密度合格（>= 0.5）時は終了にルーティングされること"""
        # 密度不足
        low_density_state: WritingGraphState = {
            "is_integrity_ok": True,
            "is_causal_ok": True,
            "event_density": 0.4,
            "ac_iter": 1,
            "max_ac_iter": 2,
        }
        self.assertEqual(check_audit_results(low_density_state), "generate_draft")

        # 密度合格
        pass_state: WritingGraphState = {
            "is_integrity_ok": True,
            "is_causal_ok": True,
            "event_density": 0.75,
            "quality_score": 0.85,
            "ac_iter": 1,
            "max_ac_iter": 2,
        }
        self.assertEqual(check_audit_results(pass_state), "__end__")


if __name__ == "__main__":
    unittest.main()
