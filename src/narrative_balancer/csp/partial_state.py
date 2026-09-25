"""Partial plot state representation for minimal-change narrative repair."""

from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field, ConfigDict
from src.narrative_balancer.models import Beat


class PartialPlotState(BaseModel):
    """Encapsulates confirmed episodes and undetermined episodes."""
    model_config = ConfigDict(extra="ignore")

    total_episodes: int = Field(default=40, ge=1)
    confirmed_beats: Dict[int, Beat] = Field(default_factory=dict, description="1-based episode mapping")
    unconfirmed_episodes: Set[int] = Field(default_factory=set)

    @classmethod
    def from_beats(cls, beats: List[Beat], total_episodes: Optional[int] = None) -> "PartialPlotState":
        total = total_episodes or (max((b.episode for b in beats), default=40))
        confirmed = {b.episode: b for b in beats}
        all_eps = set(range(1, total + 1))
        unconfirmed = all_eps - set(confirmed.keys())
        return cls(total_episodes=total, confirmed_beats=confirmed, unconfirmed_episodes=unconfirmed)

    def merge_solution(self, solved_beats: List[Beat]) -> "PartialPlotState":
        """Merge solved beats into this state, completing unconfirmed episodes."""
        new_confirmed = dict(self.confirmed_beats)
        for b in solved_beats:
            new_confirmed[b.episode] = b
        return PartialPlotState(
            total_episodes=self.total_episodes,
            confirmed_beats=new_confirmed,
            unconfirmed_episodes=set(),
        )

    def to_beat_list(self) -> List[Beat]:
        """Convert state to an ordered list of beats sorted by episode number."""
        return [self.confirmed_beats[ep] for ep in sorted(self.confirmed_beats.keys())]
