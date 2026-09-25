"""
テスト: Easy Mode フローのエンドツーエンドテスト
かんたんモードのパイプライン実行インターフェースおよびカスタム実行フックの挙動を検証する。
"""

import unittest
from unittest.mock import AsyncMock, MagicMock
from src.easy_mode.pipeline import EasyModePipeline
from src.shared.utils import StatusReporter


class TestEasyModeFlow(unittest.IsolatedAsyncioTestCase):
    async def test_easy_mode_pipeline_default_execution(self):
        """EasyModePipeline のデフォルト実行フローが正常に動作することを検証"""
        pipeline = EasyModePipeline()
        self.assertIsNotNone(pipeline._pipeline)

        reporter = MagicMock(spec=StatusReporter)
        result = await pipeline.execute(
            theme="勇者の目覚め",
            reporter=reporter,
            genre="fantasy",
        )

        self.assertEqual(result["status"], "done")
        self.assertEqual(result["theme"], "勇者の目覚め")
        self.assertIn("book_id", result)
        self.assertEqual(result["episodes"], 1)

    async def test_easy_mode_pipeline_custom_run_mock(self):
        """パイプラインのカスタム run フックが正しく呼び出されることを検証"""
        pipeline = EasyModePipeline()
        mock_run = AsyncMock(return_value={
            "status": "success",
            "episodes": [
                {"episode_number": 1, "title": "序章", "content": "冒険が始まる。"}
            ],
            "total_words": 1500,
        })
        pipeline.run = mock_run

        result = await pipeline.execute(theme="異世界転生")
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["episodes"]), 1)
        self.assertEqual(result["total_words"], 1500)
        mock_run.assert_called_once_with(theme="異世界転生")

    async def test_easy_mode_pipeline_error_handling(self):
        """パイプライン実行時エラーが適切にハンドリングされることを検証"""
        pipeline = EasyModePipeline()
        pipeline.run = AsyncMock(side_effect=RuntimeError("Pipeline failed"))

        with self.assertRaises(RuntimeError):
            await pipeline.execute(theme="失敗するテーマ")


if __name__ == '__main__':
    unittest.main()