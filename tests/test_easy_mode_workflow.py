"""
EasyModeWorkflow → AutoWorkflowPipeline 委譲テスト

EasyModeWorkflow がインラインロジックではなく、統合パイプライン
(AutoWorkflowPipeline) に正しく委譲しているかを検証する。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.writing import FullAutoWorkflowResult


class MockReporter:
    """StatusReporter のモック実装"""

    def __init__(self, should_stop: bool = False):
        self.messages: list[tuple[str, str]] = []
        self.progress_calls: list[tuple[int, int, str, str]] = []
        self._should_stop = should_stop

    class _State:
        def __init__(self, should_stop: bool):
            self._should_stop = should_stop

        def should_stop(self) -> bool:
            return self._should_stop

    @property
    def state(self) -> _State:
        return self._State(self._should_stop)

    def update_progress(
        self, current: int, total: int, message: str = "", sub_message: str = ""
    ) -> None:
        self.progress_calls.append((current, total, message, sub_message))

    def report(self, message: str, level: str = "info") -> None:
        self.messages.append((message, level))


def _make_mock_engine() -> MagicMock:
    """EasyMode 用の最小 Engine モック"""
    engine = MagicMock()
    engine.planner = MagicMock()
    engine.planner.infer_easy_mode_params = AsyncMock(
        return_value=MagicMock(
            genre_key="ファンタジー",
            core_idea="テスト",
            mc_concept="チート",
            title_idea="タイトル",
        )
    )
    engine.planner.create_hegemony_plan = AsyncMock(
        return_value=(1, MagicMock(title="テスト小説"))
    )
    engine.planner.plan_auditor = MagicMock()
    engine.planner.plan_auditor.audit_bible_completeness = AsyncMock(return_value=True)
    engine.writer = MagicMock()
    engine.writer.generate_episodes_pipeline = AsyncMock(return_value=(1000, []))
    engine.llm = MagicMock()
    engine.llm.generate = AsyncMock(return_value="テキスト")
    engine.auditor = MagicMock()
    engine.auditor.audit = AsyncMock(
        return_value={"overall_score": 900, "issues": [], "improvements": []}
    )
    engine.repo = MagicMock()
    engine.repo.plot = MagicMock()
    engine.repo.plot.get_all_plots = AsyncMock(return_value=[])
    engine.repo.bible = MagicMock()
    engine.repo.bible.get_by_book_id = AsyncMock(return_value=MagicMock())
    engine.repo.plot.get_by_book_and_number = AsyncMock(return_value=MagicMock())
    engine.repo.episode = MagicMock()
    engine.repo.episode.get_by_book_and_number = AsyncMock(
        return_value=MagicMock(content="テスト本文")
    )
    engine.repo.episode.update_content = AsyncMock(return_value=True)
    engine.repo.get_book = AsyncMock(return_value=MagicMock(title="テスト小説"))
    return engine


def _make_full_auto_result(**overrides) -> FullAutoWorkflowResult:
    """FullAutoWorkflowResult のテスト用ファクトリ"""
    base: dict = {
        "book_id": 1,
        "title": "テスト小説",
        "chars_count": 1000,
        "failed_episodes": [],
        "status": "success",
        "easy_parameters": {"concept": "テスト"},
        "average_audit_score": 90.0,
        "episodes_detail": [
            {
                "episode_num": 1,
                "title": "第1話",
                "word_count": 1000,
                "audit_score": 90.0,
                "audit_passed": True,
                "rewrite_count": 0,
                "needs_human_review": False,
            }
        ],
        "illustrations": [],
        "marketing_pack": {"title": "テスト小説"},
    }
    base.update(overrides)
    return FullAutoWorkflowResult(**base)


class TestEasyModeWorkflowDelegation:
    """EasyModeWorkflow の AutoWorkflowPipeline 委譲テスト"""

    @pytest.fixture
    def mock_engine(self) -> MagicMock:
        return _make_mock_engine()

    @pytest.fixture
    def mock_reporter(self) -> MockReporter:
        return MockReporter()

    @pytest.mark.asyncio
    async def test_easy_mode_delegates_to_pipeline(
        self, mock_engine: MagicMock, mock_reporter: MockReporter
    ) -> None:
        """EasyModeWorkflow.execute() が AutoWorkflowPipeline に委譲する"""
        from src.backend.workflows.easy_mode_workflow import EasyModeWorkflow

        workflow = EasyModeWorkflow(engine=mock_engine)

        with patch(
            "src.backend.workflows.easy_mode_workflow.create_easy_mode_pipeline"
        ) as mock_create:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value=_make_full_auto_result())
            mock_create.return_value = mock_pipeline

            await workflow.execute(
                mock_reporter,
                genre="ファンタジー",
                keywords=["test"],
                protagonist_type="チート",
                target_episodes=3,
                words_per_episode=2000,
            )

        mock_pipeline.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_easy_mode_passes_is_easy_mode_true_to_context(
        self, mock_engine: MagicMock, mock_reporter: MockReporter
    ) -> None:
        """Context.is_easy_mode=True で pipeline.execute() が呼ばれる"""
        from src.backend.workflows.easy_mode_workflow import EasyModeWorkflow

        workflow = EasyModeWorkflow(engine=mock_engine)

        with patch(
            "src.backend.workflows.easy_mode_workflow.create_easy_mode_pipeline"
        ) as mock_create:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value=_make_full_auto_result())
            mock_create.return_value = mock_pipeline

            await workflow.execute(
                mock_reporter,
                genre="ファンタジー",
                target_episodes=3,
            )

        call_args = mock_pipeline.execute.await_args
        ctx = call_args.args[0]
        assert ctx.is_easy_mode is True
        assert ctx.genre == "ファンタジー"
        assert ctx.target_eps == 3

    @pytest.mark.asyncio
    async def test_easy_mode_uses_progress_reporter_adapter(
        self, mock_engine: MagicMock, mock_reporter: MockReporter
    ) -> None:
        """ProgressReporterAdapter(is_easy_mode=True) が生成される"""
        from src.backend.workflows.easy_mode_workflow import EasyModeWorkflow
        from src.services.progress_reporter import ProgressReporterAdapter

        workflow = EasyModeWorkflow(engine=mock_engine)

        with patch(
            "src.backend.workflows.easy_mode_workflow.create_easy_mode_pipeline"
        ) as mock_create, patch(
            "src.backend.workflows.easy_mode_workflow.ProgressReporterAdapter",
            wraps=ProgressReporterAdapter,
        ) as mock_adapter_cls:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value=_make_full_auto_result())
            mock_create.return_value = mock_pipeline

            await workflow.execute(
                mock_reporter,
                genre="ファンタジー",
                target_episodes=3,
            )

            mock_adapter_cls.assert_called_once()
            # ProgressReporterAdapter(reporter, is_easy_mode=...) の呼び出し方を検証
            call = mock_adapter_cls.call_args
            is_easy_mode_kw = call.kwargs.get("is_easy_mode")
            # 1番目の positional arg は reporter, 2番目 or kwargs は is_easy_mode
            positional_is_easy_mode = (
                call.args[1] if len(call.args) >= 2 else None
            )
            assert is_easy_mode_kw is True or positional_is_easy_mode is True, (
                f"Expected is_easy_mode=True, got args={call.args}, kwargs={call.kwargs}"
            )

    @pytest.mark.asyncio
    async def test_easy_mode_returns_dict_with_expected_keys(
        self, mock_engine: MagicMock, mock_reporter: MockReporter
    ) -> None:
        """返却値が EasyMode 互換 dict 形式である"""
        from src.backend.workflows.easy_mode_workflow import EasyModeWorkflow

        workflow = EasyModeWorkflow(engine=mock_engine)

        with patch(
            "src.backend.workflows.easy_mode_workflow.create_easy_mode_pipeline"
        ) as mock_create:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value=_make_full_auto_result())
            mock_create.return_value = mock_pipeline

            result = await workflow.execute(
                mock_reporter,
                genre="ファンタジー",
                target_episodes=3,
            )

        # EasyMode 互換 dict 必須キー
        assert "title" in result
        assert "episodes" in result
        assert "status" in result
        assert "total_episodes" in result
        assert result["title"] == "テスト小説"
        assert result["status"] == "success"
        assert len(result["episodes"]) == 1

    @pytest.mark.asyncio
    async def test_easy_mode_passes_protagonist_type_as_archetype(
        self, mock_engine: MagicMock, mock_reporter: MockReporter
    ) -> None:
        """protagonist_type が archetype_key に変換される"""
        from src.backend.workflows.easy_mode_workflow import EasyModeWorkflow

        workflow = EasyModeWorkflow(engine=mock_engine)

        with patch(
            "src.backend.workflows.easy_mode_workflow.create_easy_mode_pipeline"
        ) as mock_create:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value=_make_full_auto_result())
            mock_create.return_value = mock_pipeline

            await workflow.execute(
                mock_reporter,
                genre="SF",
                protagonist_type="主人公カスタム",
                target_episodes=5,
            )

        call_args = mock_pipeline.execute.await_args
        ctx = call_args.args[0]
        assert ctx.archetype_key == "主人公カスタム"
        assert ctx.genre == "SF"

    @pytest.mark.asyncio
    async def test_easy_mode_uses_default_genre_when_not_provided(
        self, mock_engine: MagicMock, mock_reporter: MockReporter
    ) -> None:
        """genre 省略時にデフォルト 'ファンタジー' を使う"""
        from src.backend.workflows.easy_mode_workflow import EasyModeWorkflow

        workflow = EasyModeWorkflow(engine=mock_engine)

        with patch(
            "src.backend.workflows.easy_mode_workflow.create_easy_mode_pipeline"
        ) as mock_create:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value=_make_full_auto_result())
            mock_create.return_value = mock_pipeline

            await workflow.execute(mock_reporter)  # genre 省略

        call_args = mock_pipeline.execute.await_args
        ctx = call_args.args[0]
        assert ctx.genre == "ファンタジー"

    @pytest.mark.asyncio
    async def test_easy_mode_passes_enable_audit_as_spice_guard(
        self, mock_engine: MagicMock, mock_reporter: MockReporter
    ) -> None:
        """enable_audit=False で enable_spice_guard=False になる"""
        from src.backend.workflows.easy_mode_workflow import EasyModeWorkflow

        workflow = EasyModeWorkflow(engine=mock_engine)

        with patch(
            "src.backend.workflows.easy_mode_workflow.create_easy_mode_pipeline"
        ) as mock_create:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value=_make_full_auto_result())
            mock_create.return_value = mock_pipeline

            await workflow.execute(
                mock_reporter,
                enable_audit=False,
                max_rewrites=0,
            )

        call_args = mock_pipeline.execute.await_args
        ctx = call_args.args[0]
        assert ctx.enable_spice_guard is False
        assert ctx.max_rewrite_iterations == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--no-cov", "-p", "no:cacheprovider"])
