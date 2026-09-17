"""
src/services/pipeline_steps.py の深層単体テスト.
"""

from __future__ import annotations

import tempfile
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.pipeline_steps import (
    PlanStep,
    WriteStep,
    CatharsisAnalysisStep,
    AuditRewriteStep,
    PackageStep,
    IllustrationStep,
    MarketingStep,
    HookGenerationStep,
    IllustrationPointGenerationStep,
    ForeshadowingRegistrationStep,
)
from src.services.pipeline_base import WorkflowContext


# ==============================================================================
# 1. PlanStep Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_plan_step_execute_success():
    """PlanStep.execute の正常系テスト."""
    # モックの設定
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        book_id=None,
        start_ep=1,
        end_ep=None,
        easy_parameters={},
    )
    
    # エンジンとレポジトリのモック
    engine = MagicMock()
    engine.planner = MagicMock()
    engine.planner.create_hegemony_plan = AsyncMock(
        return_value=(1, MagicMock(title="Test Title", model_dump=MagicMock(return_value={})))
    )
    engine.planner.plan_auditor = MagicMock()
    engine.planner.plan_auditor.audit_bible_completeness = AsyncMock(return_value=True)
    
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    # ステップの実行
    step = PlanStep()
    result = await step.execute(ctx, engine, reporter)
    
    # アサーション
    assert result is True
    assert ctx.book_id == 1
    assert ctx.title == "Test Title"
    engine.planner.create_hegemony_plan.assert_called_once()
    reporter.update_progress.assert_called()


@pytest.mark.asyncio
async def test_plan_step_execute_failure_due_to_planner_error():
    """PlanStep.execute がプランナーエラーで失敗するテスト."""
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        book_id=None,
        start_ep=1,
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    engine.planner = MagicMock()
    engine.planner.create_hegemony_plan = AsyncMock(side_effect=Exception("Planner failed"))
    
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = PlanStep()
    
    with pytest.raises(Exception, match="Planner failed"):
        await step.execute(ctx, engine, reporter)


@pytest.mark.asyncio
async def test_plan_step_execute_skipped_due_to_stop_signal():
    """PlanStep.execute がストップシグナルでスキップされるテスト."""
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        book_id=None,
        start_ep=1,
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    engine.planner = MagicMock()
    engine.planner.create_hegemony_plan = AsyncMock(
        return_value=(1, MagicMock(title="Test Title", model_dump=MagicMock(return_value={})))
    )
    engine.planner.plan_auditor = MagicMock()
    engine.planner.plan_auditor.audit_bible_completeness = AsyncMock(return_value=True)
    
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=True)  # ストップシグナル
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = PlanStep()
    result = await step.execute(ctx, engine, reporter)
    
    # ストップシグナルがある場合でも、プランナーは呼び出されるが、結果はFalseになるはず
    # 実際の実装では、planner.create_hegemony_plan が呼ばれた後に should_stop をチェックする
    assert result is False  # ストップシグナルがあると False を返す
    reporter.update_progress.assert_called()


# ==============================================================================
# 2. WriteStep Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_write_step_execute_success():
    """WriteStep.execute の正常系テスト."""
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        book_id=1,
        start_ep=1,
        end_ep=5,
        max_retries=2,
        is_easy_mode=False,
        easy_parameters={},
    )
    
    engine = MagicMock()
    engine.writer = MagicMock()
    
    # _shared_ops.execute_with_retry のモック
    with pytest.MonkeyPatch().context() as m:
        m.setattr("src.backend.workflows._shared_ops.execute_with_retry", AsyncMock(return_value=(25000, [])))
        
        reporter = MagicMock()
        reporter.state.should_stop = MagicMock(return_value=False)
        reporter.update_progress = MagicMock()
        reporter.report = MagicMock()
        
        step = WriteStep()
        result = await step.execute(ctx, engine, reporter)
        
        assert result is True
        assert ctx.chars_count == 25000
        assert ctx.failed_episodes == []
        reporter.update_progress.assert_called()


