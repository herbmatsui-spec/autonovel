"""Validation routines for structural quarter boundaries in story grammar."""

from typing import List
from src.narrative_balancer.models import Beat, BeatType


def validate_quarter_boundaries(beats: List[Beat]) -> List[str]:
    """Validate quarterly structural requirements across the narrative sequence."""
    violations: List[str] = []
    n = len(beats)
    if n < 4:
        return violations

    q_size = n // 4

    # Quarter 2 (Midpoint section)
    q2_beats = beats[q_size:q_size * 2]
    has_disaster = any(b.beat_type in (BeatType.MIDPOINT_DISASTER, BeatType.DISASTER, BeatType.BATTLE) for b in q2_beats)
    max_q2_tension = max((b.tension for b in q2_beats), default=0.0)

    if not has_disaster and max_q2_tension < 7.0:
        violations.append("Quarter 2 lacks a midpoint crisis, battle or high tension turn (max tension < 7.0)")

    # Quarter 4 (Climax section)
    q4_beats = beats[q_size * 3:]
    has_climax = any(b.beat_type == BeatType.CLIMAX for b in q4_beats)
    if not has_climax:
        violations.append("Quarter 4 lacks a designated CLIMAX beat")

    return violations
