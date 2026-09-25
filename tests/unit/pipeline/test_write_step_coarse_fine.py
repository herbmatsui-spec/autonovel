import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.pipeline_base import WorkflowContext
from src.backend.background import StatusReporter
from src.services.pipeline_steps import WriteStep


def create_test_context(**kwargs):
    defaults = {
        "genre": "ファンタジー",
        "keywords": "転生, 魔法",
        "archetype_key": "hero",
        "target_eps": 3,
        "initial_limit": 10,
        "word_count": 2000,
        "book_id": 1,
        "start_ep": 1,
        "end_ep": 3,
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
    # Writer mocks
    engine.writer.generate_episodes_pipeline = AsyncMock(return_value=(6000, []))

    # Plot Expander mock
    engine.plot_expander = MagicMock()
    engine.plot_expander.ensure_detailed_plot = AsyncMock()
    return engine


@pytest.mark.asyncio
async def test_write_step_triggers_jit_expansion(mock_engine, mock_reporter):
    """執筆開始前に対象話数の JIT プロット展開 (ensure_detailed_plot) が発火すること"""
    ctx = create_test_context(use_coarse_fine_plot=True)
    step = WriteStep()
    result = await step.execute(ctx, mock_engine, mock_reporter)

    assert result is True
    mock_engine.plot_expander.ensure_detailed_plot.assert_awaited_once_with(
        book_id=ctx.book_id,
        ep_num=ctx.start_ep,
        reporter=mock_reporter,
    )
    assert ctx.chars_count == 6000


@pytest.mark.asyncio
async def test_write_step_first_episode_safety(mock_engine, mock_reporter):
    """第1話（前話なし）でも安全に JIT プロット展開が実行されること"""
    ctx = create_test_context(start_ep=1, end_ep=1)
    step = WriteStep()
    result = await step.execute(ctx, mock_engine, mock_reporter)

    assert result is True
    mock_engine.plot_expander.ensure_detailed_plot.assert_awaited_with(
        book_id=ctx.book_id,
        ep_num=1,
        reporter=mock_reporter,
    )


@pytest.mark.asyncio
async def test_write_step_toggle_backward_compatibility(mock_engine, mock_reporter):
    """二段階化フラグ無効時、ensure_detailed_plot は呼ばれず従来の執筆が行われること"""
    ctx = create_test_context(use_coarse_fine_plot=False)
    step = WriteStep()
    result = await step.execute(ctx, mock_engine, mock_reporter)

    assert result is True
    mock_engine.plot_expander.ensure_detailed_plot.assert_not_awaited()
    assert ctx.chars_count == 6000


@pytest.mark.asyncio
async def test_write_step_expander_error_resilience(mock_engine, mock_reporter):
    """ensure_detailed_plot が例外を投げても WriteStep 自体は執筆パイプラインへ継続すること"""
    mock_engine.plot_expander.ensure_detailed_plot.side_effect = RuntimeError("JIT展開エラー")

    ctx = create_test_context(use_coarse_fine_plot=True)
    step = WriteStep()
    result = await step.execute(ctx, mock_engine, mock_reporter)

    # EpisodeWriter 内のフォールバックに委ねられ、WriteStep 自体はクラッシュしない
    assert result is True
    assert ctx.chars_count == 6000
