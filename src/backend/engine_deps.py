from dataclasses import dataclass
from typing import Optional

from src.core.interfaces import (
    IContextManager,
    ICritiqueAgent,
    ILogicalAuditor,
    IMarketingAgent,
    INarrativeController,
    IPlanningAgent,
    IPlotAgent,
    IPromptManager,
    IStyleRagManager,
    ITextFormatter,
    IWorldBibleGenerator,
    IWritingAgent,
)


@dataclass
class EngineDeps:
    planner: Optional[IPlanningAgent] = None
    writer: Optional[IWritingAgent] = None
    pm: Optional[IPromptManager] = None
    ctx_mgr: Optional[IContextManager] = None
    formatter: Optional[ITextFormatter] = None
    validator: Optional[ILogicalAuditor] = None
    auditor: Optional[ILogicalAuditor] = None
    narrative: Optional[INarrativeController] = None
    critique: Optional[ICritiqueAgent] = None
    marketing: Optional[IMarketingAgent] = None
    bible_agent: Optional[IWorldBibleGenerator] = None
    plot_agent: Optional[IPlotAgent] = None
    style_rag: Optional[IStyleRagManager] = None
