"""
エロティック機能の統合テスト
エロティックゲートが正しくパイプラインに伝播することを確認
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.auto_workflow_pipeline import (
    AutoWorkflowPipeline,
    create_full_auto_pipeline,
    WorkflowContext,
)
from src.services.pipeline_base import WorkflowStep
from src.services.pipeline_steps import PlanStep


class MockEngine:
    """エロティック統合テスト用モックエンジン"""

    def __init__(self):
        self.repo = MagicMock()
        self.planner = MagicMock()
        self.writer = MagicMock()
        self.llm = MagicMock()
        self.auditor = MagicMock()

        # デフォルトモック設定
        self.planner.infer_easy_mode_params = AsyncMock(return_value=MagicMock(
            genre_key="ファンタジー",
            core_idea="テストコンセプト",
            mc_concept="チート主人公",
            title_idea="テスト小説",
        ))
        self.planner.create_hegemony_plan = AsyncMock(return_value=(1, MagicMock(title="テスト小説")))
        self.planner.plan_auditor = MagicMock()
        self.planner.plan_auditor.audit_bible_completeness = AsyncMock(return_value=True)

        self.writer.generate_episodes_pipeline = AsyncMock(return_value=(10000, []))
        self.llm.generate = AsyncMock(return_value="リライトされた本文")
        self.auditor.audit = AsyncMock(return_value={
            "overall_score": 900,  # 1000点満点
            "issues": [],
            "improvements": ["もっと面白く"],
        })

        # リポジトリモック
        self.repo.plot.get_all_plots = AsyncMock(return_value=[])
        self.repo.bible.get_by_book_id = AsyncMock(return_value=MagicMock())
        self.repo.plot.get_by_book_and_number = AsyncMock(return_value=MagicMock())
        self.repo.episode.get_by_book_and_number = AsyncMock(return_value=MagicMock(content="テスト本文"))
        self.repo.episode.update_content = AsyncMock(return_value=True)
        self.repo.get_book = AsyncMock(return_value=MagicMock(title="テスト小説"))


class MockReporter:
    """モック進捗レポーター"""

    def __init__(self, should_stop: bool = False):
        self.messages = []
        self.progress_calls = []
        self._should_stop = should_stop
        self.state = self

    def update_progress(self, current: int, total: int, message: str = "", sub_message: str = ""):
        self.progress_calls.append((current, total, message, sub_message))

    def report(self, message: str, level: str = "info"):
        self.messages.append((message, level))

    def should_stop(self):
        return self._should_stop


@pytest.mark.asyncio
async def test_erotic_parameters_propagated_to_planner():
    """エロティックパラメータがPlannerに正しく伝播することを確認"""
    mock_engine = MockEngine()
    mock_reporter = MockReporter()

    # エロティック有効でパイプラインを作成
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="チート,無双",
        archetype_key="王道ざまぁ（爽快感最大）",
        target_eps=3,
        initial_limit=3,
        word_count=2000,
        concept="テストコンセプト",
        tone_vibe=0.6,
        user_prompt="",
        enable_spice_guard=True,
        enable_illustration=False,
        enable_catharsis_analysis=True,
        enable_marketing=True,
        max_retries=0,
        is_easy_mode=False,
    )
    # エロティックパラメータをeasy_parametersに設定 (Plannerが参照する場所)
    ctx.easy_parameters["enable_erotic"] = True
    ctx.easy_parameters["erotic_intensity"] = 3

    # PlanStepのみを含むパイプラインを作成
    pipeline = AutoWorkflowPipeline([PlanStep()])


    # パイプラインを実行
    result = await pipeline.execute(ctx, mock_engine, mock_reporter)

    # 成功することを確認
    assert result.status == "success"

    # Plannerのcreate_hegemony_planがエロティックパラメータで呼ばれたことを確認
    mock_engine.planner.create_hegemony_plan.assert_awaited_once()

    call_args = mock_engine.planner.create_hegemony_plan.call_args
    # 第1引数はWorkflowContext、第2引数はreporter
    assert call_args[0][0] == ctx  # コンテキストが渡されている
    assert call_args[0][1] == mock_reporter  # レポーターが渡されている

    # コンテキストにエロティックパラメータが設定されていることを確認
    assert ctx.easy_parameters.get("enable_erotic") is True
    assert ctx.easy_parameters.get("erotic_intensity") == 3
@pytest.mark.asyncio
async def test_erotic_disabled_when_not_requested():
    """エロティックが要求されていない場合は無効になることを確認"""
    mock_engine = MockEngine()
    mock_reporter = MockReporter()

    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="チート,無双",
        archetype_key="王道ざまぁ（爽快感最大）",
        target_eps=3,
        initial_limit=3,
        word_count=2000,
        concept="テストコンセプト",
        tone_vibe=0.6,
        user_prompt="",
        enable_spice_guard=True,
        enable_illustration=False,
        enable_catharsis_analysis=True,
        enable_marketing=True,
        max_retries=0,
        is_easy_mode=False,
    )
    # エロティックパラメータをeasy_parametersに設定 (Plannerが参照する場所)
    ctx.easy_parameters["enable_erotic"] = False
    ctx.easy_parameters["erotic_intensity"] = 0

    pipeline = AutoWorkflowPipeline([PlanStep()])
    result = await pipeline.execute(ctx, mock_engine, mock_reporter)

    assert result.status == "success"
    mock_engine.planner.create_hegemony_plan.assert_awaited_once()
    assert ctx.easy_parameters.get("enable_erotic") is False
    assert ctx.easy_parameters.get("erotic_intensity") == 0


@pytest.mark.asyncio
async def test_full_auto_pipeline_with_erotic():
    """FullAutoパイプラインでエロティックパラメータが正しく扱われることを確認"""
    mock_engine = MockEngine()
    mock_reporter = MockReporter()

    # FullAutoワークフロー用のコンテキストを作成（pipeline_param_mapperを経由する想定）
    # ここでは直接WorkflowContextを作成し、easy_parametersを設定する
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="チート,無双",
        archetype_key="王道ざまぁ（爽快感最大）",
        target_eps=3,
        initial_limit=3,
        word_count=2000,
        concept="テストコンセプト",
        tone_vibe=0.6,
        user_prompt="",
        enable_spice_guard=True,
        enable_illustration=True,
        enable_catharsis_analysis=True,
        enable_marketing=True,
        max_retries=1,
        is_easy_mode=False,
    )
    # easy_parametersを手動で設定（実際はpipeline_param_mapperが設定する）
    ctx.easy_parameters["enable_erotic"] = True
    ctx.easy_parameters["erotic_intensity"] = 4

    # FullAutoパイプラインを作成
    pipeline = create_full_auto_pipeline(
        enable_spice_guard=True,
        enable_illustration=True,
    )

# パイプラインを実行
    result = await pipeline.execute(ctx, mock_engine, mock_reporter)

    # 成功することを確認
    assert result.status == "success"

    # 各ステップが呼ばれたことを確認（PlanStepにおいてエロティックパラメータが使われたことを確認）
    mock_engine.planner.create_hegemony_plan.assert_awaited()
    # 呼び出し時にエロティックパラメータがコンテキストに設定されていることを確認
    call_args = mock_engine.planner.create_hegemony_plan.call_args
    assert call_args[0][0].easy_parameters.get("enable_erotic") is True
    assert call_args[0][0].easy_parameters.get("erotic_intensity") == 4


