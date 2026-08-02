"""
kernels/__init__.py - Package entry point
"""

__version__ = "1.0.0"

# パッケージレベルでのエクスポート
from .base import KernelBase, KernelContext, KernelState
from .connection import Connection
from .connection_kernel import ConnectionKernel
from .dialogue import DialogueManager
from .engines import GenerationEngine
from .enigma import EnigmaEngine, unravel_mystery
from .graph import NarrativeState, NarrativeStateGraph, NarrativeStateManager
from .hegemony import HegemonyGenerator
from .interaction_config import InteractionConfig
from .interaction_formatter import InteractionFormatter, InteractionFormatterFactory
from .interaction_manager import InteractionManager
from .interaction_trigger import InteractionTrigger, TriggerConfig, TriggerType
from .memory import MemoryManager
from .pipeline import PipelineManager
from .pov import POVManager, POVType
from .preset_triggers import PresetTriggers
from .resonance import ResonanceEngine
from .serenity import SerenityManager, TransitionType

__all__ = [
    "KernelBase",
    "KernelState",
    "KernelContext",
    "Connection",
    "ConnectionKernel",
    "DialogueManager",
    "GenerationEngine",
    "EnigmaEngine",
    "unravel_mystery",
    "NarrativeState",
    "NarrativeStateGraph",
    "NarrativeStateManager",
    "HegemonyGenerator",
    "InteractionConfig",
    "InteractionFormatter",
    "InteractionFormatterFactory",
    "InteractionManager",
    "InteractionTrigger",
    "TriggerType",
    "TriggerConfig",
    "MemoryManager",
    "PipelineManager",
    "POVManager",
    "POVType",
    "PresetTriggers",
    "ResonanceEngine",
    "SerenityManager",
    "TransitionType",
]
