from __future__ import annotations

"""
database/repo_rules.py - ルールおよびマスターピース操作用のリポジトリMixin
"""
import json
import logging
import time
from typing import List, Optional

from sqlalchemy import delete, or_, select, update

from services.errors import retry_on_lock
from src.backend.database.models import Masterpiece, Rule

logger = logging.getLogger(__name__)


from src.backend.database.repositories.base import BaseRepository


class RulesRepository(BaseRepository):
    """rules および masterpieces テーブルに関するDB操作をまとめたMixin"""

    # ---------- Rules ----------
    @retry_on_lock()
    async def create_rule(
        self, target_word: str, instruction: str, level: str = "global",
        domain: str = "all", character_name: Optional[str] = None,
        status: str = "active"
    ) -> int:
        now = time.strftime('%Y-%m-%dT%H:%M:%S')
        rule = Rule(
            target_word=target_word,
            instruction=instruction,
            level=level,
            domain=domain,
            character_name=character_name,
            status=status,
            created_at=now,
            updated_at=now
        )
        self.session.add(rule)
        await self.session.flush()
        return rule.id
    async def get_rule(self, rule_id: int) -> Optional[RuleDbModel]:
        result = await self.session.execute(select(Rule).where(Rule.id == rule_id))
        rule = result.scalar_one_or_none()
        return self._to_dict(rule) if rule else None
    async def get_all_rules(self, status: Optional[str] = None) -> List[RuleDbModel]:
        stmt = select(Rule)
        if status:
            stmt = stmt.where(Rule.status == status)
        stmt = stmt.order_by(Rule.id.desc())
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_dict(r) for r in rows]
    async def get_active_rules(self, domain: str = "all") -> List[RuleDbModel]:
        """有効なルールをドメイン別(または全ドメイン)で取得"""
        stmt = select(Rule).where(Rule.status == 'active')
        if domain == "all":
            stmt = stmt.where(Rule.domain == 'all')
        else:
            stmt = stmt.where(or_(Rule.domain == 'all', Rule.domain == domain))
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_dict(r) for r in rows]
    @retry_on_lock()
    async def update_rule(
        self, rule_id: int, target_word: str, instruction: str, level: str,
        domain: str, character_name: Optional[str], status: str
    ) -> None:
        now = time.strftime('%Y-%m-%dT%H:%M:%S')
        await self.session.execute(
            update(Rule)
            .where(Rule.id == rule_id)
            .values(
                target_word=target_word,
                instruction=instruction,
                level=level,
                domain=domain,
                character_name=character_name,
                status=status,
                updated_at=now
            )
        )
    @retry_on_lock()
    async def update_rule_status(self, rule_id: int, status: str) -> None:
        now = time.strftime('%Y-%m-%dT%H:%M:%S')
        await self.session.execute(
            update(Rule)
            .where(Rule.id == rule_id)
            .values(status=status, updated_at=now)
        )
    @retry_on_lock()
    async def delete_rule(self, rule_id: int) -> None:
        await self.session.execute(
            delete(Rule).where(Rule.id == rule_id)
        )

    # ---------- Masterpieces ----------
    @retry_on_lock()
    async def create_masterpiece(
        self, emotion_or_scene: str, content: str, vector: Optional[List[float]] = None
    ) -> int:
        now = time.strftime('%Y-%m-%dT%H:%M:%S')
        vector_json = json.dumps(vector) if vector is not None else None
        mp = Masterpiece(
            emotion_or_scene=emotion_or_scene,
            content=content,
            vector_json=vector_json,
            created_at=now
        )
        self.session.add(mp)
        await self.session.flush()
        return mp.id
    async def get_all_masterpieces(self) -> List[MasterpieceDbModel]:
        result = await self.session.execute(select(Masterpiece).order_by(Masterpiece.id.desc()))
        rows = result.scalars().all()
        return [self._to_dict(r) for r in rows]
    @retry_on_lock()
    async def delete_masterpiece(self, mp_id: int) -> None:
        await self.session.execute(
            delete(Masterpiece).where(Masterpiece.id == mp_id)
        )
