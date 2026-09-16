"""workflow_checkpoints SQLAlchemy ORMモデル。"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
from src.infrastructure.database.models.base_orm import Base


class WorkflowCheckpointModel(Base):
    __tablename__ = "workflow_checkpoints"
    __table_args__ = {"extend_existing": True}

    checkpoint_id = Column(String(64), primary_key=True, index=True)
    task_id = Column(String(64), nullable=False, index=True)
    step_name = Column(String(64), nullable=False)
    step_index = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    state_payload = Column(JSON, default=dict, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
