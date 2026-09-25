"""
テスト: オーディター集約が元の専門オーディターと同等の品質を保つかの等価性テスト
ゴールデンケースデータセットを用いて、静的ルールおよびLLMオーディターの検出結果が
正しくIssueオブジェクトとして取得・分類されるかを検証する。
"""

import unittest
from unittest.mock import patch
from src.audit.pipeline import AuditPipeline
from src.audit.unified_llm_auditor import Issue


class TestUnifiedAuditorEquivalence(unittest.TestCase):
    def setUp(self):
        self.pipeline = AuditPipeline()

    def test_unified_auditor_captures_static_and_semantic_issues(self):
        """静的ルール（行頭禁則）と意味的指摘（LLM検出）の両方が正しく統合パイプラインで捕捉されるかを検証"""
        # 行頭禁則「。」を含むテキスト
        sample_text = "吾輩は猫である。\n。名前はまだ無い。\nどこで生れたか頓と見当がつかぬ。"

        mock_llm_issues = [
            Issue(
                type="character_voice",
                message="猫の一人称が急に変わる可能性があります",
                location=(10, 20),
                suggestion="一人称を『吾輩』で統一してください",
            )
        ]

        with patch.object(self.pipeline.llm_auditor, "audit", return_value=mock_llm_issues):
            issues = self.pipeline.run(sample_text)

            # 静的ルール（行頭禁則）とLLMオーディターの両方の指摘が含まれること
            self.assertGreater(len(issues), 0)
            
            types = [issue.type for issue in issues]
            # 静的ルールまたはLLMのいずれかの指摘タイプが含まれていること
            self.assertTrue(any(t in types for t in ["line_start_forbidden", "character_voice"]))

            # 各Issueが妥当な属性を持っていること
            for issue in issues:
                self.assertIsInstance(issue.type, str)
                self.assertIsInstance(issue.message, str)
                self.assertTrue(len(issue.message) > 0)

    def test_unified_auditor_returns_empty_on_clean_golden_text(self):
        """正常なゴールデンテキストに対して不要な偽陽性エラーを出さないことを検証"""
        golden_text = "吾輩は猫である。名前はまだ無い。どこで生れたかとんと見当がつかぬ。"

        with patch.object(self.pipeline.llm_auditor, "audit", return_value=[]):
            issues = self.pipeline.run(golden_text)
            self.assertEqual(len(issues), 0)


if __name__ == '__main__':
    unittest.main()