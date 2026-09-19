"""Terminal and NonTerminal symbols for narrative grammar."""

from enum import Enum


class Terminal(str, Enum):
    """Terminal symbols representing concrete episode beat occurrences."""
    SETUP = "SETUP"
    RISING = "RISING"
    MIDPOINT_DISASTER = "MIDPOINT_DISASTER"
    FALLOUT = "FALLOUT"
    STAGNATION = "STAGNATION"
    RECOVERY = "RECOVERY"
    CLIMAX = "CLIMAX"
    RESOLUTION = "RESOLUTION"
    DAILY = "DAILY"
    BATTLE = "BATTLE"
    PAYOFF = "PAYOFF"
    BASE_COLLAPSE = "BASE_COLLAPSE"
    ALLY_BETRAYAL = "ALLY_BETRAYAL"
    FALSE_VICTORY = "FALSE_VICTORY"
    REPEAT_QUEST = "REPEAT_QUEST"
    SLICE_OF_LIFE = "SLICE_OF_LIFE"
    FAKE_PROGRESS = "FAKE_PROGRESS"


class NonTerminal(str, Enum):
    """NonTerminal symbols representing abstract narrative structural units."""
    STORY = "STORY"
    QUARTER = "QUARTER"
    ACT1 = "ACT1"
    ACT2A = "ACT2A"
    ACT2B = "ACT2B"
    ACT3 = "ACT3"
    MIDPOINT_DISASTER_RULE = "MIDPOINT_DISASTER_RULE"
    STAGNATION_RULE = "STAGNATION_RULE"
    DISASTER_EVENT = "DISASTER_EVENT"
    STAGNANT_EVENT = "STAGNANT_EVENT"
