"""Anti-AI Detection & Correction module.

Detects LLM-generated "fingerprints" in draft text and automatically
rewrites them to make the prose read as if a human wrote it.

Public surface::

    from src.services.anti_ai import (
        AntiAIDetectionResult, AICategory, Severity, ViolationSpan,
        RuleBasedAntiAIDetector,
        AntiAICorrector,
        AntiAILoopController,
        LoopResult,
    )
"""

from src.services.anti_ai.models import (
    AICategory,
    AntiAIDetectionResult,
    CorrectionHistory,
    Severity,
    ViolationSpan,
)
from src.services.anti_ai.orchestrator import RuleBasedAntiAIDetector
from src.services.anti_ai.correction_pipeline import AntiAICorrector
from src.services.anti_ai.loop_controller import AntiAILoopController, LoopResult

__all__ = [
    "AICategory",
    "AntiAIDetectionResult",
    "AntiAICorrector",
    "AntiAILoopController",
    "CorrectionHistory",
    "LoopResult",
    "RuleBasedAntiAIDetector",
    "Severity",
    "ViolationSpan",
]
