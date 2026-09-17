"""
checkpoint_saver.py - LangGraph State persistence via SqliteSaver.

LangGraph はオプション依存です。インストールされていない環境でもエンジンが
初期化できるよう、インポートを遅延・例外安全にし、フォールバックとして
インメモリ保存を行います。
"""

from __future__ import annotations

# Remove unused asyncio import
import logging
from typing import Any

from config import BASE_DIR

logger = logging.getLogger(__name__)

try:
    from langgraph.checkpoint.sqlite import SqliteSaver

    HAS_LANGGRAPH = True
except ImportError:
    SqliteSaver = None  # type: ignore
    HAS_LANGGRAPH = False


class _InMemorySaver:
    """LangGraph が無い環境用のダミー永続化（インメモリ）。"""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def from_conn_string(self, _db_path: str) -> _InMemorySaver:
        return self

    async def aput(self, checkpoint: dict[str, Any]) -> None:
        cid = checkpoint.get("id") or str(id(checkpoint))
        self._store[cid] = checkpoint

    async def aget(self, checkpoint_id: str) -> dict[str, Any] | None:
        return self._store.get(checkpoint_id)

    async def alist(self, thread_id: str) -> list[dict[str, Any]]:
        return [c for c in self._store.values() if c.get("thread_id") == thread_id]

    async def adelete(self, checkpoint_id: str) -> None:
        self._store.pop(checkpoint_id, None)


class CheckpointSaver:
    """
    LangGraphのStateful WorkflowをSQLiteで永続化するアダプタ。

    - SqliteSaver を内部で保持し、checkpoint の save/get/list/delete を提供。
    - DBファイルは BASE_DIR 配下に作成する。
    - LangGraph が未インストールの場合はインメモリ保存にフォールバックする。
    """

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = str(BASE_DIR / "checkpoints.db")
        self.db_path = db_path
        self._saver: Any = None
        if not HAS_LANGGRAPH:
            logger.warning(
                "langgraph が未インストールのため CheckpointSaver はインメモリ保存にフォールバックします。"
            )

    def _get_saver(self) -> Any:
        if self._saver is None:
            if HAS_LANGGRAPH and SqliteSaver is not None:
                self._saver = SqliteSaver.from_conn_string(self.db_path)
            else:
                self._saver = _InMemorySaver()
        return self._saver

    async def save_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        """checkpoint を保存"""
        saver = self._get_saver()
        await saver.aput(checkpoint)

    async def get_checkpoint(self, checkpoint_id: str) -> dict[str, Any] | None:
        """checkpoint を取得"""
        saver = self._get_saver()
        return await saver.aget(checkpoint_id)

    async def list_checkpoints(self, thread_id: str) -> list[dict[str, Any]]:
        """thread に紐づく checkpoint 一覧を取得"""
        saver = self._get_saver()
        return await saver.alist(thread_id)

    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        """checkpoint を削除"""
        saver = self._get_saver()
        await saver.adelete(checkpoint_id)


from src.domain.entities.checkpoint import WorkflowCheckpoint, CheckpointStatus
from src.infrastructure.repositories.checkpoint import CheckpointRepository

class CheckpointManager:
    """DBベースのチェックポイント永続化管理マネージャー。"""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def record_step(self, task_id: str, step_name: str, step_index: int, state_payload: dict, status: CheckpointStatus = CheckpointStatus.COMPLETED, error_message: str | None = None) -> str:
        checkpoint_id = f"{task_id}_{step_index}_{step_name}"
        checkpoint = WorkflowCheckpoint(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            step_name=step_name,
            step_index=step_index,
            status=status,
            state_payload=state_payload,
            error_message=error_message,
        )
        with self.session_factory() as session:
            repo = CheckpointRepository(session)
            repo.save(checkpoint)
        return checkpoint_id

    def load_last_state(self, task_id: str) -> tuple[int, str, dict] | None:
        with self.session_factory() as session:
            repo = CheckpointRepository(session)
            cp = repo.get_latest_checkpoint(task_id)
            if cp and cp.status == CheckpointStatus.COMPLETED:
                return cp.step_index, cp.step_name, cp.state_payload
            return None
