from src.backend.workflows import WORKFLOW_REGISTRY, BaseWorkflow

def test_all_workflows_registered():
    """全10ワークフローがレジストリに登録されていること"""
    expected_keys = [
        "full_auto_workflow",
        "episode_writing_workflow",
        "plan_generation_workflow",
        "plot_expansion_workflow",
        "plot_rebuild_workflow",
        "run_critique_optimization_workflow",
        "retry_failed_episodes_workflow",
        "chapter_import_workflow",
        "marketing_generation_workflow",
        "refine_erotic_workflow",
    ]
    for key in expected_keys:
        assert key in WORKFLOW_REGISTRY, f"Workflow '{key}' not in WORKFLOW_REGISTRY"
        assert issubclass(WORKFLOW_REGISTRY[key], BaseWorkflow)
