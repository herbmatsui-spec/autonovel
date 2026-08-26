"""
src/backend/workflows - ワークフローパッケージ
"""

__all__ = [
    "BaseWorkflow",
    "ChapterImportWorkflow",
    "CritiqueOptimizationWorkflow",
    "EpisodeWritingWorkflow",
    "FullAutoWorkflow",
    "LogicalAuditWorkflow",
    "MarketingGenerationWorkflow",
    "PlanGenerationWorkflow",
    "PlotExpansionWorkflow",
    "PlotRebuildWorkflow",
    "RefineEroticWorkflow",
    "RetryFailedEpisodesWorkflow",
]

_WORKFLOW_MAP = {
    "BaseWorkflow": ".base_workflow",
    "ChapterImportWorkflow": ".chapter_import_workflow",
    "CritiqueOptimizationWorkflow": ".critique_optimization_workflow",
    "EpisodeWritingWorkflow": ".episode_writing_workflow",
    "FullAutoWorkflow": ".full_auto_workflow",
    "LogicalAuditWorkflow": ".logical_audit_workflow",
    "MarketingGenerationWorkflow": ".marketing_generation_workflow",
    "PlanGenerationWorkflow": ".plan_generation_workflow",
    "PlotExpansionWorkflow": ".plot_expansion_workflow",
    "PlotRebuildWorkflow": ".plot_rebuild_workflow",
    "RefineEroticWorkflow": ".refine_erotic_workflow",
    "RetryFailedEpisodesWorkflow": ".retry_failed_episodes_workflow",
}


def __getattr__(name: str):
    if name in _WORKFLOW_MAP:
        import importlib
        module = importlib.import_module(_WORKFLOW_MAP[name], __package__)
        return getattr(module, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

