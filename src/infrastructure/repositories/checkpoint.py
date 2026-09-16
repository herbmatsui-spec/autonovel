"""チェックポイントリポジトリ。"""
from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session
from src.backend.database.models_checkpoint import WorkflowCheckpointModel
from src.domain.entities.checkpoint import WorkflowCheckpoint, CheckpointStatus


class CheckpointRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, checkpoint: WorkflowCheckpoint) -> None:
        model = self.session.query(WorkflowCheckpointModel).filter_by(checkpoint_id=checkpoint.checkpoint_id).first()
        if not model:
            model = WorkflowCheckpointModel(
                checkpoint_id=checkpoint.checkpoint_id,
                task_id=checkpoint.task_id,
                step_name=checkpoint.step_name,
                step_index=checkpoint.step_index,
                status=checkpoint.status.value,
                state_payload=checkpoint.state_payload,
                error_message=checkpoint.error_message,
            )
            self.session.add(model)
        else:
            model.status = checkpoint.status.value
            model.state_payload = checkpoint.state_payload
            model.error_message = checkpoint.error_message
            model.step_index = checkpoint.step_index
        self.session.commit()

    def get_latest_checkpoint(self, task_id: str) -> Optional[WorkflowCheckpoint]:
        model = (
            self.session.query(WorkflowCheckpointModel)
            .filter_by(task_id=task_id)
            .order_by(WorkflowCheckpointModel.step_index.desc(), WorkflowCheckpointModel.created_at.desc())
            .first()
        )
        if not model:
            return None
        return WorkflowCheckpoint(
            checkpoint_id=model.checkpoint_id,
            task_id=model.task_id,
            step_name=model.step_name,
            step_index=model.step_index,
            status=CheckpointStatus(model.status),
            state_payload=model.state_payload,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
