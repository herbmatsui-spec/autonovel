"""Mapping between Beat domain models and grammar Terminal symbols."""

from src.narrative_balancer.grammar.symbols import Terminal
from src.narrative_balancer.models import Beat, BeatType


def beat_to_terminal(beat: Beat) -> Terminal:
    """Map a Beat model into a grammar Terminal symbol."""
    bt = beat.beat_type
    mapping = {
        BeatType.SETUP: Terminal.SETUP,
        BeatType.RISING: Terminal.RISING,
        BeatType.MIDPOINT_DISASTER: Terminal.MIDPOINT_DISASTER,
        BeatType.FALLOUT: Terminal.FALLOUT,
        BeatType.STAGNATION: Terminal.STAGNATION,
        BeatType.RECOVERY: Terminal.RECOVERY,
        BeatType.CLIMAX: Terminal.CLIMAX,
        BeatType.RESOLUTION: Terminal.RESOLUTION,
        BeatType.DAILY: Terminal.DAILY,
        BeatType.BATTLE: Terminal.BATTLE,
        BeatType.PAYOFF: Terminal.PAYOFF,
    }
    return mapping.get(bt, Terminal.SETUP)


def terminal_to_beat(terminal: Terminal, episode: int) -> Beat:
    """Generate a Beat model from a grammar Terminal symbol."""
    tension_map = {
        Terminal.SETUP: 4.0,
        Terminal.RISING: 6.5,
        Terminal.MIDPOINT_DISASTER: 9.0,
        Terminal.FALLOUT: 4.5,
        Terminal.STAGNATION: 3.0,
        Terminal.RECOVERY: 6.0,
        Terminal.CLIMAX: 9.5,
        Terminal.RESOLUTION: 5.0,
        Terminal.DAILY: 3.5,
        Terminal.BATTLE: 8.0,
        Terminal.PAYOFF: 7.5,
        Terminal.BASE_COLLAPSE: 9.0,
        Terminal.ALLY_BETRAYAL: 9.0,
        Terminal.FALSE_VICTORY: 8.5,
        Terminal.REPEAT_QUEST: 3.0,
        Terminal.SLICE_OF_LIFE: 3.0,
        Terminal.FAKE_PROGRESS: 3.5,
    }

    type_map = {
        Terminal.SETUP: BeatType.SETUP,
        Terminal.RISING: BeatType.RISING,
        Terminal.MIDPOINT_DISASTER: BeatType.MIDPOINT_DISASTER,
        Terminal.FALLOUT: BeatType.FALLOUT,
        Terminal.STAGNATION: BeatType.STAGNATION,
        Terminal.RECOVERY: BeatType.RECOVERY,
        Terminal.CLIMAX: BeatType.CLIMAX,
        Terminal.RESOLUTION: BeatType.RESOLUTION,
        Terminal.DAILY: BeatType.DAILY,
        Terminal.BATTLE: BeatType.BATTLE,
        Terminal.PAYOFF: BeatType.PAYOFF,
        Terminal.BASE_COLLAPSE: BeatType.MIDPOINT_DISASTER,
        Terminal.ALLY_BETRAYAL: BeatType.MIDPOINT_DISASTER,
        Terminal.FALSE_VICTORY: BeatType.MIDPOINT_DISASTER,
        Terminal.REPEAT_QUEST: BeatType.STAGNATION,
        Terminal.SLICE_OF_LIFE: BeatType.DAILY,
        Terminal.FAKE_PROGRESS: BeatType.STAGNATION,
    }

    t_val = tension_map.get(terminal, 5.0)
    b_type = type_map.get(terminal, BeatType.SETUP)

    return Beat(
        episode=episode,
        tension=t_val,
        beat_type=b_type,
        title=f"第{episode}話",
        summary=f"文法展開ビート: {terminal.value}",
    )
