from .base_workflow import BaseWorkflow
from .chapter_import_workflow import ChapterImportWorkflow
from .critique_optimization_workflow import CritiqueOptimizationWorkflow
from .easy_mode_workflow import EasyModeWorkflow
from .episode_writing_workflow import EpisodeWritingWorkflow
from .full_auto_workflow import FullAutoWorkflow
from .logical_audit_workflow import LogicalAuditWorkflow
from .marketing_generation_workflow import MarketingGenerationWorkflow
from .plan_generation_workflow import PlanGenerationWorkflow
from .plot_expansion_workflow import PlotExpansionWorkflow
from .plot_rebuild_workflow import PlotRebuildWorkflow
from .refine_erotic_workflow import RefineEroticWorkflow
from .reverse_plot_workflow import ReversePlotGenerationWorkflow
from .retry_failed_episodes_workflow import RetryFailedEpisodesWorkflow

__all__ = [
    "BaseWorkflow",
    "ChapterImportWorkflow",
    "CritiqueOptimizationWorkflow",
    "EasyModeWorkflow",
    "EpisodeWritingWorkflow",
    "FullAutoWorkflow",
    "LogicalAuditWorkflow",
    "MarketingGenerationWorkflow",
    "PlanGenerationWorkflow",
    "PlotExpansionWorkflow",
    "PlotRebuildWorkflow",
    "RefineEroticWorkflow",
    "ReversePlotGenerationWorkflow",
    "RetryFailedEpisodesWorkflow",
]

WORKFLOW_REGISTRY = {
    "easy_mode_workflow": EasyModeWorkflow,
    "full_auto_workflow": FullAutoWorkflow,
    "plan_generation_workflow": PlanGenerationWorkflow,
    "plot_expansion_workflow": PlotExpansionWorkflow,
    "retry_failed_episodes_workflow": RetryFailedEpisodesWorkflow,
    "episode_writing_workflow": EpisodeWritingWorkflow,
    "plot_rebuild_workflow": PlotRebuildWorkflow,
    "chapter_import_workflow": ChapterImportWorkflow,
    "run_critique_optimization_workflow": CritiqueOptimizationWorkflow,
    "run_logical_audit_workflow": LogicalAuditWorkflow,
    "marketing_generation_workflow": MarketingGenerationWorkflow,
    "refine_erotic_workflow": RefineEroticWorkflow,
    "reverse_plot_generation_workflow": ReversePlotGenerationWorkflow,
}

