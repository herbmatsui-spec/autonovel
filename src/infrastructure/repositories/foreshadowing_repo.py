"""DB永続化版 伏線リポジトリ (v5.0 Relational Memory)

既存の InMemoryForeshadowingRepository をSQLAlchemy AsyncSession ベースに置換。
ForeshadowingModel (ORM) を直接操作し、伏線の CRUD・未回収検索・回収更新・
バランス集計をリレーショナルDBで完結する。
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.models_foreshadowing import ForeshadowingModel
from src.models.foreshadowing_status import ForeshadowingScope, ForeshadowingStatus


class DbForeshadowingRepository:
    """SQLAlchemy AsyncSession ベースの伏線リポジトリ。

    既存の ForeshadowingRepository インターフェースを async 拡張して実装する。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── CRUD ────────────────────────────────────────────

    async def add(self, book_id: int, title: str, description: str,
                  planted_episode: int, target_episode: Optional[int] = None) -> ForeshadowingModel:
        """伏線を新規設置する"""
        record = ForeshadowingModel(
            book_id=book_id,
            title=title,
            description=description,
            planted_episode=planted_episode,
            target_episode=target_episode,
            status=ForeshadowingStatus.PLANTED.value,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def add_if_absent(
        self,
        book_id: int,
        title: str,
        description: str,
        planted_episode: int,
        scope: str = "short_term",
    ) -> Optional[ForeshadowingModel]:
        """同一 (book_id, planted_episode, title) が既にあれば追加しない（冪等な設置）。"""
        existing = await self.db.execute(
            select(ForeshadowingModel)
            .where(ForeshadowingModel.book_id == book_id)
            .where(ForeshadowingModel.planted_episode == planted_episode)
            .where(ForeshadowingModel.title == title)
        )
        if existing.scalar_one_or_none() is not None:
            return None
        record = ForeshadowingModel(
            book_id=book_id,
            title=title,
            description=description,
            planted_episode=planted_episode,
            status=ForeshadowingStatus.PLANTED.value,
            scope=scope,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def get_by_id(self, foreshadowing_id: int) -> Optional[ForeshadowingModel]:
        """ID指定で伏線を取得"""
        stmt = select(ForeshadowingModel).where(ForeshadowingModel.id == foreshadowing_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(self, foreshadowing_ids: list[int]) -> List[ForeshadowingModel]:
        """複数ID指定で伏線一覧を取得"""
        if not foreshadowing_ids:
            return []
        stmt = (
            select(ForeshadowingModel)
            .where(ForeshadowingModel.id.in_(foreshadowing_ids))
            .order_by(ForeshadowingModel.id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_book_id(self, book_id: int) -> List[ForeshadowingModel]:
        """指定作品の全伏線を取得"""
        stmt = (
            select(ForeshadowingModel)
            .where(ForeshadowingModel.book_id == book_id)
            .order_by(ForeshadowingModel.planted_episode)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── 未回収検索（ステートマシン中核クエリ） ─────────────

    async def get_unresolved(self, book_id: int) -> List[ForeshadowingModel]:
        """指定作品の未回収伏線（planted / progressed）を全件取得

        ix_foreshadowings_book_status 複合インデックスで高速検索。
        """
        active_statuses = [s.value for s in ForeshadowingStatus.active_statuses()]
        stmt = (
            select(ForeshadowingModel)
            .where(
                ForeshadowingModel.book_id == book_id,
                ForeshadowingModel.status.in_(active_statuses),
            )
            .order_by(ForeshadowingModel.planted_episode)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_unresolved_by_scope(self, book_id: int, scope: ForeshadowingScope) -> List[ForeshadowingModel]:
        """スコープ別の未回収伏線を取得"""
        active_statuses = [s.value for s in ForeshadowingStatus.active_statuses()]
        scope_value = scope.value if isinstance(scope, ForeshadowingScope) else str(scope)
        stmt = (
            select(ForeshadowingModel)
            .where(
                ForeshadowingModel.book_id == book_id,
                ForeshadowingModel.scope == scope_value,  # Changed to scope_value
                ForeshadowingModel.status.in_(active_statuses),
            )
            .order_by(ForeshadowingModel.planted_episode)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_overdue(self, book_id: int, current_episode: int) -> List[ForeshadowingModel]:
        """回収期限を超過した伏線を取得（target_episode < current_episode かつ未回収）"""
        active_statuses = [s.value for s in ForeshadowingStatus.active_statuses()]
        stmt = (
            select(ForeshadowingModel)
            .where(
                ForeshadowingModel.book_id == book_id,
                ForeshadowingModel.status.in_(active_statuses),
                ForeshadowingModel.target_episode.isnot(None),
                ForeshadowingModel.target_episode < current_episode,
            )
            .order_by(ForeshadowingModel.planted_episode)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── ステータス遷移 ─────────────────────────────────

    async def resolve(self, foreshadowing_id: int, episode_num: int) -> bool:
        """伏線を回収済みに更新"""
        stmt = (
            update(ForeshadowingModel)
            .where(ForeshadowingModel.id == foreshadowing_id)
            .values(
                status=ForeshadowingStatus.RESOLVED.value,
                resolved_episode=episode_num,
                updated_at=datetime.utcnow(),
            )
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def progress(self, foreshadowing_id: int) -> bool:
        """伏線を「進展中」に更新"""
        stmt = (
            update(ForeshadowingModel)
            .where(ForeshadowingModel.id == foreshadowing_id)
            .values(
                status=ForeshadowingStatus.PROGRESSED.value,
                updated_at=datetime.utcnow(),
            )
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def abandon(self, foreshadowing_id: int) -> bool:
        """伏線を回収放棄に更新"""
        stmt = (
            update(ForeshadowingModel)
            .where(ForeshadowingModel.id == foreshadowing_id)
            .values(
                status=ForeshadowingStatus.ABANDONED.value,
                updated_at=datetime.utcnow(),
            )
        )
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    # ── 集計 ─────────────────────────────────────────────

    async def get_balance(self, book_id: int) -> dict:
        """伏線設置/回収のバランスを取得

        Returns:
            {"planted": int, "progressed": int, "resolved": int, "abandoned": int, "active": int}
        """
        stmt = (
            select(
                ForeshadowingModel.status,
                func.count(ForeshadowingModel.id).label("count"),
            )
            .where(ForeshadowingModel.book_id == book_id)
            .group_by(ForeshadowingModel.status)
        )
        result = await self.db.execute(stmt)
        counts = {row[0]: row[1] for row in result.fetchall()}

        planted = counts.get(ForeshadowingStatus.PLANTED.value, 0)
        progressed = counts.get(ForeshadowingStatus.PROGRESSED.value, 0)
        resolved = counts.get(ForeshadowingStatus.RESOLVED.value, 0)
        abandoned = counts.get(ForeshadowingStatus.ABANDONED.value, 0)

        return {
            "planted": planted,
            "progressed": progressed,
            "resolved": resolved,
            "abandoned": abandoned,
            "active": planted + progressed,
        }