@pytest.mark.asyncio
async def test_write_step_execute_no_book_id():
    """WriteStep.execute が book_id なしで失敗するテスト."""
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        book_id=None,  # book_id が None
        start_ep=1,
        end_ep=5,
        max_retries=2,
        is_easy_mode=False,
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = WriteStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is False  # book_id が None の場合はすぐに False を返す
    reporter.update_progress.assert_not_called()


# ==============================================================================
# 3. CatharsisAnalysisStep Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_catharsis_analysis_step_execute_disabled():
    """CatharsisAnalysisStep.execute が無効時はスキップされるテスト."""
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        enable_catharsis_analysis=False,  # 無効
        book_id=1,
        start_ep=1,
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = CatharsisAnalysisStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True
    # _emit_skip が呼ばれるはずだが、詳細なアサーションは省略


@pytest.mark.asyncio
async def test_catharsis_analysis_step_execute_no_book_id():
    """CatharsisAnalysisStep.execute が book_id なしでスキップされるテスト."""
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        enable_catharsis_analysis=True,
        book_id=None,  # book_id が None
        start_ep=1,
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = CatharsisAnalysisStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True
    # _emit_skip が呼ばれるはずだが、詳細なアサーションは省略


@pytest.mark.asyncio
async def test_catharsis_analysis_step_execute_success():
    """CatharsisAnalysisStep.execute の正常系テスト."""
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        enable_catharsis_analysis=True,
        book_id=1,
        start_ep=1,
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    engine.repo = MagicMock()
    engine.repo.plot = MagicMock()
    engine.repo.plot.get_all_plots = AsyncMock(return_value=[MagicMock(tension=70), MagicMock(tension=30)])
    
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    # ProjectContext.get_setting のモック
    with pytest.MonkeyPatch().context() as m:
        m.setattr("config.project_context.ProjectContext.get_setting", MagicMock(side_effect=lambda key, default=None: {
            "catharsis_threshold": 65,
            "catharsis_reset_value": 0
        }.get(key, default)))
        
        # WavePatternAnalyzer のモック
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = MagicMock(return_value=MagicMock(
            pattern_type="wave",
            amplitude=20.0,
            catharsis_points=[1, 3, 5],
            model_dump=MagicMock(return_value={"pattern_type": "wave", "amplitude": 20.0})
        ))
        
        with pytest.MonkeyPatch().context() as m2:
            m2.setattr("src.backend.engine_narrative.WavePatternAnalyzer", MagicMock(return_value=mock_analyzer))
            
            step = CatharsisAnalysisStep()
            result = await step.execute(ctx, engine, reporter)
            
            assert result is True
            assert ctx.catharsis_pattern == {"pattern_type": "wave", "amplitude": 20.0}
            assert ctx.catharsis_positions == [1, 3, 5]
            reporter.report.assert_any_call(
                "📊 カタルシスパターンを詳細分析中...",
                "info"
            )


# ==============================================================================
# 4. AuditRewriteStep Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_audit_rewrite_step_execute_spice_guard_disabled():
    """AuditRewriteStep.execute が SpiceGuard 無効時はスキップされるテスト."""
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        enable_spice_guard=False,  # 無効
        book_id=1,
        start_ep=1,
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = AuditRewriteStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True
    # ログに出力されるはずだが、キャプチャするのは難しいので、少なくとも例外が発生しないことを確認


@pytest.mark.asyncio
async def test_audit_rewrite_step_execute_no_book_id():
    """AuditRewriteStep.execute が book_id なしでスキップされるテスト."""
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        enable_spice_guard=True,
        book_id=None,  # book_id が None
        start_ep=1:
        end_ep=None,
        max_rewrite_iterations=2,
        target_audit_score=7.0,
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = AuditRewriteStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True


