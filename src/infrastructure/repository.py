from abc import ABC, abstractmethod
from typing import Any, Generic, List, Optional, Protocol, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T", bound=BaseModel)
TCreate = TypeVar("TCreate", bound=BaseModel)


class RepositoryProtocol(Protocol[T, TCreate]):
    """Repository のプロトコル（構造的型付け用）"""

    async def get(self, entity_id: int) -> Optional[T]:
        ...

    async def get_all(self) -> List[T]:
        ...

    async def create(self, data: TCreate) -> T:
        ...

    async def update(self, entity_id: int, data: dict[str, Any]) -> Optional[T]:
        ...

    async def delete(self, entity_id: int) -> bool:
        ...


class AsyncRepository(Generic[T, TCreate], ABC):
    """非同期 Repository の抽象基底クラス"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @abstractmethod
    async def get(self, entity_id: int) -> Optional[T]:
        """ID でエンティティを取得する"""
        ...

    @abstractmethod
    async def get_all(self) -> List[T]:
        """全エンティティを取得する"""
        ...

    @abstractmethod
    async def create(self, data: TCreate) -> T:
        """エンティティを作成する"""
        ...

    @abstractmethod
    async def update(self, entity_id: int, data: dict[str, Any]) -> Optional[T]:
        """エンティティを更新する"""
        ...

    @abstractmethod
    async def delete(self, entity_id: int) -> bool:
        """エンティティを削除する"""
        ...


class SQLAlchemyRepository(AsyncRepository[T, TCreate]):
    """SQLAlchemy を用いた Repository 実装の基底クラス"""

    def __init__(self, session: AsyncSession, model_class: type) -> None:
        super().__init__(session)
        self.model_class = model_class

    async def get(self, entity_id: int) -> Optional[T]:
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def get_all(self) -> List[T]:
        stmt = select(self.model_class)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]

    async def create(self, data: TCreate) -> T:
        orm_obj = self.model_class(**data.model_dump())
        self.session.add(orm_obj)
        await self.session.flush()
        await self.session.refresh(orm_obj)
        return self._to_domain(orm_obj)

    async def update(self, entity_id: int, data: dict[str, Any]) -> Optional[T]:
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        for key, value in data.items():
            setattr(row, key, value)
        await self.session.flush()
        await self.session.refresh(row)
        return self._to_domain(row)

    async def delete(self, entity_id: int) -> bool:
        stmt = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True

    def _to_domain(self, orm_obj: Any) -> T:
        """ORM モデルから Pydantic ドメインモデルへの変換（サブクラスで上書き可能）"""
        return orm_obj  # 実装は具体的サブクラスで行う
        # Repository alias for compatibility with legacy code
Repository = SQLAlchemyRepository
