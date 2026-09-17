"""チェックポイントエンティティ定義。"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class CheckpointStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowCheckpoint(BaseModel):
    checkpoint_id: str
    task_id: str
    step_name: str
    step_index: int = 0
    status: CheckpointStatus = CheckpointStatus.PENDING
    state_payload: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
