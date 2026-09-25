"""src.services.age_client is deprecated as of v5.0 Relational Memory.

This module is retained as a minimal stub for backwards compatibility
and will be completely removed in a future release.

Backwards-compatible symbols (CypherResult, GraphStats, utility helpers) are
retained so that legacy test modules can still be imported.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from typing import Any

warnings.warn(
    "src.services.age_client is deprecated and replaced by Relational Memory. "
    "Do not use this module in new code.",
    DeprecationWarning,
    stacklevel=2,
)


@dataclass
class CypherResult:
    """Deprecated stub: Cypher クエリ結果の互換コンテナ."""

    records: list[dict[str, Any]] = field(default_factory=list)
    summary: str = "deprecated"
    execution_time_ms: float = 0.0


@dataclass
class GraphStats:
    """Deprecated stub: グラフ統計の互換コンテナ."""

    node_count: int = 0
    edge_count: int = 0
    labels: list[str] = field(default_factory=list)
    relationship_types: list[str] = field(default_factory=list)


def _parse_agtype(value: Any) -> Any:
    """Deprecated stub: agtype 文字列をパースする互換ユーティリティ."""
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                import json

                return json.loads(text)
            except (ValueError, TypeError):
                return value
        if text.startswith("[") and text.endswith("]"):
            try:
                import json

                return json.loads(text)
            except (ValueError, TypeError):
                return value
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]
    return value


def _interpolate_cypher_params(query: str, params: dict[str, Any] | None = None) -> str:
    """Deprecated stub: Cypher パラメータを $プレースホルダに展開する互換ユーティリティ."""
    if not params:
        return query
    interpolated = query
    for key, val in params.items():
        interpolated = interpolated.replace(f"${key}", repr(val))
    return interpolated


def _dict_to_cypher_map(mapping: dict[str, Any] | None = None) -> str:
    """Deprecated stub: dict を Cypher マップ文字列に変換する互換ユーティリティ."""
    if not mapping:
        return "{}"
    pairs = ", ".join(f"{k}: {repr(v)}" for k, v in mapping.items())
    return "{" + pairs + "}"


def _sanitize_graph_name(graph_name: str | None) -> str | None:
    """Deprecated stub: グラフ名をサニタイズする互換ユーティリティ（SQLインジェクション対策）."""
    if graph_name is None:
        return None
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "", graph_name)
    return sanitized or None


def _validate_column_def(column_def: str | None) -> bool:
    """Deprecated stub: カラム定義文字列の妥当性を検査する互換ユーティリティ."""
    if not column_def:
        return False
    # "name agtype" / "name type" 形式のみ許容
    pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\s+(agtype|text)$")
    return all(pattern.match(part.strip()) for part in column_def.split(",") if part.strip())


def _is_retryable_db_error(exc: Exception) -> bool:
    """Deprecated stub: DB エラーがリトライ可能か判定する互換ユーティリティ."""
    try:
        from sqlalchemy.exc import OperationalError, DBAPIError

        return isinstance(exc, OperationalError | DBAPIError)
    except ImportError:
        return False


def _safe_retry(func: Any, *args: Any, retries: int = 3, **kwargs: Any) -> Any:
    """Deprecated stub: リトライラッパーの互換ユーティリティ."""
    last_exc: Exception | None = None
    for _ in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if not _is_retryable_db_error(exc):
                raise
    raise last_exc  # type: ignore[misc]


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
