from .base_workflow import BaseWorkflow
from .chapter_import_workflow import ChapterImportWorkflow
from .critique_optimization_workflow import CritiqueOptimizationWorkflow
from .episode_writing_workflow import EpisodeWritingWorkflow
from .full_auto_workflow import FullAutoWorkflow
from .logical_audit_workflow import LogicalAuditWorkflow
from .plan_generation_workflow import PlanGenerationWorkflow
from .plot_expansion_workflow import PlotExpansionWorkflow
from .plot_rebuild_workflow import PlotRebuildWorkflow
from .retry_failed_episodes_workflow import RetryFailedEpisodesWorkflow

WORKFLOW_REGISTRY = {
    "full_auto_workflow": FullAutoWorkflow,
    "plan_generation_workflow": PlanGenerationWorkflow,
    "plot_expansion_workflow": PlotExpansionWorkflow,
    "retry_failed_episodes_workflow": RetryFailedEpisodesWorkflow,
    "episode_writing_workflow": EpisodeWritingWorkflow,
    "plot_rebuild_workflow": PlotRebuildWorkflow,
    "chapter_import_workflow": ChapterImportWorkflow,
    "run_critique_optimization_workflow": CritiqueOptimizationWorkflow,
    "run_logical_audit_workflow": LogicalAuditWorkflow,
}

