"""
Test file for pipeline steps.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from src.services.pipeline_steps import (
    PlanStep,
    WriteStep,
)
from src.services.pipeline_base import WorkflowContext


@pytest.mark.asyncio
async def test_plan_step_execute_success():
    """PlanStep.execute の正常系テスト."""
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
    reporter.state.should_stop = MagicMock(return_value=False)
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    
    step = PlanStep()
    result = await step.execute(ctx, engine, reporter)
    
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