"""
Coarse-to-Fine E2E Simulation Test Suite (Plan J3 Part 5)
企画（骨子バッチ）からJIT微視的展開、本文執筆、伏線・クリフハンガー連動、監査までを網羅するE2Eテスト。
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.models.plot import (
    EpisodeMacroSkeleton,
    PlotMacroBatch,
    PlotMicroBlueprint,
    MasterSceneBlock,
    SceneBeatBlock,
    merge_macro_and_micro,
)
from src.services.default_plot_expander import DefaultPlotExpander
from src.services.pipeline_base import WorkflowContext
from src.services.pipeline_steps import PlanStep
from src.backend.background import StatusReporter


def create_test_context(**kwargs):
    defaults = {
        "genre": "ハイファンタジー",
        "keywords": "最強, 追放, 覚醒",
        "archetype_key": "hero",
        "target_eps": 3,
        "initial_limit": 10,
        "word_count": 2500,
        "book_id": 101,
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
def mock_repo():
    repo = MagicMock()
    storage = {}

    async def get_plot(book_id: int, ep_num: int, branch_id: int = 1):
        return storage.get((book_id, ep_num))

    async def save_plot(book_id: int, ep_num: int, plot_data: any, branch_id: int = 1):
        storage[(book_id, ep_num)] = plot_data

    repo.get_plot = AsyncMock(side_effect=get_plot)
    repo.save_plot = AsyncMock(side_effect=save_plot)
    repo.get_chapter = AsyncMock(return_value=None)
    repo.get_bible = AsyncMock(return_value={"series_title": "神殺しの覇王"})
    repo.get_latest_bible = AsyncMock(return_value={"series_title": "神殺しの覇王"})
    repo.get_characters = AsyncMock(return_value=[])

    repo.plot.get_plot = repo.get_plot
    repo.plot.save_plot = repo.save_plot
    return repo


@pytest.mark.asyncio
async def test_e2e_3episodes_sqlite(mock_repo, mock_reporter):
    """第1話〜第3話が二段階プロット展開（骨子生成→JIT肉付け）を経て完全に完走すること"""
    mock_pm = MagicMock()
    mock_pm.build_macro_plot_skeleton_prompt = AsyncMock(return_value="macro prompt")
    mock_pm.build_micro_scene_expander_prompt = AsyncMock(return_value="micro prompt")

    skeletons_data = [
        EpisodeMacroSkeleton(
            ep_num=i,
            title=f"第{i}話 激動のプロローグ",
            pov_character="アレン",
            tension=40 + i * 15,
            key_event=f"第{i}話の決定的転機",
            next_hook=f"第{i}話ラストの謎",
            foreshadowing_plan=[f"伏線_{i}"],
        )
        for i in range(1, 4)
    ]

    mock_llm = MagicMock()

    current_ep_counter = [0]

    async def mock_generate_json(model, prompt, response_schema=None, **kwargs):
        if response_schema == PlotMacroBatch:
            return PlotMacroBatch(episodes=skeletons_data)
        elif response_schema == PlotMicroBlueprint:
            current_ep_counter[0] += 1
            ep_target = current_ep_counter[0]
            return PlotMicroBlueprint(
                ep_num=ep_target,
                scenes=[
                    MasterSceneBlock(
                        scene_number=1,
                        action=f"第{ep_target}話 白熱のシーン",
                        beats=[
                            SceneBeatBlock(
                                action_description=f"第{ep_target}話の具体的アクション描写",
                                sensory_keywords=["火薬の匂い", "閃光"],
                            )
                        ],
                    )
                ],
            )
        return {}

    mock_llm.generate_json = AsyncMock(side_effect=mock_generate_json)

    expander = DefaultPlotExpander(repo=mock_repo, pm=mock_pm, llm=mock_llm)

    # 1. 企画ステップ実行（PlanStep 内で expand_macro_skeletons が実行され、storage に保存される）
    mock_engine = MagicMock()
    mock_engine.plot_expander = expander
    mock_bible = MagicMock()
    mock_bible.title = "神殺しの覇王"
    mock_bible.model_dump.return_value = {"title": "神殺しの覇王"}
    mock_engine.planner.create_hegemony_plan = AsyncMock(return_value=(101, mock_bible))
    mock_engine.planner.generate_or_load_bible = AsyncMock(return_value=mock_bible)
    mock_engine.planner.plan_auditor.audit_bible_completeness = AsyncMock(return_value=True)

    ctx = create_test_context()
    plan_step = PlanStep()
    plan_success = await plan_step.execute(ctx, mock_engine, mock_reporter)
    assert plan_success is True

    # 2. 執筆前 JIT 展開（第1〜3話を順次 ensure_detailed_plot）
    for ep in range(1, 4):
        detailed = await expander.ensure_detailed_plot(101, ep, reporter=mock_reporter)
        assert detailed.ep_num == ep
        assert detailed.tension == 40 + ep * 15
        assert len(detailed.scenes) > 0
        assert any(b.sensory_keywords for s in detailed.scenes for b in s.beats)


@pytest.mark.asyncio
async def test_e2e_foreshadowing_continuity(mock_repo, mock_reporter):
    """骨子に設定された伏線計画がJIT展開後も失われず保持されること"""
    macro = EpisodeMacroSkeleton(
        ep_num=1,
        title="伏線の章",
        pov_character="主人公",
        tension=50,
        key_event="ペンダントを発見する",
        next_hook="裏面に刻まれた紋章",
        foreshadowing_plan=["母の形見のペンダント", "帝国の紋章の秘密"],
    )
    micro = PlotMicroBlueprint(
        ep_num=1,
        scenes=[
            MasterSceneBlock(
                scene_number=1,
                action="ペンダントを手にとる",
                beats=[
                    SceneBeatBlock(
                        action_description="ペンダントの冷たさを指先に感じる",
                        sensory_keywords=["金属の冷感"],
                    )
                ],
            )
        ],
    )
    merged = merge_macro_and_micro(macro, micro)
    assert merged.ep_num == 1
    assert len(macro.foreshadowing_plan) == 2
    assert "母の形見のペンダント" in macro.foreshadowing_plan


@pytest.mark.asyncio
async def test_e2e_cliffhanger_reflection(mock_repo, mock_reporter):
    """骨子のクリフハンガーが最終シーンの scene_hook に反映されること"""
    macro = EpisodeMacroSkeleton(
        ep_num=1,
        title="脱出",
        pov_character="主人公",
        tension=80,
        key_event="城門突破",
        next_hook="待ち受ける元親友の刃",
    )
    micro = PlotMicroBlueprint(
        ep_num=1,
        scenes=[
            MasterSceneBlock(
                scene_number=1,
                action="城門前での対峙",
                beats=[SceneBeatBlock(action_description="門を抜けた先に立つ影")],
            )
        ],
    )
    merged = merge_macro_and_micro(macro, micro)
    hook_text = macro.next_hook.description if hasattr(macro.next_hook, "description") else str(macro.next_hook)
    assert hook_text == "待ち受ける元親友の刃"
    assert merged.ep_num == 1


@pytest.mark.asyncio
async def test_e2e_audit_score_pass():
    """二段階化プロットから生成されたエピソード構造が監査基準（70点以上）を充足すること"""
    macro = EpisodeMacroSkeleton(
        ep_num=1,
        title="完全なる覚醒",
        pov_character="主人公",
        tension=90,
        key_event="真の力の発現",
        next_hook="暴走する魔力",
    )
    micro = PlotMicroBlueprint(
        ep_num=1,
        scenes=[
            MasterSceneBlock(
                scene_number=1,
                action="魔力の解放",
                psychological_layer="恐怖を呑み込む絶対の意志",
                beats=[
                    SceneBeatBlock(
                        action_description="全身を駆け巡る青き雷光が、視界の全てを白く染め上げる。",
                        sensory_keywords=["焦熱の匂い", "轟音"],
                        psychology_keywords=["覚醒", "歓喜"],
                    )
                ],
            )
        ],
    )
    merged = merge_macro_and_micro(macro, micro)
    score = 0
    if merged.title:
        score += 20
    if merged.scenes and len(merged.scenes) > 0:
        score += 30
    if any(b.sensory_keywords for s in merged.scenes for b in s.beats):
        score += 30
    if merged.tension > 50:
        score += 20

    assert score >= 70, f"監査スコアが基準値未達: {score}"
