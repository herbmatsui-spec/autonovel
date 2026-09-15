from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.auto_workflow_pipeline import (
    AutoWorkflowPipeline,
    InferenceStep,
    create_custom_pipeline,
    create_easy_mode_pipeline,
    create_full_auto_pipeline,
)
from src.services.pipeline_base import WorkflowContext, WorkflowStep
from src.services.pipeline_steps import (
    AuditRewriteStep,
    CatharsisAnalysisStep,
    IllustrationStep,
    MarketingStep,
    PackageStep,
    PlanStep,
    WriteStep,
)


def test_create_full_auto_pipeline_default():
    pipeline = create_full_auto_pipeline()
    step_types = [type(s) for s in pipeline.steps]
    assert InferenceStep in step_types
    assert PlanStep in step_types
    assert CatharsisAnalysisStep in step_types
    assert WriteStep in step_types
    assert AuditRewriteStep not in step_types
    assert IllustrationStep not in step_types
    assert MarketingStep in step_types
    assert PackageStep in step_types


def test_create_full_auto_pipeline_options():
    pipeline = create_full_auto_pipeline(
        enable_spice_guard=True,
        enable_illustration=True,
        enable_catharsis_analysis=False,
        enable_marketing=False,
    )
    step_types = [type(s) for s in pipeline.steps]
    assert AuditRewriteStep in step_types
    assert IllustrationStep in step_types
    assert CatharsisAnalysisStep not in step_types
    assert MarketingStep not in step_types


def test_create_easy_mode_pipeline():
    pipeline = create_easy_mode_pipeline(
        enable_spice_guard=True,
        enable_marketing=True,
    )
    step_types = [type(s) for s in pipeline.steps]
    assert InferenceStep in step_types
    assert PlanStep in step_types
    assert WriteStep in step_types
    assert AuditRewriteStep in step_types
    assert MarketingStep in step_types
    assert PackageStep in step_types
    assert CatharsisAnalysisStep not in step_types
    assert IllustrationStep not in step_types


def test_create_custom_pipeline():
    custom_steps = [InferenceStep(), PackageStep()]
    pipeline = create_custom_pipeline(steps=custom_steps)
    assert pipeline.steps == custom_steps

    pipeline_options = create_custom_pipeline(
        inference=False,
        plan=True,
        catharsis=True,
        write=False,
        audit_rewrite=True,
        illustration=True,
        marketing=False,
    )
    step_types = [type(s) for s in pipeline_options.steps]
    assert InferenceStep not in step_types
    assert PlanStep in step_types
    assert CatharsisAnalysisStep in step_types
    assert WriteStep not in step_types
    assert AuditRewriteStep in step_types
    assert IllustrationStep in step_types
    assert MarketingStep not in step_types
    assert PackageStep in step_types


@pytest.mark.asyncio
async def test_auto_workflow_pipeline_execute_success():
    mock_step1 = AsyncMock(spec=WorkflowStep)
    mock_step1.execute.return_value = True
    mock_step2 = AsyncMock(spec=WorkflowStep)
    mock_step2.execute.return_value = True

    pipeline = AutoWorkflowPipeline([mock_step1, mock_step2])
    ctx = MagicMock(spec=WorkflowContext)
    ctx.book_id = 1
    ctx.title = "Test Title"
    ctx.chars_count = 5000
    ctx.failed_episodes = []
    ctx.zip_data = b"dummy_zip"
    ctx.zip_filename = "test.zip"
    ctx.is_easy_mode = False
    ctx.easy_parameters = None
    ctx.average_audit_score = 90.0
    ctx.episodes_detail = []
    ctx.enable_spice_guard = False
    ctx.illustrations = []
    ctx.marketing_pack = None

    reporter = MagicMock()
    reporter.state.should_stop.return_value = False

    result = await pipeline.execute(ctx, MagicMock(), reporter)
    assert result.status == "success"
    assert result.book_id == 1
    assert result.title == "Test Title"
    assert mock_step1.execute.await_count == 1
    assert mock_step2.execute.await_count == 1


