from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class PipelineEvent:
    event_type: str  # task_started | pdca_cycle | audit_diff | score_updated | completed | error
    book_id: int
    task_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    payload: dict[str, Any] = field(default_factory=dict)
