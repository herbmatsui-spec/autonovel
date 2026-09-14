"""Plot repository interface."""

from __future__ import annotations
from typing import Protocol, Optional, List, runtime_checkable
from src.domain.entities.plot import Plot, PlotPoint, Arc
from src.domain.value_objects.ids import PlotId, NovelId, PlotPointId, ArcId
from src.domain.entities.plot import PlotStatus, ChainPhase


@runtime_checkable
class IPlotRepository(Protocol):
    """Plot repository interface."""

    async def get_by_novel(self, novel_id: NovelId) -> Optional[Plot]:
        """Get plot by novel ID."""
        ...

    async def save(self, plot: Plot) -> Plot:
        """Save plot (insert or update)."""
        ...

    async def delete(self, plot_id: PlotId) -> bool:
        """Delete plot by ID. Returns True if deleted."""
        ...

    async def exists(self, novel_id: NovelId) -> bool:
        """Check if plot exists for novel."""
        ...

    # PlotPoints
    async def get_plot_point(self, plot_point_id: PlotPointId) -> Optional[PlotPoint]:
        """Get plot point by ID."""
        ...

    async def save_plot_point(self, plot_point: PlotPoint) -> PlotPoint:
        """Save plot point (insert or update)."""
        ...

    async def list_plot_points_by_plot(
        self,
        plot_id: PlotId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PlotPoint]:
        """List plot points by plot."""
        ...

    async def list_plot_points_by_episode(
        self,
        plot_id: PlotId,
        episode_number: int,
    ) -> List[PlotPoint]:
        """List plot points for a specific episode."""
        ...

    async def count_plot_points_by_plot(self, plot_id: PlotId) -> int:
        """Count plot points in a plot."""
        ...

    async def delete_plot_point(self, plot_point_id: PlotPointId) -> bool:
        """Delete plot point by ID. Returns True if deleted."""
        ...

    async def get_plot_points_by_phase(
        self,
        plot_id: PlotId,
        phase: ChainPhase,
    ) -> List[PlotPoint]:
        """Get plot points by chain phase."""
        ...

    async def get_max_order_in_phase(
        self,
        plot_id: PlotId,
        phase: ChainPhase,
    ) -> int:
        """Get maximum order in a chain phase."""
        ...

    async def reorder_plot_points(
        self,
        plot_id: PlotId,
        point_orders: List[tuple[PlotPointId, int]],
    ) -> bool:
        """Reorder plot points."""

    # Arcs
    async def get_arc(self, arc_id: ArcId) -> Optional[Arc]:
        """Get arc by ID."""
        ...

    async def save_arc(self, arc: Arc) -> Arc:
        """Save arc (insert or update)."""
        ...

    async def list_arcs_by_plot(
        self,
        plot_id: PlotId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Arc]:
        """List arcs by plot."""
        ...

    async def count_arcs_by_plot(self, plot_id: PlotId) -> int:
        """Count arcs in a plot."""
        ...

    async def delete_arc(self, arc_id: ArcId) -> bool:
        """Delete arc by ID. Returns True if deleted."""
        ...

    async def get_arc_by_phase(
        self,
        plot_id: PlotId,
        phase: ChainPhase,
    ) -> Optional[Arc]:
        """Get arc for a specific phase."""
        ...