from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.errors import retry_on_lock
from src.backend.database.models import Base

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession):
        self.session = session

    @property
    def model_class(self) -> Type[T]:
        raise NotImplementedError

    async def get(self, id: int) -> Optional[T]:
        result = await self.session.execute(select(self.model_class).where(self.model_class.id == id)) # type: ignore
        return result.scalar_one_or_none()

    async def get_all(self) -> List[T]:
        result = await self.session.execute(select(self.model_class))
        return list(result.scalars().all())

    def add(self, entity: T) -> None:
        self.session.add(entity)

    @retry_on_lock()
    async def delete(self, entity: T) -> None:
        await self.session.delete(entity)

    @retry_on_lock()
    async def delete_by_id(self, id: int) -> None:
        await self.session.execute(delete(self.model_class).where(self.model_class.id == id)) # type: ignore

    def _to_dict(self, instance) -> dict:
        if not instance:
            return {}
        return {c.name: getattr(instance, c.name) for c in instance.__table__.columns}

    def _parse_row(self, row: dict, json_fields: list) -> dict:
        import json
        for f in json_fields:
            if f in row and isinstance(row[f], str):
                try:
                    row[f] = json.loads(row[f])
                except (json.JSONDecodeError, TypeError):
                    pass
        return row