@pytest.mark.asyncio
async def test_auto_workflow_pipeline_execute_failure():
    mock_step1 = AsyncMock(spec=WorkflowStep)
    mock_step1.execute.return_value = False
    mock_step2 = AsyncMock(spec=WorkflowStep)

    pipeline = AutoWorkflowPipeline([mock_step1, mock_step2])
    ctx = MagicMock(spec=WorkflowContext)
    ctx.book_id = 1
    ctx.title = "Fail Title"
    ctx.chars_count = 0
    ctx.failed_episodes = [{"ep_num": 1, "error": "write failed"}]
    ctx.is_easy_mode = False
    ctx.easy_parameters = None
    ctx.average_audit_score = 0.0
    ctx.episodes_detail = []
    ctx.enable_spice_guard = False

    reporter = MagicMock()
    reporter.state.should_stop.return_value = False

    result = await pipeline.execute(ctx, MagicMock(), reporter)
    assert result.status == "failed"
    assert mock_step2.execute.await_count == 0


@pytest.mark.asyncio
async def test_auto_workflow_pipeline_execute_stopped():
    mock_step1 = AsyncMock(spec=WorkflowStep)
    mock_step1.execute.return_value = False

    pipeline = AutoWorkflowPipeline([mock_step1])
    ctx = MagicMock(spec=WorkflowContext)
    ctx.book_id = 2
    ctx.title = "Stop Title"
    ctx.chars_count = 0
    ctx.failed_episodes = []
    ctx.is_easy_mode = False
    ctx.easy_parameters = None
    ctx.average_audit_score = 0.0
    ctx.episodes_detail = []
    ctx.enable_spice_guard = False

    reporter = MagicMock()
    reporter.state.should_stop.return_value = True

    result = await pipeline.execute(ctx, MagicMock(), reporter)
    assert result.status == "stopped"


@pytest.mark.asyncio
async def test_auto_workflow_pipeline_execute_plan_integrity_failure():
    mock_plan_step = PlanStep()
    mock_plan_step.execute = AsyncMock(return_value=False)

    pipeline = AutoWorkflowPipeline([mock_plan_step])
    ctx = MagicMock(spec=WorkflowContext)
    ctx.book_id = 3
    ctx.title = "Plan Fail"
    ctx.chars_count = 0
    ctx.failed_episodes = []
    ctx.is_easy_mode = False
    ctx.easy_parameters = None
    ctx.average_audit_score = 0.0
    ctx.episodes_detail = []
    ctx.enable_spice_guard = False

    reporter = MagicMock()
    reporter.state.should_stop.return_value = False

    result = await pipeline.execute(ctx, MagicMock(), reporter)
    assert result.status == "failed_integrity_check"


@pytest.mark.asyncio
async def test_inference_step_with_prompt():
    step = InferenceStep()
    ctx = MagicMock(spec=WorkflowContext)
    ctx.user_prompt = "最強の勇者"
    ctx.genre = "fantasy"
    ctx.concept = "old concept"
    ctx.keywords = "magic"
    ctx.title = ""

    engine = MagicMock()
    inference_result = MagicMock()
    inference_result.genre_key = "isekai"
    inference_result.core_idea = "cheat ability"
    inference_result.mc_concept = "overpowered"
    inference_result.title_idea = "Cheat Hero"
    engine.planner.infer_easy_mode_params = AsyncMock(return_value=inference_result)

    reporter = MagicMock()
    success = await step.execute(ctx, engine, reporter)
    assert success is True
    assert ctx.genre == "isekai"
    assert "cheat ability" in ctx.concept
    assert "overpowered" in ctx.keywords
    assert ctx.title == "Cheat Hero"


@pytest.mark.asyncio
async def test_inference_step_without_prompt():
    step = InferenceStep()
    ctx = MagicMock(spec=WorkflowContext)
    ctx.user_prompt = ""

    engine = MagicMock()
    reporter = MagicMock()
    success = await step.execute(ctx, engine, reporter)
    assert success is True
    engine.planner.infer_easy_mode_params.assert_not_called()


@pytest.mark.asyncio
async def test_inference_step_exception_handling():
    step = InferenceStep()
    ctx = MagicMock(spec=WorkflowContext)
    ctx.user_prompt = "最強の勇者"
    ctx.genre = "fantasy"
    ctx.concept = "concept"
    ctx.keywords = ""
    ctx.title = ""

    engine = MagicMock()
    engine.planner.infer_easy_mode_params = AsyncMock(side_effect=RuntimeError("API error"))

    reporter = MagicMock()
    success = await step.execute(ctx, engine, reporter)
    assert success is True
    reporter.report.assert_called()
