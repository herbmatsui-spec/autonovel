from __future__ import annotations

"""
database/repo_character.py - キャラクター(Characters)データ操作用のリポジトリMixin
"""
import json
from typing import TYPE_CHECKING, Any, List

from sqlalchemy import select, update

from services.errors import retry_on_lock
from src.backend.database.models import Character

if TYPE_CHECKING:
    from src.models import CharacterDbModel


from src.backend.database.repositories.base import BaseRepository


class CharacterRepository(BaseRepository):
    """Charactersテーブルに関するDB操作をまとめたMixin"""
    async def get_all_characters(self, book_id: int) -> List['CharacterDbModel']:
        result = await self.session.execute(
            select(Character).where(Character.book_id == book_id)
        )
        chars = result.scalars().all()
        from src.models import CharacterDbModel
        return [CharacterDbModel(**self._parse_row(self._to_dict(c), ['registry_data'])) for c in chars]
    @retry_on_lock()
    async def create_character(self, book_id: int, name: str, role: str, registry_data: Any) -> None:
        char = Character(
            book_id=book_id,
            name=name,
            role=role,
            registry_data=json.dumps(registry_data, ensure_ascii=False) if isinstance(registry_data, dict) else registry_data
        )
        self.session.add(char)
    @retry_on_lock()
    async def update_character_registry(self, char_id: int, registry_data: Any) -> None:
        await self.session.execute(
            update(Character)
            .where(Character.id == char_id)
            .values(registry_data=json.dumps(registry_data, ensure_ascii=False) if isinstance(registry_data, dict) else registry_data)
        )
