
import pytest

from src.backend.workflows import WORKFLOW_REGISTRY


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
    workflow = workflow_cls(engine)

    result = await workflow.execute(
        reporter=None,
        book_id=1,
        ep_num=2,
        import_text="test content",
        do_refine=True
    )

    assert result == {"status": "success"}
