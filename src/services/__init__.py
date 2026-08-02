"""src/services/__init__.py
Re-exports for ease of import.
"""

from .erotic_afterglow_evaluator import AfterglowEvaluator
from .ncs_calibration import NarrativeCoherenceScorer  # Renamed to avoid conflict
from .safe_replace import SafeReplacer

__all__ = [
    "AfterglowEvaluator",
    "NarrativeCoherenceScorer",  # Renamed for clarity
    "SafeReplacer",
]
