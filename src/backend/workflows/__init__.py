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
    "WORKFLOW_REGISTRY",
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


def _get_workflow_registry():
    import importlib
    reg = {}
    key_mapping = {
        "full_auto_workflow": ("FullAutoWorkflow", ".full_auto_workflow"),
        "episode_writing_workflow": ("EpisodeWritingWorkflow", ".episode_writing_workflow"),
        "plan_generation_workflow": ("PlanGenerationWorkflow", ".plan_generation_workflow"),
        "plot_expansion_workflow": ("PlotExpansionWorkflow", ".plot_expansion_workflow"),
        "plot_rebuild_workflow": ("PlotRebuildWorkflow", ".plot_rebuild_workflow"),
        "run_critique_optimization_workflow": ("CritiqueOptimizationWorkflow", ".critique_optimization_workflow"),
        "retry_failed_episodes_workflow": ("RetryFailedEpisodesWorkflow", ".retry_failed_episodes_workflow"),
        "chapter_import_workflow": ("ChapterImportWorkflow", ".chapter_import_workflow"),
        "marketing_generation_workflow": ("MarketingGenerationWorkflow", ".marketing_generation_workflow"),
        "refine_erotic_workflow": ("RefineEroticWorkflow", ".refine_erotic_workflow"),
        "logical_audit_workflow": ("LogicalAuditWorkflow", ".logical_audit_workflow"),
    }
    for k, (cls_name, mod_path) in key_mapping.items():
        try:
            mod = importlib.import_module(mod_path, __package__)
            reg[k] = getattr(mod, cls_name)
        except Exception:
            pass
    return reg


WORKFLOW_REGISTRY = _get_workflow_registry()


def __getattr__(name: str):
    if name == "WORKFLOW_REGISTRY":
        return WORKFLOW_REGISTRY
    if name in _WORKFLOW_MAP:
        import importlib
        module = importlib.import_module(_WORKFLOW_MAP[name], __package__)
        return getattr(module, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

