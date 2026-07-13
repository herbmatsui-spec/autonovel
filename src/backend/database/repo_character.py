from __future__ import annotations

"""
database/repo_character.py - キャラクター(Characters)データ操作用のリポジトリMixin
"""
import json
from typing import Any, List

from sqlalchemy import select, update

from src.backend.database.core import retry_with_logging
from src.backend.database.models import Character
from src.models import CharacterDbModel


class CharacterRepositoryMixin:
    """Charactersテーブルに関するDB操作をまとめたMixin"""

    @retry_with_logging()
    async def get_all_characters(self, book_id: int) -> List[CharacterDbModel]:
        async with self._get_session() as session:
            result = await session.execute(
                select(Character).where(Character.book_id == book_id)
            )
            chars = result.scalars().all()
            return [CharacterDbModel(**self._parse_row(self._to_dict(c), ['registry_data'])) for c in chars]

    @retry_with_logging()
    async def create_character(self, book_id: int, name: str, role: str, registry_data: Any) -> None:
        async with self._get_session() as session:
            char = Character(
                book_id=book_id,
                name=name,
                role=role,
                registry_data=json.dumps(registry_data, ensure_ascii=False) if isinstance(registry_data, dict) else registry_data
            )
            session.add(char)

    @retry_with_logging()
    async def update_character_registry(self, char_id: int, registry_data: Any) -> None:
        async with self._get_session() as session:
            await session.execute(
                update(Character)
                .where(Character.id == char_id)
                .values(registry_data=json.dumps(registry_data, ensure_ascii=False) if isinstance(registry_data, dict) else registry_data)
            )

