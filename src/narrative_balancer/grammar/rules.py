"""Context-Free Grammar rules for narrative plot architectures."""

from typing import Dict, List, Union
from src.narrative_balancer.grammar.symbols import NonTerminal, Terminal

Symbol = Union[NonTerminal, Terminal]
Production = List[Symbol]

GRAMMAR: Dict[NonTerminal, List[Production]] = {
    NonTerminal.STORY: [
        [NonTerminal.ACT1, NonTerminal.ACT2A, NonTerminal.ACT2B, NonTerminal.ACT3],
        [NonTerminal.QUARTER, NonTerminal.QUARTER, NonTerminal.QUARTER, NonTerminal.QUARTER],
    ],
    NonTerminal.ACT1: [
        [Terminal.SETUP, Terminal.RISING, Terminal.BATTLE],
        [Terminal.SETUP, Terminal.DAILY, Terminal.RISING],
        [Terminal.SETUP, Terminal.RISING],
    ],
    NonTerminal.ACT2A: [
        [Terminal.RISING, NonTerminal.MIDPOINT_DISASTER_RULE, Terminal.FALLOUT],
        [Terminal.RISING, Terminal.MIDPOINT_DISASTER, Terminal.RECOVERY],
        [Terminal.SETUP, NonTerminal.STAGNATION_RULE, Terminal.RECOVERY],
        [Terminal.RISING, Terminal.STAGNATION, Terminal.RECOVERY],
    ],
    NonTerminal.ACT2B: [
        [Terminal.FALLOUT, Terminal.RECOVERY, Terminal.BATTLE],
        [Terminal.RECOVERY, Terminal.PAYOFF, Terminal.RISING],
        [Terminal.FALLOUT, Terminal.BATTLE],
    ],
    NonTerminal.ACT3: [
        [Terminal.RISING, Terminal.CLIMAX, Terminal.RESOLUTION],
        [Terminal.BATTLE, Terminal.CLIMAX, Terminal.RESOLUTION],
        [Terminal.CLIMAX, Terminal.RESOLUTION],
    ],
    NonTerminal.MIDPOINT_DISASTER_RULE: [
        [Terminal.MIDPOINT_DISASTER],
        [Terminal.BASE_COLLAPSE],
        [Terminal.ALLY_BETRAYAL],
        [Terminal.FALSE_VICTORY],
    ],
    NonTerminal.STAGNATION_RULE: [
        [Terminal.STAGNATION],
        [Terminal.REPEAT_QUEST],
        [Terminal.SLICE_OF_LIFE],
        [Terminal.FAKE_PROGRESS],
    ],
    NonTerminal.QUARTER: [
        [Terminal.SETUP, Terminal.RISING, Terminal.BATTLE, Terminal.PAYOFF],
        [Terminal.RISING, Terminal.MIDPOINT_DISASTER, Terminal.FALLOUT, Terminal.RECOVERY],
        [Terminal.SETUP, Terminal.DAILY, Terminal.RISING, Terminal.PAYOFF],
        [Terminal.BATTLE, Terminal.RISING, Terminal.CLIMAX, Terminal.RESOLUTION],
    ],
}
