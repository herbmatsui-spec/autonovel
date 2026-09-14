"""Plot domain service - pure business logic for plot integrity and structure validation."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
import re

from src.domain.entities.plot import Plot, PlotPoint, Arc, PlotStatus, ChainPhase
from src.domain.value_objects.ids import NovelId, PlotId
from src.domain.value_objects.text import Title, TextContent, MarkdownText
from src.domain.value_objects.scores import TensionScore
from src.domain.repositories.plot_repository import IPlotRepository


class PlotValidationError(Exception):
    """Raised when plot validation fails."""
    pass


class PlotStructureValidator:
    """Validates plot structure and integrity."""

    MIN_TENSION = 0
    MAX_TENSION = 100
    MIN_CATHARSIS = 0
    MAX_CATHARSIS = 100

    @staticmethod
    def validate_plot(plot: Plot) -> List[str]:
        """Validate a single plot. Returns list of errors (empty if valid)."""
        errors = []

        if not plot.title or not str(plot.title).strip():
            errors.append("Plot title cannot be empty")

        if plot.episode_number < 1:
            errors.append("Episode number must be positive")

        if not PlotStructureValidator.MIN_TENSION <= plot.tension_score.value <= PlotStructureValidator.MAX_TENSION:
            errors.append(f"Tension score must be between {PlotStructureValidator.MIN_TENSION} and {PlotStructureValidator.MAX_TENSION}")

        if not PlotStructureValidator.MIN_CATHARSIS <= plot.catharsis <= PlotStructureValidator.MAX_CATHARSIS:
            errors.append(f"Catharsis must be between {PlotStructureValidator.MIN_CATHARSIS} and {PlotStructureValidator.MAX_CATHARSIS}")

        if plot.status == PlotStatus.LOCKED and plot.is_locked:
            pass

        return errors

    @staticmethod
    def validate_arc(arc: Arc) -> List[str]:
        """Validate a story arc."""
        errors = []

        if not arc.name.strip():
            errors.append("Arc name cannot be empty")

        if arc.start_episode < 1:
            errors.append("Start episode must be positive")

        if arc.end_episode < arc.start_episode:
            errors.append("End episode must be >= start episode")

        return errors

    @staticmethod
    def validate_chain_phase_transition(current: ChainPhase, next_phase: ChainPhase) -> bool:
        """Validate if chain phase transition is valid."""
        valid_transitions = {
            ChainPhase.FRICITON: [ChainPhase.TURN],
            ChainPhase.TURN: [ChainPhase.COUNTER_TURN],
            ChainPhase.COUNTER_TURN: [ChainPhase.RESOLUTION],
            ChainPhase.RESOLUTION: [ChainPhase.CATHARSIS, ChainPhase.MICRO_CATHARSIS],
            ChainPhase.CATHARSIS: [ChainPhase.FRICITON],
            ChainPhase.MICRO_CATHARSIS: [ChainPhase.FRICITON],
        }
        return next_phase in valid_transitions.get(current, [])


class PlotIntegrityChecker:
    """Checks plot integrity across episodes."""

    def __init__(self, plot_repo: IPlotRepository):
        self._plot_repo = plot_repo

    async def check_episode_continuity(
        self,
        novel_id: NovelId,
        branch_id: NovelId,
        episode_number: int,
    ) -> List[str]:
        """Check continuity between current and previous episode plots."""
        issues = []

        current_plot = await self._plot_repo.get_by_episode(novel_id, branch_id, episode_number)
        if not current_plot:
            issues.append(f"Plot for episode {episode_number} not found")
            return issues

        if episode_number > 1:
            prev_plot = await self._plot_repo.get_by_episode(novel_id, branch_id, episode_number - 1)
            if prev_plot:
                issues.extend(self._check_continuity_between(prev_plot, current_plot))

        return issues

    def _check_continuity_between(self, prev: Plot, current: Plot) -> List[str]:
        """Check continuity between two consecutive plots."""
        issues = []

        tension_diff = abs(current.tension_score.value - prev.tension_score.value)
        if tension_diff > 50:
            issues.append(f"Large tension jump: {prev.tension_score.value} -> {current.tension_score.value}")

        if prev.status == PlotStatus.COMPLETED and current.status == PlotStatus.PLANNED:
            pass
        elif prev.status == PlotStatus.PLANNED and current.status == PlotStatus.WRITING:
            pass
        elif current.status.value < prev.status.value:
            issues.append(f"Status regression: {prev.status.value} -> {current.status.value}")

        return issues

    async def check_arc_coverage(
        self,
        novel_id: NovelId,
        branch_id: NovelId,
    ) -> Dict[str, Any]:
        """Check if all episodes in arcs have plots."""
        arcs = await self._plot_repo.get_arcs_by_novel(novel_id)
        all_plots = await self._plot_repo.list_by_branch(novel_id, branch_id)

        plot_episodes = {p.episode_number for p in all_plots}
        gaps = []

        for arc in arcs:
            for ep in range(arc.start_episode, arc.end_episode + 1):
                if ep not in plot_episodes:
                    gaps.append({"arc": arc.name, "episode": ep})

        return {
            "total_arcs": len(arcs),
            "total_plots": len(all_plots),
            "gaps": gaps,
            "coverage_pct": (len(plot_episodes) / max(1, sum(a.get_span() for a in arcs))) * 100 if arcs else 100,
        }


@dataclass
class PlotDomainService:
    """
    Domain service for plot business logic.
    
    Pure business logic - no infrastructure dependencies.
    Depends only on repository interfaces.
    """
    plot_repo: IPlotRepository

    def __post_init__(self):
        self._validator = PlotStructureValidator()
        self._integrity_checker = PlotIntegrityChecker(self.plot_repo)

    async def create_plot(
        self,
        novel_id: NovelId,
        branch_id: NovelId,
        episode_number: int,
        title: str,
        summary: str = "",
    ) -> Plot:
        """Create a new plot with validation."""
        existing = await self.plot_repo.get_by_episode(novel_id, branch_id, episode_number)
        if existing:
            raise PlotValidationError(f"Plot for episode {episode_number} already exists")

        plot = Plot.create(
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=episode_number,
            title=title,
            summary=summary,
        )

        errors = self._validator.validate_plot(plot)
        if errors:
            raise PlotValidationError("; ".join(errors))

        return await self.plot_repo.save(plot)

    async def update_plot_content(
        self,
        plot_id: PlotId,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        one_line_summary: Optional[str] = None,
        detailed_blueprint: Optional[TextContent] = None,
        thought_process: Optional[TextContent] = None,
    ) -> Plot:
        """Update plot content with validation."""
        plot = await self.plot_repo.get_by_id(plot_id)
        if not plot:
            raise PlotValidationError(f"Plot {plot_id} not found")

        if plot.is_locked:
            raise PlotValidationError("Cannot update locked plot")

        plot.update_content(
            title=title,
            summary=summary,
            one_line_summary=one_line_summary,
            detailed_blueprint=detailed_blueprint,
            thought_process=thought_process,
        )

        errors = self._validator.validate_plot(plot)
        if errors:
            raise PlotValidationError("; ".join(errors))

        return await self.plot_repo.save(plot)

    async def set_plot_tension(
        self,
        plot_id: PlotId,
        tension: int,
        delta: int = 0,
    ) -> Plot:
        """Set plot tension score."""
        plot = await self.plot_repo.get_by_id(plot_id)
        if not plot:
            raise PlotValidationError(f"Plot {plot_id} not found")

        if not self._validator.MIN_TENSION <= tension <= self._validator.MAX_TENSION:
            raise PlotValidationError(f"Tension must be between {self._validator.MIN_TENSION} and {self._validator.MAX_TENSION}")

        plot.set_tension(tension, delta)
        return await self.plot_repo.save(plot)

    async def set_plot_catharsis(
        self,
        plot_id: PlotId,
        catharsis: int,
        catharsis_type: str = "",
    ) -> Plot:
        """Set plot catharsis level."""
        plot = await self.plot_repo.get_by_id(plot_id)
        if not plot:
            raise PlotValidationError(f"Plot {plot_id} not found")

        if not self._validator.MIN_CATHARSIS <= catharsis <= self._validator.MAX_CATHARSIS:
            raise PlotValidationError(f"Catharsis must be between {self._validator.MIN_CATHARSIS} and {self._validator.MAX_CATHARSIS}")

        plot.set_catharsis(catharsis, catharsis_type)
        return await self.plot_repo.save(plot)

    async def advance_chain_phase(self, plot_id: PlotId, next_phase: ChainPhase) -> Plot:
        """Advance plot chain phase with validation."""
        plot = await self.plot_repo.get_by_id(plot_id)
        if not plot:
            raise PlotValidationError(f"Plot {plot_id} not found")

        if not self._validator.validate_chain_phase_transition(plot.current_chain_phase, next_phase):
            raise PlotValidationError(f"Invalid chain phase transition: {plot.current_chain_phase} -> {next_phase}")

        plot.set_chain_phase(next_phase)
        return await self.plot_repo.save(plot)

    async def add_scene_to_plot(self, plot_id: PlotId, scene: str) -> Plot:
        """Add a scene to plot."""
        plot = await self.plot_repo.get_by_id(plot_id)
        if not plot:
            raise PlotValidationError(f"Plot {plot_id} not found")

        if plot.is_locked:
            raise PlotValidationError("Cannot modify locked plot")

        plot.add_scene(scene)
        return await self.plot_repo.save(plot)

    async def remove_scene_from_plot(self, plot_id: PlotId, scene_index: int) -> Plot:
        """Remove a scene from plot."""
        plot = await self.plot_repo.get_by_id(plot_id)
        if not plot:
            raise PlotValidationError(f"Plot {plot_id} not found")

        if plot.is_locked:
            raise PlotValidationError("Cannot modify locked plot")

        if not plot.remove_scene(scene_index):
            raise PlotValidationError(f"Scene index {scene_index} out of range")

        return await self.plot_repo.save(plot)

    async def lock_plot(self, plot_id: PlotId) -> Plot:
        """Lock plot from further changes."""
        plot = await self.plot_repo.get_by_id(plot_id)
        if not plot:
            raise PlotValidationError(f"Plot {plot_id} not found")

        plot.lock()
        return await self.plot_repo.save(plot)

    async def unlock_plot(self, plot_id: PlotId) -> Plot:
        """Unlock plot for editing."""
        plot = await self.plot_repo.get_by_id(plot_id)
        if not plot:
            raise PlotValidationError(f"Plot {plot_id} not found")

        plot.unlock()
        return await self.plot_repo.save(plot)

    async def change_plot_status(self, plot_id: PlotId, status: PlotStatus) -> Plot:
        """Change plot status."""
        plot = await self.plot_repo.get_by_id(plot_id)
        if not plot:
            raise PlotValidationError(f"Plot {plot_id} not found")

        plot.change_status(status)
        return await self.plot_repo.save(plot)

    async def get_plot(self, plot_id: PlotId) -> Optional[Plot]:
        """Get plot by ID."""
        return await self.plot_repo.get_by_id(plot_id)

    async def get_plot_by_episode(
        self,
        novel_id: NovelId,
        branch_id: NovelId,
        episode_number: int,
    ) -> Optional[Plot]:
        """Get plot by episode number."""
        return await self.plot_repo.get_by_episode(novel_id, branch_id, episode_number)

    async def list_plots_by_branch(
        self,
        novel_id: NovelId,
        branch_id: NovelId,
    ) -> List[Plot]:
        """List all plots for a branch."""
        return await self.plot_repo.list_by_branch(novel_id, branch_id)

    async def list_plots_by_novel(self, novel_id: NovelId) -> List[Plot]:
        """List all plots for a novel."""
        return await self.plot_repo.list_by_novel(novel_id)

    async def validate_episode_continuity(
        self,
        novel_id: NovelId,
        branch_id: NovelId,
        episode_number: int,
    ) -> List[str]:
        """Validate continuity for an episode."""
        return await self._integrity_checker.check_episode_continuity(
            novel_id, branch_id, episode_number
        )

    async def check_arc_coverage(
        self,
        novel_id: NovelId,
        branch_id: NovelId,
    ) -> Dict[str, Any]:
        """Check arc coverage."""
        return await self._integrity_checker.check_arc_coverage(novel_id, branch_id)

    async def create_arc(
        self,
        novel_id: NovelId,
        name: str,
        description: TextContent,
        start_episode: int,
        end_episode: int,
        arc_type: str = "main",
    ) -> Arc:
        """Create a new story arc."""
        arc = Arc.create(
            novel_id=novel_id,
            name=name,
            description=description,
            start_episode=start_episode,
            end_episode=end_episode,
            arc_type=arc_type,
        )

        errors = self._validator.validate_arc(arc)
        if errors:
            raise PlotValidationError("; ".join(errors))

        return await self.plot_repo.save_arc(arc)

    async def get_arcs_by_novel(self, novel_id: NovelId) -> List[Arc]:
        """Get all arcs for a novel."""
        return await self.plot_repo.get_arcs_by_novel(novel_id)

    async def create_plot_point(
        self,
        plot_id: PlotId,
        order: int,
        description: TextContent,
        point_type: str,
        tension_contribution: int = 0,
        is_major: bool = False,
    ) -> PlotPoint:
        """Create a plot point."""
        plot = await self.plot_repo.get_by_id(plot_id)
        if not plot:
            raise PlotValidationError(f"Plot {plot_id} not found")

        plot_point = PlotPoint(
            id=PlotId.generate(),
            plot_id=plot_id,
            order=order,
            description=description,
            type=point_type,
            tension_contribution=tension_contribution,
            is_major=is_major,
        )

        return await self.plot_repo.save_plot_point(plot_point)

    async def get_plot_points(self, plot_id: PlotId) -> List[PlotPoint]:
        """Get all plot points for a plot."""
        return await self.plot_repo.get_plot_points(plot_id)

    async def update_plot_scores(
        self,
        plot_id: PlotId,
        state_integrity: Optional[int] = None,
        emotional_resonance: Optional[int] = None,
        thematic_depth: Optional[int] = None,
        literary_beauty: Optional[int] = None,
        erotic_intensity: Optional[int] = None,
    ) -> Plot:
        """Update plot quality scores."""
        plot = await self.plot_repo.get_by_id(plot_id)
        if not plot:
            raise PlotValidationError(f"Plot {plot_id} not found")

        plot.update_scores(
            state_integrity=state_integrity,
            emotional_resonance=emotional_resonance,
            thematic_depth=thematic_depth,
            literary_beauty=literary_beauty,
            erotic_intensity=erotic_intensity,
        )

        return await self.plot_repo.save(plot)

    async def add_healed_field(self, plot_id: PlotId, field: str) -> Plot:
        """Add a healed field to plot."""
        plot = await self.plot_repo.get_by_id(plot_id)
        if not plot:
            raise PlotValidationError(f"Plot {plot_id} not found")

        plot.add_healed_field(field)
        return await self.plot_repo.save(plot)

    async def delete_plot(self, plot_id: PlotId) -> bool:
        """Delete a plot."""
        return await self.plot_repo.delete(plot_id)

    async def delete_arc(self, arc_id: PlotId) -> bool:
        """Delete an arc."""
        return await self.plot_repo.delete_arc(arc_id)