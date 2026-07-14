from __future__ import annotations

"""
database/repo_misc.py - その他のデータ(Style Fragments, Custom Styles, Internal State, Patches, Optimization, Background Tasks)操作用のリポジトリMixin
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select, update

from services.errors import retry_on_lock
from src.backend.database.models import (
    BackgroundTask,
    CustomStyle,
    InternalState,
    OptimizationHistory,
    PendingPatch,
    StyleFragment,
)

logger = logging.getLogger(__name__)


from src.backend.database.repositories.base import BaseRepository


class MiscRepository(BaseRepository):
    """その他のテーブル(Style fragments, Custom styles, Internal state, Pending patches, Optimization, Background Tasks)に関するDB操作をまとめたMixin"""

    # ---------- Optimization History ----------
    @retry_on_lock()
    async def save_optimization_report(self, book_id: int, report: Dict[str, Any]) -> None:
        opt = OptimizationHistory(
            book_id=book_id,
            report_json=json.dumps(report, ensure_ascii=False),
            created_at=datetime.now()
        )
        self.session.add(opt)
    async def get_optimization_history(self, book_id: int) -> List[OptimizationHistoryDbModel]:
        result = await self.session.execute(
            select(OptimizationHistory)
            .where(OptimizationHistory.book_id == book_id)
            .order_by(OptimizationHistory.created_at.desc())
        )
        rows = result.scalars().all()
        return [self._parse_row(self._to_dict(r), ['report_json']) for r in rows]

    # ---------- Style Fragments (RAG) ----------
    @retry_on_lock()
    async def add_style_fragment(self, tag: str, content: str, embedding: List[float], origin: str = "Master") -> None:
        frag = StyleFragment(
            tag=tag,
            content=content,
            embedding_json=json.dumps(embedding),
            origin=origin,
            created_at=datetime.now()
        )
        self.session.add(frag)
    async def get_all_style_fragments(self, tag: Optional[str] = None) -> List[StyleFragmentDbModel]:
        stmt = select(StyleFragment)
        if tag:
            stmt = stmt.where(StyleFragment.tag == tag)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_dict(r) for r in rows]
    async def search_style_fragments_by_tag(self, tag: str, limit: int = 5) -> List[StyleFragmentDbModel]:
        result = await self.session.execute(
            select(StyleFragment)
            .where(StyleFragment.tag == tag)
            .order_by(func.random())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [self._to_dict(r) for r in rows]

    # ---------- Custom Styles ----------
    @retry_on_lock()
    async def save_custom_style(self, name: str, instruction: str, score: int, analysis: str) -> None:
        result = await self.session.execute(select(CustomStyle).where(CustomStyle.name == name))
        style = result.scalar_one_or_none()
        if not style:
            style = CustomStyle(name=name)
            self.session.add(style)
        style.instruction = instruction
        style.score = score
        style.analysis = analysis
        style.created_at = datetime.now()
    async def get_all_custom_styles(self) -> List[CustomStyleDbModel]:
        result = await self.session.execute(
            select(CustomStyle).order_by(CustomStyle.score.desc())
        )
        rows = result.scalars().all()
        return [self._to_dict(r) for r in rows]
    @retry_on_lock()
    async def delete_custom_style(self, style_id: int) -> None:
        await self.session.execute(
            delete(CustomStyle).where(CustomStyle.id == style_id)
        )

    # ---------- Internal State ----------
    @retry_on_lock()
    async def save_internal_state(self, key: str, value: Any) -> None:
        """ウィザードの下書きなどの内部状態を保存する"""
        result = await self.session.execute(select(InternalState).where(InternalState.key == key))
        state = result.scalar_one_or_none()
        if not state:
            state = InternalState(key=key)
            self.session.add(state)
        state.value = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        state.updated_at = datetime.now()
    async def get_internal_state(self, key: str) -> Optional[Any]:
        """保存された内部状態を取得する"""
        result = await self.session.execute(select(InternalState.value).where(InternalState.key == key))
        row_val = result.scalar_one_or_none()
        if row_val is not None:
            try:
                return json.loads(row_val)
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug(f"Failed to parse internal_state JSON for key {key}, returning raw string: {e}")
                return row_val
        return None

    # ---------- Pending Patches (Human-in-the-Loop) ----------
    @retry_on_lock()
    async def save_pending_patch(
        self, book_id: int, patch_type: str,
        patch_content: str, ab_test_result: Dict[str, Any]
    ) -> int:
        """承認待ちパッチを保存"""
        patch = PendingPatch(
            book_id=book_id,
            patch_type=patch_type,
            patch_content=json.dumps(patch_content, ensure_ascii=False) if isinstance(patch_content, dict) else patch_content,
            ab_test_result=json.dumps(ab_test_result, ensure_ascii=False),
            status="pending",
            created_at=datetime.now()
        )
        self.session.add(patch)
        await self.session.flush()
        return patch.id
    async def get_pending_patches(self, book_id: int) -> List[PendingPatchDbModel]:
        """承認待ちパッチ一覧を取得"""
        result = await self.session.execute(
            select(PendingPatch)
            .where(PendingPatch.book_id == book_id)
            .where(PendingPatch.status == 'pending')
            .order_by(PendingPatch.created_at.desc())
        )
        rows = result.scalars().all()
        return [self._parse_row(self._to_dict(r), ['ab_test_result']) for r in rows]
    @retry_on_lock()
    async def update_patch_status(self, patch_id: int, status: str) -> None:
        """パッチのステータスを更新（approved / rejected）"""
        await self.session.execute(
            update(PendingPatch)
            .where(PendingPatch.id == patch_id)
            .values(status=status, reviewed_at=datetime.now())
        )
    async def get_rejected_patches(self, book_id: int, limit: int = 5) -> List[PendingPatchDbModel]:
        """却下されたパッチの履歴を取得"""
        result = await self.session.execute(
            select(PendingPatch)
            .where(PendingPatch.book_id == book_id)
            .where(PendingPatch.status == 'rejected')
            .order_by(PendingPatch.reviewed_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [self._parse_row(self._to_dict(r), ['ab_test_result']) for r in rows]

    # ---------- Background Tasks ----------
    @retry_on_lock()
    async def save_background_task(
        self, id: str, status: str, current_step: int, total_steps: int,
        message: str, sub_message: str, streaming_text: str, logs: List[str],
        error: Optional[str] = None, result_data: Optional[Any] = None
    ) -> None:
        """バックグラウンドタスクの状態をDBに保存/更新する"""
        result = await self.session.execute(select(BackgroundTask).where(BackgroundTask.id == id))
        task = result.scalar_one_or_none()
        if not task:
            task = BackgroundTask(id=id)
            self.session.add(task)
        task.status = status
        task.current_step = current_step
        task.total_steps = total_steps
        task.message = message
        task.sub_message = sub_message
        task.streaming_text = streaming_text
        task.logs = json.dumps(logs, ensure_ascii=False)
        task.error = error
        task.result_data = json.dumps(result_data, ensure_ascii=False) if result_data is not None else None
        # updated_at will be set automatically on update or manually here if needed
    async def get_background_task(self, task_id: str) -> Optional[BackgroundTaskDbModel]:
        """バックグラウンドタスクの状態をDBから取得する"""
        result = await self.session.execute(select(BackgroundTask).where(BackgroundTask.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            return self._parse_row(self._to_dict(task), ['logs', 'result_data'])
        return None
