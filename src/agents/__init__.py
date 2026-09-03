# agents/__init__.py
from src.agents.audit import LogicalAuditor
from src.agents.base import BaseAgent
from src.agents.bible import BibleAgent
from src.agents.context_builder_agent import ContextBuilderAgent
from src.agents.marketing import MarketingAgent
from src.agents.orchestrator import AgentContext, AgentName, AgentResult, Orchestrator
from src.agents.event_bus import AgentEvent, EventBus

# from src.agents.audit import InternalLogicValidator, DeAIAuditor, PlotIntegrityMonitor, FastPlotScreener, AbilityConsistencyChecker, PlanAuditor
from src.agents.planning import PlanningAgent  # 企画・アーク生成 (generate_arcs) を担当
from src.agents.plot import PlotAgent  # プロット展開 (expand_plots) を担当
from src.agents.writing import WritingAgent

__all__ = [
    "BaseAgent",
    "LogicalAuditor",
    "BibleAgent",
    "ContextBuilderAgent",
    "PlotAgent",
    "PlanningAgent",
    "PlanAuditor",
    "WritingAgent",
    "MarketingAgent",
    "AgentName",
    "AgentContext",
    "AgentResult",
    "Orchestrator",
    "AgentEvent",
    "EventBus",
]