@pytest.mark.asyncio
async def test_audit_rewrite_step_execute_success():
    """AuditRewriteStep.execute の正常系テスト."""
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=2,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        enable_spice_guard=True,
        book_id=1,
        start_ep=1:
        end_ep=None,
        max_rewrite_iterations=2,
        target_audit_score=7.0,
        easy_parameters={},
    )
    
    engine = MagicMock()
    engine.repo = MagicMock()
    engine.repo.episode = MagicMock()
    engine.repo.episode.get_by_book_and_number = AsyncMock(
        return_value=MagicMock(content="Test episode content")
    )
    engine.repo.episode.update_content = AsyncMock()
    engine.repo.bible = MagicMock()
    engine.repo.bible.get_by_book_id = AsyncMock(return_value=MagicMock())
    engine.repo.plot = MagicMock()
    engine.repo.plot.get_by_book_and_number = AsyncMock(return_value=MagicMock())
    
    # アダプターのモック
    with pytest.MonkeyPatch().context() as m:
        # create_audit_adapter 関数をモック
        mock_audit_adapter = MagicMock()
        mock_audit_adapter.audit_episode = AsyncMock(return_value={
            "score": 8.0,
            "improvements": ["Add more detail"],
            "needs_human_review": False
        })
        m.setattr("src.services.audit_adapter.create_audit_adapter", MagicMock(return_value=mock_audit_adapter))
        
        # create_spice_guard_adapter 関数をモック
        mock_spice_guard = MagicMock()
        mock_spice_guard.extract_spice = MagicMock(return_value=["spice1", "spice2"])
        mock_spice_guard.build_rewrite_prompt = MagicMock(return_value="Rewrite prompt")
        mock_spice_guard.clean_markers = MagicMock(side_effect=lambda x: x)
        m.setattr("src.services.spice_guard_adapter.create_spice_guard_adapter", MagicMock(return_value=mock_spice_guard))
        
        engine.llm = MagicMock()
        engine.llm.generate = AsyncMock(return_value="Rewritten content")
        
        reporter = MagicMock()
        reporter.state.should_stop = MagicMock(return_value=False)
        reporter.update_progress = MagicMock()
        reporter.report = MagicMock()
        
        step = AuditRewriteStep()
        result = await step.execute(ctx, engine, reporter)
        
        assert result is True
        assert hasattr(ctx, 'average_audit_score')
        assert hasattr(ctx, 'episodes_detail')
        assert len(ctx.episodes_detail) == 2  # target_eps = 2
        reporter.update_progress.assert_called()


# ==============================================================================
# 5. PackageStep Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_package_step_execute_success():
    """PackageStep.execute の正常系テスト."""
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        book_id=1,
        start_ep=1:
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    engine.repo = MagicMock()
    engine.repo.get_book = AsyncMock(return_value=MagicMock(title="Test Book"))
    
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    
    step = PackageStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True
    assert ctx.zip_data is None
    assert ctx.zip_filename == "export_1.zip"
    assert ctx.title == "Test Book"
    assert ctx.marketing_pack["title"] == "Test Book"
    reporter.update_progress.assert_any_call(
        3, 4, "STEP 4/4: 納品データの準備中..."
    )
    reporter.update_progress.assert_any_call(
        4, 4, "全行程完了！"
    )


@pytest.mark.asyncio
async def test_package_step_execute_no_book_id():
    """PackageStep.execute が book_id なしで失敗するテスト."""
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        book_id=None,  # book_id が None
        start_ep=1:
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = PackageStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is False
    # 実際は_warningレベルで報告される（⏭️シンボル付き）
    reporter.report.assert_any_call(
        "⏭️ package: book_id is None",
        "warning"
    )


