"""
checkpoint_saver.py - LangGraph State persistence via SqliteSaver.

LangGraph はオプション依存です。インストールされていない環境でもエンジンが
初期化できるよう、インポートを遅延・例外安全にし、フォールバックとして
インメモリ保存を行います。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

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
        self._store: Dict[str, Any] = {}

    def from_conn_string(self, _db_path: str) -> "_InMemorySaver":
        return self

    async def aput(self, checkpoint: Dict[str, Any]) -> None:
        cid = checkpoint.get("id") or str(id(checkpoint))
        self._store[cid] = checkpoint

    async def aget(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(checkpoint_id)

    async def alist(self, thread_id: str) -> List[Dict[str, Any]]:
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

    def __init__(self, db_path: Optional[str] = None):
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

    async def save_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """checkpoint を保存"""
        saver = self._get_saver()
        await saver.aput(checkpoint)

    async def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """checkpoint を取得"""
        saver = self._get_saver()
        return await saver.aget(checkpoint_id)

    async def list_checkpoints(self, thread_id: str) -> List[Dict[str, Any]]:
        """thread に紐づく checkpoint 一覧を取得"""
        saver = self._get_saver()
        return await saver.alist(thread_id)

    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        """checkpoint を削除"""
        saver = self._get_saver()
        await saver.adelete(checkpoint_id)
