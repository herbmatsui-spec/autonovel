"""
tests/integration/test_erotic_refine_workflow.py
refine_erotic_workflowの統合テスト。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.workflows.refine_erotic_workflow import RefineEroticWorkflow


@pytest.mark.asyncio
async def test_refine_erotic_workflow_success():
    """正常なケースのテスト"""
    # モックのセットアップ
    mock_engine = MagicMock()
    mock_uow = MagicMock()
    mock_engine.repo.__aenter__.return_value = mock_uow

    # モックのチャプターとプロット
    mock_chapter = MagicMock()
    mock_chapter.content = "元のコンテンツ"
    mock_plot = MagicMock()

    mock_uow.chapters.get_chapter = AsyncMock(return_value=mock_chapter)
    mock_uow.plots.get_plot = AsyncMock(return_value=mock_plot)
    mock_uow.session.commit = AsyncMock()

    # ワークフローとモックエンジン
    workflow = RefineEroticWorkflow(engine=mock_engine)

    # EroticSpecialistのモック化（実際の処理をスキップ）
    original_metaphor_filter = None
    try:
        from src.engine.prompts.erotic_specialist import EroticSpecialist
        original_metaphor_filter = EroticSpecialist.metaphor_filter
        EroticSpecialist.metaphor_filter = lambda self, text, intensity: text  # 変更なし
    except ImportError:
        pass

    # EroticIntegrityCheckerのモック化
    original_check_all = None
    try:
        from src.agents.erotic_integrity import EroticIntegrityChecker
        original_check_all = EroticIntegrityChecker.check_all
        EroticIntegrityChecker.check_all = lambda self, text, consent_state=None: (True, [], None, None)
    except ImportError:
        pass

    # AfterglowEvaluatorのモック化
    original_evaluate = None
    try:
        from src.services.erotic_afterglow_evaluator import AfterglowEvaluator
        original_evaluate = AfterglowEvaluator.evaluate
        AfterglowEvaluator.evaluate = lambda self, text: (True, [])
    except ImportError:
        pass

    try:
        # 実行
        result = await workflow.execute(
            book_id=1,
            ep_num=1,
            intensity=3,
            platform_preset="kakuyomu_romance",
            reporter=MagicMock()  # ロガーはモック
        )

        # アサーション
        assert result["success"] is True
        assert result["is_ok"] is True
        assert result["intensity_applied"] == 3

        # データベース更新が行われたことを確認
        assert mock_chapter.content == "元のコンテンツ"  # メタファーフィルターで変更なしの場合
        assert mock_plot.erotic_intensity == 3
        mock_uow.session.commit.assert_awaited_once()
    finally:
        # モックを元に戻す
        if original_metaphor_filter:
            from src.engine.prompts.erotic_specialist import EroticSpecialist
            EroticSpecialist.metaphor_filter = original_metaphor_filter
        if original_check_all:
            from src.agents.erotic_integrity import EroticIntegrityChecker
            EroticIntegrityChecker.check_all = original_check_all
        if original_evaluate:
            from src.services.erotic_afterglow_evaluator import AfterglowEvaluator
            AfterglowEvaluator.evaluate = original_evaluate


@pytest.mark.asyncio
async def test_refine_erotic_workflow_failure():
    """何らかのステップが失敗したケースのテスト"""
    # モックのセットアップ
    mock_engine = MagicMock()
    mock_uow = MagicMock()
    mock_engine.repo.__aenter__.return_value = mock_uow

    # モックのチャプターとプロット
    mock_chapter = MagicMock()
    mock_chapter.content = "元のコンテンツ"
    mock_plot = MagicMock()

    mock_uow.chapters.get_chapter = AsyncMock(return_value=mock_chapter)
    mock_uow.plots.get_plot = AsyncMock(return_value=mock_plot)
    mock_uow.session.commit = AsyncMock()

    # ワークフローとモックエンジン
    workflow = RefineEroticWorkflow(engine=mock_engine)

    # EroticIntegrityCheckerを失敗させるモック
    original_check_all = None
    try:
        from src.agents.erotic_integrity import EroticIntegrityChecker
        original_check_all = EroticIntegrityChecker.check_all
        EroticIntegrityChecker.check_all = lambda self, text, consent_state=None: (False, ["テストエラー"], None, None)
    except ImportError:
        pass

    try:
        # 実行
        result = await workflow.execute(
            book_id=1,
            ep_num=1,
            intensity=2,
            platform_preset="kakuyomu_romance",
            reporter=MagicMock()
        )

        # アサーション
        assert result["success"] is True
        assert result["is_ok"] is False  # チェックが失敗しているのでFalse
        assert result["intensity_applied"] == 2
    finally:
        # モックを元に戻す
        if original_check_all:
            from src.agents.erotic_integrity import EroticIntegrityChecker
            EroticIntegrityChecker.check_all = original_check_all
