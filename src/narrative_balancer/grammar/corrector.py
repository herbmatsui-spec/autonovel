"""Midpoint plot intervention corrector using grammar templates."""

from typing import List
from src.narrative_balancer.grammar.symbols import Terminal
from src.narrative_balancer.grammar.beat_mapping import terminal_to_beat
from src.narrative_balancer.models import Beat, BeatType


def force_midpoint_correction(beats: List[Beat], ep: int = 20) -> List[Beat]:
    """Ensure episode `ep` serves as a disruptive Midpoint Disaster event."""
    if not beats:
        return beats

    new_beats = [b.model_copy(deep=True) for b in beats]
    target_idx = min(len(new_beats) - 1, max(0, ep - 1))

    current = new_beats[target_idx]
    if current.beat_type != BeatType.MIDPOINT_DISASTER:
        disaster_beat = terminal_to_beat(Terminal.BASE_COLLAPSE, ep)
        disaster_beat.title = current.title or f"第{ep}話 拠点陥落・中盤クライシス"
        disaster_beat.summary = "本拠地が急襲され壊滅的打撃を被る。仲間の一人が離脱。"
        disaster_beat.tension = 9.0
        new_beats[target_idx] = disaster_beat

    return new_beats
