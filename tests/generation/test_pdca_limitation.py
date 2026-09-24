"""
テスト: PDCAスリム化のリグレッションテスト（全文再生成ループ禁止・局所パッチ最大1回 の振る舞い保証）
"""
import unittest
from src.generation.pdca_controller import PDCAController

class TestPDcalimitation(unittest.TestCase):
    def test_full_regeneration_disabled_by_default(self):
        """Phase 3 ではデフォルトで全文再生成は禁止される"""
        controller = PDCAController()  # デフォルトコンストラクタ
        self.assertEqual(controller.max_regenerations, 0)
        self.assertFalse(controller.should_regenerate_full_text())

    def test_local_patch_limited_to_one(self):
        """局所パッチは最大1回まで許容される"""
        controller = PDCAController(max_local_patches=1)
        self.assertTrue(controller.can_do_local_patch())
        controller.record_local_patch()
        self.assertFalse(controller.can_do_local_patch())

if __name__ == '__main__':
    unittest.main()