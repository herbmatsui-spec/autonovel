"""Plot domain entity."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from enum import Enum

from src.domain.value_objects.ids import NovelId, PlotId
from src.domain.value_objects.text import Title, TextContent, MarkdownText
from src.domain.value_objects.scores import TensionScore


class PlotStatus(Enum):
    """Plot status enumeration."""
    PLANNED = "planned"
    WRITING = "writing"
    COMPLETED = "completed"
    REVISED = "revised"
    LOCKED = "locked"


class ChainPhase(Enum):
    """Story chain phase."""
    FRICITON = "Friction"
    TURN = "Turn"
    COUNTER_TURN = "CounterTurn"
    RESOLUTION = "Resolution"
    CATHARSIS = "Catharsis"
    MICRO_CATHARSIS = "MicroCatharsis"


@dataclass
class Plot:
    """Plot/Story outline entity for a specific episode."""
    id: PlotId
    novel_id: NovelId
    branch_id: NovelId
    episode_number: int
    title: Title
    summary: TextContent
    one_line_summary: str = ""
    detailed_blueprint: TextContent = field(default_factory=lambda: MarkdownText(""))
    thought_process: TextContent = field(default_factory=lambda: MarkdownText(""))
    tension_score: TensionScore = field(default_factory=lambda: TensionScore(value=50))
    catharsis: int = 0
    status: PlotStatus = PlotStatus.PLANNED
    scenes: List[str] = field(default_factory=list)
    is_catharsis: bool = False
    catharsis_type: str = "なし"
    love_meter: int = 0
    next_hook: str = "{}"
    misunderstanding_gap: str = ""
    lite_model_director_notes: str = ""
    script_content: str = ""
    current_chain_phase: ChainPhase = ChainPhase.FRICITON
    resolution_style: str = "Cheat"
    burned_cost_or_loot: str = "なし"
    antagonist_status: str = "現状維持"
    thematic_milestone: str = "なし"
    state_integrity_score: int = 100
    emotional_resonance_score: int = 0
    thematic_depth_score: int = 0
    literary_beauty_score: int = 0
    erotic_intensity: int = 0
    healed_fields: List[str] = field(default_factory=list)
    is_micro_catharsis: bool = False
    information_asymmetry_level: float = 0.0
    cost_score: float = 0.0
    qol_delta: int = 0
    discovery_item: str = ""
    sanctuary_event: str = ""
    is_locked: bool = False
    is_simulation: bool = False
    simulation_id: str = ""
    pov_character_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.episode_number < 1:
            raise ValueError("Episode number must be positive")

    @classmethod
    def create(
        cls,
        novel_id: NovelId,
        branch_id: NovelId,
        episode_number: int,
        title: str,
        summary: str = "",
    ) -> Plot:
        """Factory method to create a new plot."""
        plot_id = PlotId.generate()
        now = datetime.now()
        return cls(
            id=plot_id,
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=episode_number,
            title=Title(title),
            summary=MarkdownText(summary),
            tension_score=TensionScore(value=50),
            created_at=now,
            updated_at=now,
        )

    def update_content(
        self,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        one_line_summary: Optional[str] = None,
        detailed_blueprint: Optional[TextContent] = None,
        thought_process: Optional[TextContent] = None,
    ) -> None:
        """Update plot content."""
        if title is not None:
            self.title = Title(title)
        if summary is not None:
            self.summary = MarkdownText(summary)
        if one_line_summary is not None:
            self.one_line_summary = one_line_summary
        if detailed_blueprint is not None:
            self.detailed_blueprint = detailed_blueprint
        if thought_process is not None:
            self.thought_process = thought_process
        self.updated_at = datetime.now()

    def set_tension(self, value: int, delta: int = 0) -> None:
        """Set tension score."""
        self.tension_score = TensionScore(value=value, delta=delta)
        self.updated_at = datetime.now()

    def set_catharsis(self, value: int, catharsis_type: str = "") -> None:
        """Set catharsis level."""
        self.catharsis = value
        if catharsis_type:
            self.catharsis_type = catharsis_type
        self.is_catharsis = value >= 80
        self.updated_at = datetime.now()

    def change_status(self, status: PlotStatus) -> None:
        """Change plot status."""
        self.status = status
        self.updated_at = datetime.now()

    def lock(self) -> None:
        """Lock the plot from further changes."""
        self.is_locked = True
        self.updated_at = datetime.now()

    def unlock(self) -> None:
        """Unlock the plot."""
        self.is_locked = False
        self.updated_at = datetime.now()

    def set_chain_phase(self, phase: ChainPhase) -> None:
        """Set current chain phase."""
        self.current_chain_phase = phase
        self.updated_at = datetime.now()

    def add_scene(self, scene: str) -> None:
        """Add a scene to the plot."""
        self.scenes.append(scene)
        self.updated_at = datetime.now()

    def remove_scene(self, index: int) -> bool:
        """Remove a scene by index."""
        if 0 <= index < len(self.scenes):
            self.scenes.pop(index)
            self.updated_at = datetime.now()
            return True
        return False

    def update_scores(
        self,
        state_integrity: Optional[int] = None,
        emotional_resonance: Optional[int] = None,
        thematic_depth: Optional[int] = None,
        literary_beauty: Optional[int] = None,
        erotic_intensity: Optional[int] = None,
    ) -> None:
        """Update quality scores."""
        if state_integrity is not None:
            self.state_integrity_score = max(0, min(100, state_integrity))
        if emotional_resonance is not None:
            self.emotional_resonance_score = max(0, min(100, emotional_resonance))
        if thematic_depth is not None:
            self.thematic_depth_score = max(0, min(100, thematic_depth))
        if literary_beauty is not None:
            self.literary_beauty_score = max(0, min(100, literary_beauty))
        if erotic_intensity is not None:
            self.erotic_intensity = max(0, min(100, erotic_intensity))
        self.updated_at = datetime.now()

    def add_healed_field(self, field: str) -> None:
        """Add a healed field."""
        if field not in self.healed_fields:
            self.healed_fields.append(field)
            self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "branch_id": str(self.branch_id),
            "episode_number": self.episode_number,
            "title": str(self.title),
            "summary": self.summary.content,
            "one_line_summary": self.one_line_summary,
            "detailed_blueprint": self.detailed_blueprint.content,
            "thought_process": self.thought_process.content,
            "tension": self.tension_score.value,
            "tension_delta": self.tension_score.delta,
            "catharsis": self.catharsis,
            "status": self.status.value,
            "scenes": self.scenes,
            "is_catharsis": self.is_catharsis,
            "catharsis_type": self.catharsis_type,
            "love_meter": self.love_meter,
            "next_hook": self.next_hook,
            "misunderstanding_gap": self.misunderstanding_gap,
            "lite_model_director_notes": self.lite_model_director_notes,
            "script_content": self.script_content,
            "current_chain_phase": self.current_chain_phase.value,
            "resolution_style": self.resolution_style,
            "burned_cost_or_loot": self.burned_cost_or_loot,
            "antagonist_status": self.antagonist_status,
            "thematic_milestone": self.thematic_milestone,
            "state_integrity_score": self.state_integrity_score,
            "emotional_resonance_score": self.emotional_resonance_score,
            "thematic_depth_score": self.thematic_depth_score,
            "literary_beauty_score": self.literary_beauty_score,
            "erotic_intensity": self.erotic_intensity,
            "healed_fields": self.healed_fields,
            "is_micro_catharsis": self.is_micro_catharsis,
            "information_asymmetry_level": self.information_asymmetry_level,
            "cost_score": self.cost_score,
            "qol_delta": self.qol_delta,
            "discovery_item": self.discovery_item,
            "sanctuary_event": self.sanctuary_event,
            "is_locked": self.is_locked,
            "is_simulation": self.is_simulation,
            "simulation_id": self.simulation_id,
            "pov_character_id": self.pov_character_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Plot):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass(frozen=True, slots=True)
class PlotPoint:
    """Individual plot point within a plot."""
    id: PlotId
    plot_id: PlotId
    order: int
    description: TextContent
    type: str  # setup, conflict, climax, resolution, twist
    tension_contribution: int = 0
    is_major: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.order < 0:
            raise ValueError("Order must be non-negative")


@dataclass(frozen=True, slots=True)
class Arc:
    """Story arc spanning multiple episodes."""
    id: PlotId
    novel_id: NovelId
    name: str
    description: TextContent
    start_episode: int
    end_episode: int
    arc_type: str = "main"  # main, sub, character, romance, mystery
    status: PlotStatus = PlotStatus.PLANNED
    themes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Arc name cannot be empty")
        if self.start_episode < 1:
            raise ValueError("Start episode must be positive")
        if self.end_episode < self.start_episode:
            raise ValueError("End episode must be >= start episode")

    @classmethod
    def create(
        cls,
        novel_id: NovelId,
        name: str,
        description: TextContent,
        start_episode: int,
        end_episode: int,
        arc_type: str = "main",
    ) -> Arc:
        return cls(
            id=PlotId.generate(),
            novel_id=novel_id,
            name=name,
            description=description,
            start_episode=start_episode,
            end_episode=end_episode,
            arc_type=arc_type,
        )

    def get_span(self) -> int:
        """Get number of episodes in this arc."""
        return self.end_episode - self.start_episode + 1

    def contains_episode(self, episode: int) -> bool:
        """Check if episode is within this arc."""
        return self.start_episode <= episode <= self.end_episode


__all__ = [
    "Plot",
    "PlotPoint",
    "Arc",
    "PlotStatus",
    "ChainPhase",
]