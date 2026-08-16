from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from prompts.manager import PromptManager
    from src.agents.audit import LogicalAuditor
    from src.agents.MarketingAgent import MarketingAgent
    from src.agents.PlanningAgent import PlanningAgent
    from src.agents.plot import PlotAgent
    from src.agents.WritingAgent import WritingAgent
    from src.backend.engine_context import ContextManager
    from src.backend.engine_critique import CritiqueAgent
    from src.backend.engine_narrative import NarrativeController
    from src.backend.engine_style_rag import StyleRagManager
    from src.backend.sanitizer import TextFormatter
    from src.services.bible_service import WorldBibleGenerator


@dataclass
class EngineDeps:
    planner: Optional["PlanningAgent"] = None
    writer: Optional["WritingAgent"] = None
    pm: Optional["PromptManager"] = None
    ctx_mgr: Optional["ContextManager"] = None
    formatter: Optional["TextFormatter"] = None
    validator: Optional["LogicalAuditor"] = None
    auditor: Optional["LogicalAuditor"] = None
    narrative: Optional["NarrativeController"] = None
    critique: Optional["CritiqueAgent"] = None
    marketing: Optional["MarketingAgent"] = None
    bible_agent: Optional["WorldBibleGenerator"] = None
    plot_agent: Optional["PlotAgent"] = None
    style_rag: Optional["StyleRagManager"] = None
