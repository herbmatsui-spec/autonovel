"""Variable schema for CP-SAT solver."""

from typing import Dict, List, Any

try:
    from ortools.sat.python import cp_model
except ImportError:
    cp_model = None

from src.narrative_balancer.models import BeatType


BEAT_TYPE_MAP = {bt: idx for idx, bt in enumerate(BeatType)}
INV_BEAT_TYPE_MAP = {idx: bt for idx, bt in enumerate(BeatType)}


class CSPVariables:
    """Encapsulates CP-SAT decision variables for the narrative sequence."""

    def __init__(
        self,
        model: Any,
        n_episodes: int = 40,
        characters: List[str] = None,
    ):
        if cp_model is None:
            raise ImportError("ortools is required for CSPVariables. Install with `pip install ortools`.")
        self.n_episodes = n_episodes
        self.characters = characters or ["Protagonist", "Rival", "Mentor"]

        # Tension integer variable: 1 to 10
        self.tension: List[Any] = [
            model.NewIntVar(1, 10, f"tension_{i}") for i in range(n_episodes)
        ]

        # Beat type variable: 0 to len(BeatType)-1
        num_types = len(BeatType)
        self.beat_type: List[cp_model.IntVar] = [
            model.NewIntVar(0, num_types - 1, f"beat_type_{i}") for i in range(n_episodes)
        ]

        # Defeat flag (boolean)
        self.defeat: List[cp_model.IntVar] = [
            model.NewBoolVar(f"defeat_{i}") for i in range(n_episodes)
        ]

        # Foreshadowing setup & payoff flags (boolean)
        self.setup: List[cp_model.IntVar] = [
            model.NewBoolVar(f"setup_{i}") for i in range(n_episodes)
        ]
        self.payoff: List[cp_model.IntVar] = [
            model.NewBoolVar(f"payoff_{i}") for i in range(n_episodes)
        ]

        # Character presence: dict mapping char -> list of BoolVar
        self.char_presence: Dict[str, List[cp_model.IntVar]] = {}
        for ch in self.characters:
            self.char_presence[ch] = [
                model.NewBoolVar(f"char_{ch}_ep_{i}") for i in range(n_episodes)
            ]

        # Auxiliary: Disaster beat indicator
        self.is_disaster: List[cp_model.IntVar] = [
            model.NewBoolVar(f"is_disaster_{i}") for i in range(n_episodes)
        ]
        disaster_idx = BEAT_TYPE_MAP[BeatType.DISASTER]
        mid_disaster_idx = BEAT_TYPE_MAP[BeatType.MIDPOINT_DISASTER]

        for i in range(n_episodes):
            b_is_d = model.NewBoolVar(f"b_dis_{i}")
            b_is_md = model.NewBoolVar(f"b_mdd_{i}")
            model.Add(self.beat_type[i] == disaster_idx).OnlyEnforceIf(b_is_d)
            model.Add(self.beat_type[i] != disaster_idx).OnlyEnforceIf(b_is_d.Not())
            model.Add(self.beat_type[i] == mid_disaster_idx).OnlyEnforceIf(b_is_md)
            model.Add(self.beat_type[i] != mid_disaster_idx).OnlyEnforceIf(b_is_md.Not())
            # is_disaster[i] <=> (b_is_d OR b_is_md)
            model.AddBoolOr([b_is_d, b_is_md]).OnlyEnforceIf(self.is_disaster[i])
            model.AddBoolAnd([b_is_d.Not(), b_is_md.Not()]).OnlyEnforceIf(self.is_disaster[i].Not())
