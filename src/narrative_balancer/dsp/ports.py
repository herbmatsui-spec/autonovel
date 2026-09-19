"""DSP Tension Balancer interface protocols."""

from typing import List, Protocol, runtime_checkable
from src.narrative_balancer.dsp.models import Beat, SagDetection


@runtime_checkable
class TensionAnalyzer(Protocol):
    """Protocol for detecting sag and analyzing tension curves."""

    def analyze(self, beats: List[Beat]) -> List[SagDetection]:
        """Analyze beats and return detected sag events."""
        ...


@runtime_checkable
class Corrector(Protocol):
    """Protocol for applying narrative/tension corrections."""

    def correct(self, beats: List[Beat]) -> List[Beat]:
        """Apply balancing corrections to the input beats."""
        ...