# ==============================================================================
# 6. IllustrationStep Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_illustration_step_execute_disabled():
    """IllustrationStep.execute が無効時はスキップされるテスト."
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        enable_illustration=False,  # 無効
        start_ep=1:
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = IllustrationStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True
    # 実際は_warningレベルで報告される（⏭️シンボル付き）
    reporter.report.assert_any_call(
        "⏭️ illustration: enable_illustration=False",
        "warning"
    )


@pytest.mark.asyncio
async def test_illustration_step_execute_no_settings():
    """IllustrationStep.execute が設定なしでスキップされるテスト."
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        enable_illustration=True,
        illustration_settings={},  # 空の辞書（有効だがenableIllustrationキーがない）
        start_ep=1:
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = IllustrationStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True
    # 実際は_warningレベルで報告される（⏭️シンボル付き）
    reporter.report.assert_any_call(
        "⏭️ illustration: illustration_settings.enableIllustration is not set",
        "warning"
    )


@pytest.mark.asyncio
async def test_illustration_step_execute_success():
    """IllustrationStep.execute の正常系テスト."
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        enable_illustration=True,
        illustration_settings={"enableIllustration": True},
        book_id=1:
        start_ep=1:
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    # illustration_agent のモック
    mock_ill_agent = MagicMock()
    engine.illustration_agent = mock_ill_agent
    
    # IllustrationWorkflow のモック
    with pytest.MonkeyPatch().context() as m:
        mock_workflow = MagicMock()
        mock_workflow.execute = AsyncMock(return_value={"status": "success", "illustrations": ["ill1", "ill2"]})
        m.setattr("src.backend.workflows.illustration_workflow.IllustrationWorkflow", MagicMock(return_value=mock_workflow))
        
        reporter = MagicMock()
        reporter.state.should_stop = MagicMock(return_value=False)
        reporter.update_progress = MagicMock()
        reporter.report = MagicMock()
        
        step = IllustrationStep()
        result = await step.execute(ctx, engine, reporter)
        
        assert result is True
        assert ctx.illustrations == ["ill1", "ill2"]
        reporter.report.assert_called_with(
            "🎨 挿絵生成完了: 2枚",
            "info"
        )


# ==============================================================================
# 7. MarketingStep Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_marketing_step_execute_disabled():
    """MarketingStep.execute が無効時はスキップされるテスト."
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10,
        initial_limit=5,
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        enable_marketing=False,  # 無効
        start_ep=1:
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = MarketingStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True
    # 実際は_warningレベルで報告される（⏭️シンボル付き）
    reporter.report.assert_any_call(
        "⏭️ marketing: enable_marketing=False",
        "warning"
    )


@pytest.mark.asyncio
async def test_marketing_step_execute_no_book_id():
    """MarketingStep.execute が book_id なしでスキップされるテスト."
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword",
        archetype_key="hero",
        target_eps=10:
        initial_limit=5:
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        enable_marketing=True,
        book_id=None,  # book_id が None
        start_ep=1:
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = MarketingStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True


@pytest.mark.asyncio
async def test_marketing_step_execute_success():
    """MarketingStep.execute の正常系テスト."
    ctx = WorkflowContext(
        genre="fantasy",
        keywords="magic, sword":
        archetype_key="hero",
        target_eps=10:
        initial_limit=5:
        word_count=5000,
        concept="A young hero discovers magical powers",
        title="",
        tone_vibe=0.6,
        enable_marketing=True,
        book_id=1:
        start_ep=1:
        end_ep=None,
        easy_parameters={},
    )
    
    engine = MagicMock()
    engine.repo = MagicMock()
    
    # プリセットのモック
    with pytest.MonkeyPatch().context() as m:
        m.setattr("src.services.preset_loader.load_preset_for_pipeline", MagicMock(return_value={
            "marketing": {
                "synopsis_structure": {"hook": "A magical adventure"},
                "catchphrase_templates": ["Experience the magic!"],
                "tags": ["fantasy", "adventure"]
            },
            "titles": {
                "title_templates": ["The Hero's Journey"]
            }
        }))
        
        engine.llm = MagicMock()
        engine.llm.generate = AsyncMock(return_value="Generated Title")
        
        reporter = MagicMock()
        reporter.state.should_stop = MagicMock(return_value=False)
        reporter.update_progress = MagicMock()
        reporter.report = MagicMock()
        
        step = MarketingStep()
        result = await step.execute(ctx, engine, reporter)
        
        assert result is True
        # 正常に実行され、何らかのタイトルが設定されていることを確認
        # 正確な値はプリセットの処理やLLMの結果により変わるため、
        # ここで空でないことのみを確認する
        assert ctx.title != ""
        assert ctx.marketing_pack["title"] != ""
        # conceptはテンプレート処理により変換される可能性があるため、空でないことのみ確認
        assert ctx.marketing_pack["concept"] != ""
        assert ctx.marketing_pack["synopsis"]["hook"] == "A magical adventure"
        # マーケティング生成完了のメッセージが出ていることを確認
        reporter.report.assert_any_call(
            "📢 マーケティング生成完了: タイトル『",
            "info"
        )


