import pytest

from src.backend.workflows import WORKFLOW_REGISTRY
from src.backend.workflows.plot_rebuild_workflow import PlotRebuildWorkflow
from src.core.null_objects import NullEngine
from src.models.plot import ArcBlueprint, ArcList


def test_workflow_registry():
    assert "full_auto_workflow" in WORKFLOW_REGISTRY
    assert "plan_generation_workflow" in WORKFLOW_REGISTRY
    assert "plot_expansion_workflow" in WORKFLOW_REGISTRY
    assert "retry_failed_episodes_workflow" in WORKFLOW_REGISTRY
    assert "episode_writing_workflow" in WORKFLOW_REGISTRY
    assert "plot_rebuild_workflow" in WORKFLOW_REGISTRY
    assert "chapter_import_workflow" in WORKFLOW_REGISTRY
    assert "run_critique_optimization_workflow" in WORKFLOW_REGISTRY


@pytest.mark.anyio
async def test_chapter_import_workflow_execution():
    from src.core.null_objects import NullEngine

    # NullEngineを使用
    engine = NullEngine()

    workflow_cls = WORKFLOW_REGISTRY["chapter_import_workflow"]
    workflow = workflow_cls(engine=engine)

    result = await workflow.execute(
        reporter=None, book_id=1, ep_num=2, import_text="test content", do_refine=True
    )

    assert result == {"status": "success"}


class _FakeArc(ArcBlueprint):
    def __init__(self, arc_num=1, start_ep=1, end_ep=3, title="弧", summary="概要"):
        super().__init__(
            arc_num=arc_num, start_ep=start_ep, end_ep=end_ep, title=title, summary=summary
        )


class _FakePlot:
    def __init__(self, ep_num):
        self.ep_num = ep_num

    def model_dump(self):
        return {"ep_num": self.ep_num}


class _FakePlanner:
    def __init__(self, fail=False):
        self._fail = fail

    async def generate_arcs(self, *args, **kwargs):
        if self._fail:
            raise RuntimeError("arc generation failed")
        return ArcList(arcs=[_FakeArc()])


class _FakePlotAgent:
    def __init__(self, fail=False):
        self._fail = fail

    async def expand_plots(self, *args, **kwargs):
        if self._fail:
            raise RuntimeError("expansion failed")
        return [_FakePlot(ep) for ep in range(1, 4)]


class _FakeRepo:
    async def get_book(self, book_id):
        class _Book:
            title = "テスト小説"
            current_branch_id = 1

        return _Book()


@pytest.mark.anyio
async def test_plot_rebuild_workflow_pipeline_success():
    from src.backend.background import StatusReporter

    workflow = PlotRebuildWorkflow(
        engine=NullEngine(),
        planner=_FakePlanner(),
        plot_agent=_FakePlotAgent(),
        repo=_FakeRepo(),
    )
    params = {
        "book_id": 1,
        "start_ep": 1,
        "new_total": 3,
        "new_keywords": "冒険",
        "trend_memo": "人気",
    }
    result = await workflow.execute(reporter=StatusReporter(), params=params)
    assert result["done"] is True
    assert result["count"] > 0
    assert len(result["arcs"]) == 1
    assert len(result["expanded"]) == 3
    assert result["metadata"]["start_ep"] == 1


@pytest.mark.anyio
async def test_plot_rebuild_workflow_arc_generation_failure():
    from src.backend.background import StatusReporter

    workflow = PlotRebuildWorkflow(
        engine=NullEngine(),
        planner=_FakePlanner(fail=True),
        plot_agent=_FakePlotAgent(),
        repo=_FakeRepo(),
    )
    params = {
        "book_id": 1,
        "start_ep": 1,
        "new_total": 3,
        "new_keywords": "冒険",
        "trend_memo": "人気",
    }
    result = await workflow.execute(reporter=StatusReporter(), params=params)
    assert result["done"] is False
    assert "error" in result
    assert result["count"] == 0


@pytest.mark.anyio
async def test_plot_rebuild_workflow_expansion_failure_degrades():
    from src.backend.background import StatusReporter

    workflow = PlotRebuildWorkflow(
        engine=NullEngine(),
        planner=_FakePlanner(),
        plot_agent=_FakePlotAgent(fail=True),
        repo=_FakeRepo(),
    )
    params = {
        "book_id": 1,
        "start_ep": 1,
        "new_total": 3,
        "new_keywords": "冒険",
        "trend_memo": "人気",
    }
    result = await workflow.execute(reporter=StatusReporter(), params=params)
    # ステップ3が失敗してもパイプラインは停止せず、空expandedで成功を返す
    assert result["done"] is True
    assert result["count"] == 0
    assert len(result["arcs"]) == 1
