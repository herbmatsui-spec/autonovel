"""Plot DTOs."""

from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.plot import Plot

from pydantic import BaseModel, ConfigDict, Field

MODEL_CONFIG_DEFAULTS = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())

ChainPhase = Literal["Friction", "Prep", "Payoff", "Discovery", "Bonding", "Fulfillment", "Hate"]


class GeneratePlotDTO(BaseModel):
    """DTO for generating a new plot."""

    novel_id: str = Field(..., min_length=1)
    branch_id: str = Field(..., min_length=1)
    concept: str = Field(default="")
    genre: str = Field(default="")
    target_episodes: int = Field(default=50, ge=1, le=500)
    structure_type: str = Field(default="three_act")  # "three_act", "five_act", "hero_journey", "kishotenketsu"
    seed_plot_points: Optional[list[dict]] = None

    model_config = MODEL_CONFIG_DEFAULTS


class PlotExpansionDTO(BaseModel):
    """DTO for expanding a plot."""

    plot_id: str = Field(..., min_length=1)
    detail_level: str = Field(default="normal")  # "brief", "normal", "detailed"
    focus_arcs: Optional[list[str]] = None
    add_foreshadowing: bool = Field(default=True)
    add_subplots: bool = Field(default=True)

    model_config = MODEL_CONFIG_DEFAULTS


class CreatePlotPointDTO(BaseModel):
    """DTO for creating a plot point."""

    plot_id: str = Field(..., min_length=1)
    episode_number: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(default="")
    phase: ChainPhase = Field(default="Friction")
    tension: int = Field(default=50, ge=0, le=100)
    catharsis: int = Field(default=0, ge=0, le=100)
    characters_involved: list[str] = Field(default_factory=list)
    foreshadowing: list[str] = Field(default_factory=list)
    payoff_for: list[str] = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS


class UpdatePlotPointDTO(BaseModel):
    """DTO for updating a plot point."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    summary: Optional[str] = None
    phase: Optional[ChainPhase] = None
    tension: Optional[int] = Field(default=None, ge=0, le=100)
    catharsis: Optional[int] = Field(default=None, ge=0, le=100)
    characters_involved: Optional[list[str]] = None
    foreshadowing: Optional[list[str]] = None
    payoff_for: Optional[list[str]] = None

    model_config = MODEL_CONFIG_DEFAULTS


class CreateArcDTO(BaseModel):
    """DTO for creating a plot arc."""

    plot_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    start_episode: int = Field(..., ge=1)
    end_episode: int = Field(..., ge=1)
    arc_type: str = Field(default="main")  # "main", "sub", "character", "romance"
    characters: list[str] = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS


class PlotPointResponseDTO(BaseModel):
    """DTO for plot point response."""

    id: str
    plot_id: str
    episode_number: int
    title: str
    summary: str
    phase: ChainPhase
    tension: int
    catharsis: int
    characters_involved: list[str]
    foreshadowing: list[str]
    payoff_for: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS


class ArcResponseDTO(BaseModel):
    """DTO for plot arc response."""

    id: str
    plot_id: str
    name: str
    description: str
    start_episode: int
    end_episode: int
    arc_type: str
    characters: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS


class PlotResponseDTO(BaseModel):
    """DTO for plot response."""

    id: str
    novel_id: str
    branch_id: str
    title: str
    structure_type: str
    target_episodes: int
    plot_points: list[PlotPointResponseDTO] = Field(default_factory=list)
    arcs: list[ArcResponseDTO] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, plot: "Plot") -> "PlotResponseDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(plot.id),
            novel_id=str(plot.novel_id),
            branch_id=str(plot.branch_id),
            title=plot.title,
            structure_type=plot.structure_type,
            target_episodes=plot.target_episodes,
            plot_points=[
                PlotPointResponseDTO(
                    id=str(pp.id),
                    plot_id=str(pp.plot_id),
                    episode_number=pp.episode_number,
                    title=pp.title,
                    summary=pp.summary,
                    phase=pp.phase,
                    tension=pp.tension,
                    catharsis=pp.catharsis,
                    characters_involved=pp.characters_involved,
                    foreshadowing=pp.foreshadowing,
                    payoff_for=pp.payoff_for,
                    created_at=pp.created_at,
                    updated_at=pp.updated_at,
                )
                for pp in plot.plot_points
            ],
            arcs=[
                ArcResponseDTO(
                    id=str(arc.id),
                    plot_id=str(arc.plot_id),
                    name=arc.name,
                    description=arc.description,
                    start_episode=arc.start_episode,
                    end_episode=arc.end_episode,
                    arc_type=arc.arc_type,
                    characters=arc.characters,
                    created_at=arc.created_at,
                    updated_at=arc.updated_at,
                )
                for arc in plot.arcs
            ],
            created_at=plot.created_at,
            updated_at=plot.updated_at,
        )


class PlotListItemDTO(BaseModel):
    """DTO for plot list item (lightweight)."""

    id: str
    novel_id: str
    branch_id: str
    title: str
    structure_type: str
    plot_points_count: int
    arcs_count: int
    created_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, plot: "Plot") -> "PlotListItemDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(plot.id),
            novel_id=str(plot.novel_id),
            branch_id=str(plot.branch_id),
            title=plot.title,
            structure_type=plot.structure_type,
            plot_points_count=len(plot.plot_points),
            arcs_count=len(plot.arcs),
            created_at=plot.created_at,
        )