# ==============================================================================
# 8. HookGenerationStep Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_hook_generation_step_execute():
    """HookGenerationStep.execute のテスト (現在は常に True を返す骨格実装)."
    ctx = WorkflowContext(
        genre="fantasy":
        keywords="magic, sword":
        archetype_key="hero":
        target_eps=10:
        initial_limit=5:
        word_count=5000:
        concept="A young hero discovers magical powers":
        title="":
        tone_vibe=0.6:
        start_ep=1:
        end_ep=None:
        easy_parameters={},
    )
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.report = MagicMock()
    
    step = HookGenerationStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True  # 骨格実装なので常に True


# ==============================================================================
# 9. IllustrationPointGenerationStep Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_illustration_point_generation_step_execute_disabled():
    """IllustrationPointGenerationStep.execute が無効時はスキップされるテスト."
    ctx = WorkflowContext(
        genre="fantasy":
        keywords="magic, sword":
        archetype_key="hero":
        target_eps=10:
        initial_limit=5:
        word_count=5000:
        concept="A young hero discovers magical powers":
        title="":
        tone_vibe=0.6:
        enable_illustration=False,  # 無効
        start_ep=1:
        end_ep=None:
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = IllustrationPointGenerationStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True
    # 実際は_warningレベルで報告される（⏭️シンボル付き）
    reporter.report.assert_any_call(
        "⏭️ illustration_point: enable_illustration=False",
        "warning"
    )


@pytest.mark.asyncio
async def test_illustration_point_generation_step_execute_no_book_id():
    """IllustrationPointGenerationStep.execute が book_id なしでスキップされるテスト."
    ctx = WorkflowContext(
        genre="fantasy":
        keywords="magic, sword":
        archetype_key="hero":
        target_eps=10:
        initial_limit=5:
        word_count=5000:
        concept="A young hero discovers magical powers":
        title="":
        tone_vibe=0.6:
        enable_illustration=True:
        book_id=None,  # book_id が None
        start_ep=1:
        end_ep=None:
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = IllustrationPointGenerationStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True


@pytest.mark.asyncio
async def test_illustration_point_generation_step_execute_success():
    """IllustrationPointGenerationStep.execute の正常系テスト."
    ctx = WorkflowContext(
        genre="fantasy":
        keywords="magic, sword":
        archetype_key="hero":
        target_eps=10:
        initial_limit=5:
        word_count=5000:
        concept="A young hero discovers magical powers":
        title="":
        tone_vibe=0.6:
        enable_illustration=True:
        book_id=1:
        start_ep=1:
        end_ep=None:
        easy_parameters={},
    )
    
    engine = MagicMock()
    engine.repo = MagicMock()
    engine.repo.bible = MagicMock()
    engine.repo.bible.get_by_book_id = AsyncMock(return_value=MagicMock(characters=[
        MagicMock(name="Hero"):
        MagicMock(name="Villain")
    ]))
    engine.repo.plot = MagicMock()
    engine.repo.plot.get_all_plots = AsyncMock(return_value=[MagicMock(), MagicMock(), MagicMock()])  # 3つ以上
    engine.repo.episode = MagicMock()
    engine.repo.episode.get_all_by_book_id = AsyncMock(return_value=[MagicMock(), MagicMock(), MagicMock()])
    
    # IllustrationPoint のモック
    with pytest.MonkeyPatch().context() as m:
        mock_illustration_point = MagicMock()
        m.setattr("src.models.illustration_point.IllustrationPoint", MagicMock(return_value=mock_illustration_point))
        
        reporter = MagicMock()
        reporter.state.should_stop = MagicMock(return_value=False)
        reporter.update_progress = MagicMock()
        reporter.report = MagicMock()
        
        step = IllustrationPointGenerationStep()
        result = await step.execute(ctx, engine, reporter)
        
        assert result is True
        assert hasattr(ctx, 'illustration_points')
        assert len(ctx.illustration_points) >= 1  # 少なくとも1つの挿絵ポイントが生成される
        reporter.report.assert_called_with(
            f"🎨 挿絵ポイント生成完了: {len(ctx.illustration_points)}点の挿絵指示を生成",
            "info"
        )


# ==============================================================================
# 10. ForeshadowingRegistrationStep Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_foreshadowing_registration_step_execute_no_book_id():
    """ForeshadowingRegistrationStep.execute が book_id なしでスキップされるテスト."
    ctx = WorkflowContext(
        genre="fantasy":
        keywords="magic, sword":
        archetype_key="hero":
        target_eps=10:
        initial_limit=5:
        word_count=5000:
        concept="A young hero discovers magical powers":
        title="":
        tone_vibe=0.6:
        book_id=None,  # book_id が None
        start_ep=1:
        end_ep=None:
        easy_parameters={},
    )
    
    engine = MagicMock()
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.report = MagicMock()
    
    step = ForeshadowingRegistrationStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True


@pytest.mark.asyncio
async def test_foreshadowing_registration_step_execute_no_plots():
    """ForeshadowingRegistrationStep.execute がプロットなしでスキップされるテスト."
    ctx = WorkflowContext(
        genre="fantasy":
        keywords="magic, sword":
        archetype_key="hero":
        target_eps=10:
        initial_limit=5:
        word_count=5000:
        concept="A young hero discovers magical powers":
        title="":
        tone_vibe=0.6:
        book_id=1:
        start_ep=1:
        end_ep=None:
        easy_parameters={},
    )
    
    engine = MagicMock()
    engine.repo = MagicMock()
    engine.repo.plot = MagicMock()
    engine.repo.plot.get_all_plots = AsyncMock(return_value=[])  # プロットなし
    
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.report = MagicMock()
    
    step = ForeshadowingRegistrationStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True
    # 実際は警告アイコン(⚠️)で報告される
    reporter.report.assert_any_call(
        "⚠️ プロットが見つからないため伏線登録をスキップします",
        "warning"
    )


@pytest.mark.asyncio
async def test_foreshadowing_registration_step_execute_success():
    """ForeshadowingRegistrationStep.execute の正常系テスト."
    ctx = WorkflowContext(
        genre="fantasy":
        keywords="magic, sword":
        archete_key="hero":
        target_eps=10:
        initial_limit=5:
        word_count=5000:
        concept="A young hero discovers magical powers":
        title="":
        tone_vibe=0.6:
        book_id=1:
        start_ep=1:
        end_ep=None:
        easy_parameters={},
    )
    
    engine = MagicMock()
    engine.repo = MagicMock()
    engine.repo.plot = MagicMock()
    engine.repo.plot.get_all_plots = AsyncMock(return_value=[
        MagicMock(foreshadowing_hint="Ancient prophecy foretells the hero's return"):
        MagicMock(mystery_element="The missing king's crown")
    ])
    
    # リポジトリのモック (None にしてコンテキストフォールバックをテスト)
    engine.foreshadowing_repository = None
    
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.report = MagicMock()
    
    step = ForeshadowingRegistrationStep()
    result = await step.execute(ctx, engine, reporter)
    
    assert result is True
    assert hasattr(ctx, 'foreshadowings')
    assert len(ctx.foreshadowings) == 2  # 2つのプロットから伏線が抽出される
    reporter.report.assert_any_call(
        "📌 2件の伏線を登録しました",
        "info"
    )


# ==============================================================================
# 11. エラーハンドリングテスト
# ==============================================================================


@pytest.mark.asyncio
async def test_pipeline_steps_error_handling():
    """各パイプラインステップのエラーハンドリングをテスト."
    # PlanStep のエラーハンドリング
    ctx = WorkflowContext(
        genre="fantasy":
        keywords="magic, sword":
        archete_key="hero":
        target_eps=10:
        initial_limit=5:
        word_count=5000:
        concept="A young hero discovers magical powers":
        title="":
        tone_vibe=0.6:
        book_id=None:
        start_ep=1:
        end_ep=None:
        easy_parameters={},
    )
    
    engine = MagicMock()
    engine.planner = MagicMock()
    engine.planner.create_hegemony_plan = AsyncMock(side_effect=Exception("Test error"))
    engine.planner.plan_auditor = MagicMock()
    engine.planner.plan_auditor.audit_bible_completeness = AsyncMock(return_value=True)
    
    reporter = MagicMock()
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = PlanStep()
    
    # PlanStep は例外を再送出する
    with pytest.raises(Exception, match="Test error"):
        await step.execute(ctx, engine, reporter)
    
    # AuditRewriteStep は例外をキャッチして True を返す (継続)
    ctx2 = WorkflowContext(
        genre="fantasy":
        keywords="magic, sword":
        archete_key="hero":
        target_eps=1:
        initial_limit=5:
        word_count=5000:
        concept="A young hero discovers magical powers":
        title="":
        tone_vibe=0.6:
        enable_spice_guard=True:
        book_id=1:
        start_ep=1:
        end_ep=None:
        max_rewrite_iterations=1:
        target_audit_score=7.0:
        easy_parameters={},
    )
    
    engine2 = MagicMock()
    engine2.repo = MagicMock()
    engine2.repo.episode = MagicMock()
    engine2.repo.episode.get_by_book_and_number = AsyncMock(
        return_value=MagicMock(content="Test content")
    )
    engine2.repo.episode.update_content = AsyncMock()
    engine2.repo.bible = MagicMock()
    engine2.repo.bible.get_by_book_id = AsyncMock(return_value=MagicMock())
    engine2.repo.plot = MagicMock()
    engine2.repo.plot.get_by_book_and_number = AsyncMock(return_value=MagicMock())
    
    # アダプターが例外を送出する
    with pytest.MonkeyPatch().context() as m:
        # create_audit_adapter 関数をモック
        m.setattr("src.services.audit_adapter.create_audit_adapter", MagicMock(side_effect=Exception("Audit adapter error")))
        
        # create_spice_guard_adapter 関数をモック
        mock_spice_guard = MagicMock()
        mock_spice_guard.extract_spice = MagicMock(return_value=[])
        mock_spice_guard.build_rewrite_prompt = MagicMock(return_value="")
        mock_spice_guard.clean_markers = MagicMock(side_effect=lambda x: x)
        m.setattr("src.services.spice_guard_adapter.create_spice_guard_adapter", MagicMock(return_value=mock_spice_guard))
        
        engine2.llm = MagicMock()
        engine2.llm.generate = AsyncMock(return_value="")
        
        reporter2 = MagicMock()
        reporter2.state.should_stop = MagicMock(return_value=False)
        reporter2.update_progress = MagicMock()
        reporter2.report = MagicMock()
        
        step2 = AuditRewriteStep()
        result2 = await step2.execute(ctx2, engine2, reporter2)
        
        # AuditRewriteStep は例外をキャッチして True を返す (継続)
        assert result2 is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])