# agents/__init__.py
from src.agents.audit import LogicalAuditor
from src.agents.base import BaseAgent
from src.agents.bible import BibleAgent
from src.agents.debate import NullDebateAgent
from src.agents.marketing import MarketingAgent

# from src.agents.audit import InternalLogicValidator, DeAIAuditor, PlotIntegrityMonitor, FastPlotScreener, AbilityConsistencyChecker, PlanAuditor
from src.agents.planning import PlanningAgent
from src.agents.plot import PlotAgent
from src.agents.writing import WritingAgent

__all__ = [
    "BaseAgent",
    "LogicalAuditor",
    "BibleAgent",
    "PlotAgent",
    "PlanningAgent",
    "PlanAuditor",
    "WritingAgent",
    "MarketingAgent",
]

