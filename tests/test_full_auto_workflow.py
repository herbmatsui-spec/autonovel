"""
FullAutoWorkflow → AutoWorkflowPipeline 委譲テスト

FullAutoWorkflow がインラインロジックではなく、統合パイプライン
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
    """FullAuto 用の最小 Engine モック"""
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
        "chars_count": 2000,
        "failed_episodes": [],
        "zip_data": None,
        "zip_filename": None,
        "status": "success",
        "easy_parameters": {"concept": "テスト"},
        "average_audit_score": 88.0,
        "episodes_detail": [],
        "illustrations": [],
        "marketing_pack": {"title": "テスト小説"},
    }
    base.update(overrides)
    return FullAutoWorkflowResult(**base)


class TestFullAutoWorkflowDelegation:
    """FullAutoWorkflow の AutoWorkflowPipeline 委譲テスト"""

    @pytest.fixture
    def mock_engine(self) -> MagicMock:
        return _make_mock_engine()

    @pytest.fixture
    def mock_reporter(self) -> MockReporter:
        return MockReporter()

    @pytest.mark.asyncio
    async def test_full_auto_delegates_to_pipeline(
        self, mock_engine: MagicMock, mock_reporter: MockReporter
    ) -> None:
        """FullAutoWorkflow.execute() が AutoWorkflowPipeline に委譲する"""
        from src.backend.workflows.full_auto_workflow import FullAutoWorkflow

        workflow = FullAutoWorkflow(engine=mock_engine)

        with patch(
            "src.backend.workflows.full_auto_workflow.create_full_auto_pipeline"
        ) as mock_create:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value=_make_full_auto_result())
            mock_create.return_value = mock_pipeline

            await workflow.execute(
                mock_reporter,
                genre="ファンタジー",
                keywords=["test"],
                archetype_key="王道",
                target_eps=3,
                initial_limit=3,
                word_count=2000,
            )

        mock_pipeline.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_full_auto_passes_is_easy_mode_false_to_context(
        self, mock_engine: MagicMock, mock_reporter: MockReporter
    ) -> None:
        """Context.is_easy_mode=False で pipeline.execute() が呼ばれる"""
        from src.backend.workflows.full_auto_workflow import FullAutoWorkflow

        workflow = FullAutoWorkflow(engine=mock_engine)

        with patch(
            "src.backend.workflows.full_auto_workflow.create_full_auto_pipeline"
        ) as mock_create:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value=_make_full_auto_result())
            mock_create.return_value = mock_pipeline

            await workflow.execute(
                mock_reporter,
                genre="ファンタジー",
                keywords=["test"],
                archetype_key="王道",
                target_eps=3,
                initial_limit=3,
                word_count=2000,
            )

        call_args = mock_pipeline.execute.await_args
        ctx = call_args.args[0]
        assert ctx.is_easy_mode is False
        assert ctx.genre == "ファンタジー"
        assert ctx.target_eps == 3
        assert ctx.archetype_key == "王道"

    @pytest.mark.asyncio
    async def test_full_auto_uses_progress_reporter_adapter(
        self, mock_engine: MagicMock, mock_reporter: MockReporter
    ) -> None:
        """ProgressReporterAdapter(is_easy_mode=False) が生成される"""
        from src.backend.workflows.full_auto_workflow import FullAutoWorkflow
        from src.services.progress_reporter import ProgressReporterAdapter

        workflow = FullAutoWorkflow(engine=mock_engine)

        with patch(
            "src.backend.workflows.full_auto_workflow.create_full_auto_pipeline"
        ) as mock_create, patch(
            "src.backend.workflows.full_auto_workflow.ProgressReporterAdapter",
            wraps=ProgressReporterAdapter,
        ) as mock_adapter_cls:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value=_make_full_auto_result())
            mock_create.return_value = mock_pipeline

            await workflow.execute(
                mock_reporter,
                genre="ファンタジー",
                keywords=["test"],
                archetype_key="王道",
                target_eps=3,
                initial_limit=3,
                word_count=2000,
            )

            mock_adapter_cls.assert_called_once()
            call = mock_adapter_cls.call_args
            is_easy_mode_kw = call.kwargs.get("is_easy_mode")
            positional_is_easy_mode = (
                call.args[1] if len(call.args) >= 2 else None
            )
            assert is_easy_mode_kw is False or positional_is_easy_mode is False, (
                f"Expected is_easy_mode=False, got args={call.args}, kwargs={call.kwargs}"
            )

    @pytest.mark.asyncio
    async def test_full_auto_returns_dict_with_expected_keys(
        self, mock_engine: MagicMock, mock_reporter: MockReporter
    ) -> None:
        """返却値が FullAuto 互換 dict 形式である"""
        from src.backend.workflows.full_auto_workflow import FullAutoWorkflow

        workflow = FullAutoWorkflow(engine=mock_engine)

        with patch(
            "src.backend.workflows.full_auto_workflow.create_full_auto_pipeline"
        ) as mock_create:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value=_make_full_auto_result())
            mock_create.return_value = mock_pipeline

            result = await workflow.execute(
                mock_reporter,
                genre="ファンタジー",
                keywords=["test"],
                archetype_key="王道",
                target_eps=3,
                initial_limit=3,
                word_count=2000,
            )

        # FullAuto 互換 dict 必須キー
        assert "book_id" in result
        assert "title" in result
        assert "status" in result
        assert "easy_parameters" in result
        assert "average_audit_score" in result
        assert "episodes_detail" in result
        assert result["title"] == "テスト小説"
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_full_auto_does_not_call_engine_directly(
        self, mock_engine: MagicMock, mock_reporter: MockReporter
    ) -> None:
        """workflow が engine メソッドを直接呼ばない (パイプラインに完全委譲)"""
        from src.backend.workflows.full_auto_workflow import FullAutoWorkflow

        workflow = FullAutoWorkflow(engine=mock_engine)

        with patch(
            "src.backend.workflows.full_auto_workflow.create_full_auto_pipeline"
        ) as mock_create:
            mock_pipeline = MagicMock()
            mock_pipeline.execute = AsyncMock(return_value=_make_full_auto_result())
            mock_create.return_value = mock_pipeline

            await workflow.execute(
                mock_reporter,
                genre="ファンタジー",
                keywords=["test"],
                archetype_key="王道",
                target_eps=3,
                initial_limit=3,
                word_count=2000,
            )

        # engine の writer / planner / auditor は呼ばれていないはず
        mock_engine.writer.generate_episodes_pipeline.assert_not_called()
        mock_engine.planner.create_hegemony_plan.assert_not_called()
        mock_engine.auditor.audit.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--no-cov", "-p", "no:cacheprovider"])
