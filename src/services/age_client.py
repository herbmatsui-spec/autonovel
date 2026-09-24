"""src.services.age_client is deprecated as of v5.0 Relational Memory.

This module is retained as a minimal stub for backwards compatibility
and will be completely removed in a future release.
"""

from __future__ import annotations

import warnings
from typing import Any

warnings.warn(
    "src.services.age_client is deprecated and replaced by Relational Memory. "
    "Do not use this module in new code.",
    DeprecationWarning,
    stacklevel=2,
)


class AgeClient:
    """Deprecated stub for legacy Apache AGE client."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def init_graph(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def get_neighbors(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return []

    def get_all_nodes(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return []

    def upsert_node(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def upsert_edge(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def upsert_nodes_batch(self, *args: Any, **kwargs: Any) -> int:
        return 0

    def upsert_edges_batch(self, *args: Any, **kwargs: Any) -> int:
        return 0

    def delete_node(self, *args: Any, **kwargs: Any) -> bool:
        return True

    def get_shortest_path(self, *args: Any, **kwargs: Any) -> Any:
        return None

    def get_graph_stats(self, *args: Any, **kwargs: Any) -> Any:
        class DummyStats:
            node_count = 0
            edge_count = 0
            labels = []
            relationship_types = []
        return DummyStats()

    def execute_cypher(self, *args: Any, **kwargs: Any) -> Any:
        class DummyResult:
            records = []
            summary = "deprecated"
            execution_time_ms = 0.0
        return DummyResult()


age_client = AgeClient()

__all__ = ["AgeClient", "age_client"]
