"""
統合パイプライン テスト
モックエンジンで全 Step 通しテスト
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.auto_workflow_pipeline import (
    AutoWorkflowPipeline,
    InferenceStep,
    WorkflowContext,
    create_easy_mode_pipeline,
    create_full_auto_pipeline,
)
from src.services.pipeline_base import WorkflowStep


class MockReporter:
    """モック進捗レポーター"""

    def __init__(self, should_stop: bool = False):
        self.messages = []
        self.progress_calls = []
        self._should_stop = should_stop

    class State:
        def __init__(self, should_stop: bool):
            self._should_stop = should_stop

        def should_stop(self):
            return self._should_stop

    @property
    def state(self):
        return self.State(self._should_stop)

    def update_progress(self, current: int, total: int, message: str = "", sub_message: str = ""):
        self.progress_calls.append((current, total, message, sub_message))

    def report(self, message: str, level: str = "info"):
        self.messages.append((message, level))

    def should_stop(self):
        return self._should_stop


class MockEngine:
    """モックエンジン"""

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
            title_idea="テストタイトル",
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


class TestUnifiedPipeline:
    """統合パイプラインテスト"""

    @pytest.fixture
    def mock_engine(self):
        return MockEngine()

    @pytest.fixture
    def mock_reporter(self):
        return MockReporter()

    @pytest.fixture
    def full_auto_context(self):
        return WorkflowContext(
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

    @pytest.fixture
    def easy_mode_context(self):
        return WorkflowContext(
            genre="ファンタジー",
            keywords="",
            archetype_key="チート主人公",
            target_eps=3,
            initial_limit=3,
            word_count=2000,
            concept="",
            tone_vibe=0.6,
            user_prompt="",
            enable_spice_guard=True,
            max_rewrite_iterations=2,
            target_audit_score=90.0,
            enable_illustration=False,
            enable_catharsis_analysis=False,
            enable_marketing=True,
            max_retries=0,
            is_easy_mode=True,
            preset_name="zarma",
        )

    @pytest.mark.asyncio
    async def test_full_auto_pipeline_structure(self):
        """FullAuto パイプライン構造テスト"""
        pipeline = create_full_auto_pipeline(
            enable_spice_guard=True,
            enable_illustration=True,
            enable_catharsis_analysis=True,
            enable_marketing=True,
        )

        step_names = [type(s).__name__ for s in pipeline.steps]
        expected = [
            "InferenceStep",
            "PlanStep",
            "CatharsisAnalysisStep",
            "WriteStep",
            "AuditRewriteStep",
            "IllustrationStep",
            "MarketingStep",
            "PackageStep",
        ]
        assert step_names == expected

    @pytest.mark.asyncio
    async def test_easy_mode_pipeline_structure(self):
        """EasyMode パイプライン構造テスト"""
        pipeline = create_easy_mode_pipeline("ファンタジー", 5)

        step_names = [type(s).__name__ for s in pipeline.steps]
        expected = [
            "InferenceStep",
            "PlanStep",
            "WriteStep",
            "AuditRewriteStep",
            "MarketingStep",
            "PackageStep",
        ]
        assert step_names == expected

    @pytest.mark.asyncio
    async def test_full_auto_pipeline_execution(self, mock_engine, mock_reporter, full_auto_context):
        """FullAuto パイプライン実行テスト (モック)"""
        pipeline = create_full_auto_pipeline(
            enable_spice_guard=True,
            enable_illustration=False,
            enable_catharsis_analysis=True,
        )

        # 実行時間短縮のため一部モック
        with patch("src.services.pipeline_steps.CatharsisAnalysisStep.execute", new_callable=AsyncMock) as mock_catharsis:
            mock_catharsis.return_value = True

            result = await pipeline.execute(full_auto_context, mock_engine, mock_reporter)

        assert result.status == "success"
        assert result.book_id == 1
        assert result.title == "テスト小説"
        assert result.chars_count == 10000

    @pytest.mark.asyncio
    async def test_easy_mode_pipeline_execution(self, mock_engine, mock_reporter, easy_mode_context):
        """EasyMode パイプライン実行テスト (モック)"""
        pipeline = create_easy_mode_pipeline("ファンタジー", 3)

        # AuditRewriteStep の内部でリポジトリアクセスするためモック強化
        mock_engine.repo.episode.get_by_book_and_number = AsyncMock(
            return_value=MagicMock(content="第1話の本文です。ざまぁ！無双！")
        )

        with patch("src.services.pipeline_steps.AuditRewriteStep.execute", new_callable=AsyncMock) as mock_audit:
            mock_audit.return_value = True

            result = await pipeline.execute(easy_mode_context, mock_engine, mock_reporter)

        assert result.status == "success"
        assert result.book_id == 1
        assert result.spice_guard_enabled is True

    @pytest.mark.asyncio
    async def test_pipeline_stop_on_failure(self, mock_engine, mock_reporter, full_auto_context):
        """Step 失敗時パイプライン停止テスト"""
        # PlanStep で失敗させる
        mock_engine.planner.plan_auditor.audit_bible_completeness = AsyncMock(return_value=False)

        pipeline = create_full_auto_pipeline(enable_spice_guard=False)
        result = await pipeline.execute(full_auto_context, mock_engine, mock_reporter)

        assert result.status == "failed_integrity_check"

    @pytest.mark.asyncio
    async def test_pipeline_stop_on_user_cancel(self, mock_engine, full_auto_context):
        """ユーザーキャンセル時停止テスト"""
        mock_reporter = MockReporter(should_stop=True)

        pipeline = create_full_auto_pipeline(enable_spice_guard=False)
        result = await pipeline.execute(full_auto_context, mock_engine, mock_reporter)

        assert result.status == "stopped"

    @pytest.mark.asyncio
    async def test_inference_step_with_prompt(self, mock_engine, mock_reporter):
        """InferenceStep: user_prompt 指定時の推論テスト"""
        ctx = WorkflowContext(
            genre="ファンタジー",
            keywords="",
            archetype_key="王道ざまぁ",
            target_eps=3,
            initial_limit=3,
            word_count=2000,
            user_prompt="転生チートで無双する話",
        )

        pipeline = AutoWorkflowPipeline([InferenceStep()])
        result = await pipeline.execute(ctx, mock_engine, mock_reporter)

        # 推論が実行され、genre/concept が更新される
        assert ctx.genre == "ファンタジー"
        assert "テストコンセプト" in ctx.concept

    @pytest.mark.asyncio
    async def test_plan_step_preset_integration(self, mock_engine, mock_reporter, full_auto_context):
        """PlanStep: プリセット統合テスト"""
        from src.services.pipeline_steps import PlanStep

        pipeline = AutoWorkflowPipeline([PlanStep()])
        result = await pipeline.execute(full_auto_context, mock_engine, mock_reporter)

        # プリセット設定が適用される
        assert full_auto_context.book_id == 1
        assert "style_key" in full_auto_context.easy_parameters
        assert "cheat_scale" in full_auto_context.easy_parameters

    @pytest.mark.asyncio
    async def test_write_step_retry_logic(self, mock_engine, mock_reporter):
        """WriteStep: リトライロジックテスト"""
        from src.services.pipeline_steps import WriteStep

        # Context に book_id を設定 (PlanStep をスキップするため)
        ctx = WorkflowContext(
            genre="ファンタジー",
            keywords="",
            archetype_key="王道ざまぁ",
            target_eps=3,
            initial_limit=3,
            word_count=2000,
            book_id=1,  # 事前設定
            max_retries=1,
        )

        # 1回目失敗、2回目成功
        call_count = [0]
        async def mock_generate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return (5000, [{"ep_num": 1, "error_message": "timeout"}])
            return (5000, [])

        mock_engine.writer.generate_episodes_pipeline = mock_generate

        pipeline = AutoWorkflowPipeline([WriteStep()])
        result = await pipeline.execute(ctx, mock_engine, mock_reporter)

        assert call_count[0] == 2  # 初回 + リトライ1回
        assert ctx.chars_count == 10000


# ---------------------------------------------------------------------------
# Step 1-4: WorkflowContext.warnings / _emit_skip ヘルパー
# ---------------------------------------------------------------------------


def test_workflow_context_warnings_default_empty():
    """WorkflowContext の warnings フィールドはデフォルトで空リスト。"""
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
    )
    assert ctx.warnings == []
    assert isinstance(ctx.warnings, list)


async def test_emit_skip_appends_warning_and_calls_reporter():
    """_emit_skip は reporter / ctx.warnings / metrics 全てに伝播する。"""
    from src.services.pipeline_steps import _emit_skip

    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
    )
    reporter = MockReporter()

    _emit_skip(reporter, ctx, step="illustration", reason="book_id is None")

    # ctx.warnings に積まれる
    assert ctx.warnings == ["illustration: book_id is None"]
    # reporter に warning 通知
    assert any("illustration" in m and "book_id is None" in m for m, _ in reporter.messages)
    # reporter の level は warning
    assert all(level == "warning" for _, level in reporter.messages)


async def test_emit_skip_multiple_calls_append():
    """_emit_skip は複数回呼んでも上書きせず追記する。"""
    from src.services.pipeline_steps import _emit_skip

    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
    )
    reporter = MockReporter()

    _emit_skip(reporter, ctx, "catharsis", "book_id is None")
    _emit_skip(reporter, ctx, "marketing", "llm unavailable")

    assert ctx.warnings == [
        "catharsis: book_id is None",
        "marketing: llm unavailable",
    ]


# ---------------------------------------------------------------------------
# Step 10-12: IllustrationStep の実ロジック検証
# ---------------------------------------------------------------------------


async def test_illustration_step_disabled_short_circuits():
    """Step 10: enable_illustration=False で早期 return、ctx.warnings に記録。"""
    from src.services.pipeline_steps import IllustrationStep

    mock_engine = MockEngine()
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        enable_illustration=False,
    )

    result = await IllustrationStep().execute(ctx, mock_engine, mock_reporter)
    assert result is True
    # enable_illustration=False なら ctx.warnings に reason が積まれる
    assert "illustration" in ctx.warnings[0]
    # mock_engine.illustration_agent は IllustrationStep 内で参照されない (早期 return)


async def test_illustration_step_book_id_none_observable():
    """Step 11: book_id=None で skip → ctx.warnings に積まれる。"""
    from src.services.pipeline_steps import IllustrationStep

    mock_engine = MockEngine()
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        enable_illustration=True,
        illustration_settings={"enableIllustration": True},
        book_id=None,
    )

    result = await IllustrationStep().execute(ctx, mock_engine, mock_reporter)
    assert result is True
    assert any("illustration" in w and "book_id" in w for w in ctx.warnings)


async def test_illustration_step_settings_missing_short_circuits():
    """illustration_settings が空 + enableIllustration キー無しで skip。"""
    from src.services.pipeline_steps import IllustrationStep

    mock_engine = MockEngine()
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        enable_illustration=True,
        illustration_settings={},  # enableIllustration キー無し
        book_id=1,
    )

    result = await IllustrationStep().execute(ctx, mock_engine, mock_reporter)
    assert result is True
    assert any("enableIllustration" in w for w in ctx.warnings)


async def test_illustration_step_uses_engine_agent():
    """Step 12: 実 IllustrationStep が engine.illustration_agent を再利用する。

    - engine.illustration_agent.execute を AsyncMock 化
    - illustration_workflow は engine.illustration_agent から組立
    - 呼ばれたことを確認
    """
    from src.services.pipeline_steps import IllustrationStep
    from src.backend.workflows.illustration_workflow import IllustrationWorkflow

    mock_engine = MockEngine()
    mock_reporter = MockReporter()

    # engine に illustration_agent を生やす (Mock ではなく実 IllustrationWorkflow)
    mock_workflow = MagicMock(spec=IllustrationWorkflow)
    mock_workflow.execute = AsyncMock(
        return_value={"status": "success", "illustrations": [{"id": 1, "url": "/x.png"}]}
    )
    mock_engine.illustration_agent = MagicMock()
    mock_engine.illustration_workflow = mock_workflow

    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        enable_illustration=True,
        illustration_settings={"enableIllustration": True},
        book_id=42,
    )

    # 実 IllustrationStep を engine 経由の agent のみで動かすため、import 内部を patch
    import src.backend.workflows.illustration_workflow as ill_wf_mod

    with patch.object(ill_wf_mod, "IllustrationWorkflow", return_value=mock_workflow) as wf_cls:
        result = await IllustrationStep().execute(ctx, mock_engine, mock_reporter)

    assert result is True
    wf_cls.assert_called_once()
    mock_workflow.execute.assert_awaited_once()
    call_kwargs = mock_workflow.execute.await_args.kwargs
    assert call_kwargs["book_id"] == 42
    assert ctx.illustrations == [{"id": 1, "url": "/x.png"}]
    # 成功メッセージが reporter に
    assert any("挿絵生成完了" in m for m, _ in mock_reporter.messages)


# ---------------------------------------------------------------------------
# Step 15-18: MarketingStep 3 段フォールバック
# ---------------------------------------------------------------------------


async def test_marketing_step_disabled_short_circuits():
    """enable_marketing=False で skip、ctx.warnings に積まれる。"""
    from src.services.pipeline_steps import MarketingStep

    mock_engine = MockEngine()
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        enable_marketing=False,
        book_id=1,
    )

    result = await MarketingStep().execute(ctx, mock_engine, mock_reporter)
    assert result is True
    assert any("marketing" in w for w in ctx.warnings)


async def test_marketing_step_preset_path():
    """プリセットに title_templates がある時、それを採用する。"""
    from src.services.pipeline_steps import MarketingStep

    preset = {
        "marketing": {
            "catchphrase_templates": ["最強の物語！"],
            "tags": ["異世界", "最強", "無双"],
        },
        "titles": {"title_templates": ["王道の剣"]},
    }

    mock_engine = MockEngine()
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="王道",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        book_id=1,
    )

    with patch(
        "src.services.pipeline_steps.load_preset_for_pipeline", return_value=preset
    ):
        result = await MarketingStep().execute(ctx, mock_engine, mock_reporter)

    assert result is True
    assert ctx.title == "王道の剣"
    assert ctx.marketing_pack["catchphrase"] == "最強の物語！"
    assert ctx.marketing_pack["tags"] == ["異世界", "最強", "無双"]


async def test_marketing_step_llm_fallback():
    """プリセットに title_templates が無い時、LLM でタイトル生成。"""
    from src.services.pipeline_steps import MarketingStep

    mock_engine = MockEngine()
    mock_engine.llm.generate = AsyncMock(return_value="神秘のダンジョン")
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="ダンジョン",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        book_id=1,
        concept="底辺冒険者の逆襲",
    )

    with patch(
        "src.services.pipeline_steps.load_preset_for_pipeline", return_value={}
    ):
        result = await MarketingStep().execute(ctx, mock_engine, mock_reporter)

    assert result is True
    assert ctx.title == "神秘のダンジョン"
    mock_engine.llm.generate.assert_awaited_once()


async def test_marketing_step_template_fallback():
    """プリセット空 + LLM 例外 → 固定テンプレ {genre}の物語。"""
    from src.services.pipeline_steps import MarketingStep

    mock_engine = MockEngine()
    mock_engine.llm.generate = AsyncMock(side_effect=RuntimeError("LLM down"))
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="SF",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        book_id=1,
    )

    with patch(
        "src.services.pipeline_steps.load_preset_for_pipeline", return_value={}
    ):
        result = await MarketingStep().execute(ctx, mock_engine, mock_reporter)

    assert result is True
    assert ctx.title == "SFの物語"


async def test_marketing_step_archetype_key_missing_safe():
    """archetype_key が空でも default 扱いで KeyError にならない。"""
    from src.services.pipeline_steps import MarketingStep

    mock_engine = MockEngine()
    mock_engine.llm.generate = AsyncMock(return_value="")  # LLM 空 → テンプレへ
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="",  # 重要: 未設定
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        book_id=1,
    )

    with patch(
        "src.services.pipeline_steps.load_preset_for_pipeline", return_value={}
    ) as mock_load:
        result = await MarketingStep().execute(ctx, mock_engine, mock_reporter)

    assert result is True
    # archetype="default" で load が呼ばれた
    mock_load.assert_called_once_with("ファンタジー", "default")
    # LLM も空なのでテンプレ
    assert ctx.title == "ファンタジーの物語"


# ---------------------------------------------------------------------------
# Step 19-22: CatharsisAnalysisStep skip の観測化
# ---------------------------------------------------------------------------


async def test_catharsis_step_disabled_observable():
    """enable_catharsis_analysis=False で skip → ctx.warnings に積まれる。"""
    from src.services.pipeline_steps import CatharsisAnalysisStep

    mock_engine = MockEngine()
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        enable_catharsis_analysis=False,
        book_id=1,
    )

    result = await CatharsisAnalysisStep().execute(ctx, mock_engine, mock_reporter)
    assert result is True
    assert any("catharsis" in w and "enable_catharsis_analysis" in w for w in ctx.warnings)


async def test_catharsis_step_book_id_none_observable():
    """book_id=None で skip → ctx.warnings に積まれる (silent skip 撲滅)。"""
    from src.services.pipeline_steps import CatharsisAnalysisStep

    mock_engine = MockEngine()
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        enable_catharsis_analysis=True,
        book_id=None,
    )

    result = await CatharsisAnalysisStep().execute(ctx, mock_engine, mock_reporter)
    assert result is True
    assert any("catharsis" in w and "book_id" in w for w in ctx.warnings)


async def test_catharsis_step_real_analysis_runs():
    """Step 22: 実 CatharsisAnalysisStep が ctx.catharsis_pattern を設定する。"""
    from src.services.pipeline_steps import CatharsisAnalysisStep

    mock_engine = MockEngine()
    # 3 プロット分の tension 履歴
    plot1 = MagicMock(tension=40)
    plot2 = MagicMock(tension=80)
    plot3 = MagicMock(tension=30)
    mock_engine.repo.plot.get_all_plots = AsyncMock(
        return_value=[plot1, plot2, plot3]
    )
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=3,
        initial_limit=3,
        word_count=1000,
        enable_catharsis_analysis=True,
        book_id=42,
    )

    result = await CatharsisAnalysisStep().execute(ctx, mock_engine, mock_reporter)
    assert result is True
    # catharsis_pattern が dict で詰まる (WavePatternAnalyzer の出力キー)
    assert isinstance(ctx.catharsis_pattern, dict)
    assert len(ctx.catharsis_pattern) > 0
    # easy_parameters にも反映 (PlanStep と違い _save_easy_parameters 経由なので空でも OK)


# ---------------------------------------------------------------------------
# Step 23-24: PackageStep 防御
# ---------------------------------------------------------------------------


async def test_package_step_with_marketing_disabled():
    """enable_marketing=False のまま PackageStep まで到達しても AttributeError なし。"""
    from src.services.pipeline_steps import PackageStep

    mock_engine = MockEngine()
    # engine.repo.get_book を AsyncMock 化
    mock_book = MagicMock()
    mock_book.title = "事前取得タイトル"
    mock_engine.repo.get_book = AsyncMock(return_value=mock_book)
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        book_id=7,
        enable_marketing=False,  # 重要: marketing_pack は未生成
    )
    assert ctx.marketing_pack == {}

    result = await PackageStep().execute(ctx, mock_engine, mock_reporter)
    assert result is True
    # タイトルは repo から補完される
    assert ctx.title == "事前取得タイトル"
    # marketing_pack はデフォルトシェルで補完される
    assert ctx.marketing_pack["title"] == "事前取得タイトル"
    assert "package" in " ".join(ctx.warnings)


async def test_package_step_book_id_none_returns_false():
    """book_id=None で PackageStep は False 返却 (早期 return)。"""
    from src.services.pipeline_steps import PackageStep

    mock_engine = MockEngine()
    mock_reporter = MockReporter()
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        book_id=None,
    )

    result = await PackageStep().execute(ctx, mock_engine, mock_reporter)
    assert result is False
    assert any("package" in w and "book_id" in w for w in ctx.warnings)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])