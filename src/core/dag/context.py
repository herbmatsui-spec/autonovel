"""DAG Pipeline Context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class PipelineContext:
    """Context data passed through DAG pipeline nodes."""

    data: Dict[str, Any] = field(default_factory=dict)
    state: str = "initialized"
