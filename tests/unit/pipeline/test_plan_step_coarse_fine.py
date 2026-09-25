import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.pipeline_base import WorkflowContext
from src.backend.background import StatusReporter
from src.services.pipeline_steps import PlanStep
from src.models.plot import EpisodeMacroSkeleton


def create_test_context(**kwargs):
    defaults = {
        "genre": "ファンタジー",
        "keywords": "転生, 魔法",
        "archetype_key": "hero",
        "target_eps": 3,
        "initial_limit": 10,
        "word_count": 2000,
        "book_id": 1,
        "use_coarse_fine_plot": True,
    }
    defaults.update(kwargs)
    return WorkflowContext(**defaults)


@pytest.fixture
def mock_reporter():
    reporter = MagicMock(spec=StatusReporter)
    reporter.state = MagicMock()
    reporter.state.should_stop.return_value = False
    return reporter


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    # Planner mocks
    mock_bible = MagicMock()
    mock_bible.title = "テスト小説"
    mock_bible.model_dump.return_value = {"title": "テスト小説"}
    engine.planner.create_hegemony_plan = AsyncMock(return_value=(1, mock_bible))
    engine.planner.generate_or_load_bible = AsyncMock(return_value=mock_bible)
    engine.planner.plan_auditor = MagicMock()
    engine.planner.plan_auditor.audit_bible_completeness = AsyncMock(return_value=True)

    # Plot Expander mock
    engine.plot_expander = MagicMock()
    mock_skeletons = [
        EpisodeMacroSkeleton(
            episode_number=i,
            episode_title=f"第{i}話",
            pov_character="主人公",
            target_tension=50,
            key_event="事件発生",
            next_hook="引き",
        )
        for i in range(1, 4)
    ]
    engine.plot_expander.expand_macro_skeletons = AsyncMock(return_value=mock_skeletons)
    return engine


@pytest.mark.asyncio
async def test_plan_step_executes_macro_expansion(mock_engine, mock_reporter):
    """二段階化フラグ有効時、大局骨子バッチ展開が正しく呼び出されること"""
    ctx = create_test_context(use_coarse_fine_plot=True)
    step = PlanStep()
    result = await step.execute(ctx, mock_engine, mock_reporter)

    assert result is True
    mock_engine.plot_expander.expand_macro_skeletons.assert_awaited_once_with(
        book_id=ctx.book_id,
        target_ep_list=[1, 2, 3],
        reporter=mock_reporter,
    )


@pytest.mark.asyncio
async def test_plan_step_populates_context_metadata(mock_engine, mock_reporter):
    """骨子生成後、コンテキストに骨子数が記録されること"""
    ctx = create_test_context(use_coarse_fine_plot=True)
    step = PlanStep()
    await step.execute(ctx, mock_engine, mock_reporter)

    assert ctx.easy_parameters.get("macro_skeletons_count") == 3


@pytest.mark.asyncio
async def test_plan_step_toggle_backward_compatibility(mock_engine, mock_reporter):
    """二段階化フラグ無効時、expand_macro_skeletons は呼ばれないこと"""
    ctx = create_test_context(use_coarse_fine_plot=False)
    step = PlanStep()
    result = await step.execute(ctx, mock_engine, mock_reporter)

    assert result is True
    mock_engine.plot_expander.expand_macro_skeletons.assert_not_awaited()
    assert "macro_skeletons_count" not in ctx.easy_parameters


@pytest.mark.asyncio
async def test_plan_step_legacy_fallback(mock_engine, mock_reporter):
    """大局骨子展開でエラーが発生しても処理が継続（フォールバック）されること"""
    mock_engine.plot_expander.expand_macro_skeletons.side_effect = RuntimeError("LLM一時障害")

    ctx = create_test_context(use_coarse_fine_plot=True)
    step = PlanStep()
    result = await step.execute(ctx, mock_engine, mock_reporter)

    # エラーにならず warning を報告して継続
    assert result is True
    mock_reporter.report.assert_any_call(
        "⚠️ 大局骨子生成でエラー (既存プロット継続): LLM一時障害", "warning"
    )
