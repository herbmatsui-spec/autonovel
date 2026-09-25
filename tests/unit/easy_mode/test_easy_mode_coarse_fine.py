import pytest
from unittest.mock import AsyncMock, MagicMock, ANY

from src.services.auto_workflow_pipeline import (
    create_easy_mode_pipeline,
    create_full_auto_pipeline,
    AutoWorkflowPipeline,
)
from src.services.pipeline_base import WorkflowContext
from src.services.pipeline_steps import PlanStep, WriteStep
from src.backend.background import StatusReporter
from src.models.plot import EpisodeMacroSkeleton, PlotMicroBlueprint, MasterSceneBlock, SceneBeatBlock, merge_macro_and_micro


def create_test_context(**kwargs):
    defaults = {
        "genre": "ファンタジー",
        "keywords": "転生, チート",
        "archetype_key": "hero",
        "target_eps": 2,
        "initial_limit": 5,
        "word_count": 2000,
        "use_coarse_fine_plot": True,
    }
    defaults.update(kwargs)
    return WorkflowContext(**defaults)


def test_create_easy_mode_pipeline_has_coarse_fine_support():
    """EasyMode パイプラインが二段階プロット展開に対応するステップを含んでいること"""
    pipeline = create_easy_mode_pipeline()
    step_types = [type(s) for s in pipeline.steps]
    assert PlanStep in step_types
    assert WriteStep in step_types

    ctx = create_test_context()
    assert ctx.use_coarse_fine_plot is True


def test_create_full_auto_pipeline_coarse_fine():
    """FullAuto パイプラインが二段階プロット展開に対応するステップを含んでいること"""
    pipeline = create_full_auto_pipeline()
    step_types = [type(s) for s in pipeline.steps]
    assert PlanStep in step_types
    assert WriteStep in step_types


@pytest.mark.asyncio
async def test_easy_mode_execution_with_coarse_fine():
    """EasyMode パイプライン実行時に骨子展開から執筆までが一貫して成功すること"""
    mock_reporter = MagicMock(spec=StatusReporter)
    mock_reporter.state = MagicMock()
    mock_reporter.state.should_stop.return_value = False

    mock_engine = MagicMock()
    mock_bible = MagicMock()
    mock_bible.title = "かんたん覇権小説"
    mock_bible.model_dump.return_value = {"title": "かんたん覇権小説"}
    mock_engine.planner.create_hegemony_plan = AsyncMock(return_value=(1, mock_bible))
    mock_engine.planner.generate_or_load_bible = AsyncMock(return_value=mock_bible)
    mock_engine.planner.plan_auditor = MagicMock()
    mock_engine.planner.plan_auditor.audit_bible_completeness = AsyncMock(return_value=True)

    mock_engine.plot_expander = MagicMock()
    mock_skeletons = [
        EpisodeMacroSkeleton(
            episode_number=1,
            episode_title="第1話 覚醒",
            pov_character="主人公",
            target_tension=40,
            key_event="スキル発動",
            next_hook="敵の気配",
        )
    ]
    mock_engine.plot_expander.expand_macro_skeletons = AsyncMock(return_value=mock_skeletons)
    mock_engine.plot_expander.ensure_detailed_plot = AsyncMock()

    mock_engine.writer.generate_episodes_pipeline = AsyncMock(return_value=(4000, []))

    pipeline = AutoWorkflowPipeline([PlanStep(), WriteStep()])
    ctx = create_test_context(target_eps=1)

    result = await pipeline.execute(ctx, mock_engine, mock_reporter)

    assert result.status == "success"
    assert result.chars_count == 4000
    mock_engine.plot_expander.expand_macro_skeletons.assert_awaited_once()
    mock_engine.plot_expander.ensure_detailed_plot.assert_awaited_once_with(
        book_id=1, ep_num=1, reporter=ANY
    )


def test_spice_guard_cooperation_with_jit_plot():
    """JIT展開されたプロットがSpiceGuardや執筆エンジンに必要な構造を満たしていること"""
    macro = EpisodeMacroSkeleton(
        ep_num=1,
        title="第1話",
        pov_character="主人公",
        tension=60,
        key_event="戦闘勃発",
        next_hook="謎の影",
    )
    micro = PlotMicroBlueprint(
        ep_num=1,
        scenes=[
            MasterSceneBlock(
                scene_number=1,
                action="敵と向き合う",
                psychological_layer="恐怖と覚悟の葛藤",
                beats=[
                    SceneBeatBlock(
                        action_description="抜刀の瞬間",
                        sensory_keywords=["冷気", "金属音"],
                        psychology_keywords=["恐怖", "覚悟"],
                    )
                ],
            )
        ],
    )
    merged = merge_macro_and_micro(macro, micro)
    assert len(merged.scenes) == 1
    scene = merged.scenes[0]
    assert scene.psychological_layer == "恐怖と覚悟の葛藤"
    assert len(scene.beats) == 1
    assert "冷気" in scene.beats[0].sensory_keywords
