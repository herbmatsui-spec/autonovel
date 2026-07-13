import json
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update

from services.errors import retry_on_lock
from src.backend.database.models import PromptVersion
from src.backend.database.repositories.base import BaseRepository
from src.models.prompt_version import PromptVersionDbModel


class PromptVersionRepository(BaseRepository):
    """CRUD interface for prompt_versions table"""

    @retry_on_lock()
    async def create_prompt_version(
        self, book_id: int, prompt_key: str, version_tag: str, content: str,
        score_before: Optional[float] = None, score_after: Optional[float] = None,
        ab_test_metrics: Optional[Dict[str, Any]] = None, is_active: bool = False
    ) -> PromptVersion:
        """新しいプロンプトバージョンを作成"""
        version = PromptVersion(
            book_id=book_id,
            prompt_key=prompt_key,
            version_tag=version_tag,
            content=content,
            score_before=score_before,
            score_after=score_after,
            ab_test_metrics=json.dumps(ab_test_metrics or {}, ensure_ascii=False),
            is_active=is_active,
            created_at=time.strftime('%Y-%m-%dT%H:%M:%S')
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def get_prompt_version(self, version_id: int) -> Optional[PromptVersionDbModel]:
        """IDからプロンプトバージョンを取得"""
        result = await self.session.execute(
            select(PromptVersion).where(PromptVersion.id == version_id)
        )
        row = result.scalar_one_or_none()
        if row:
            return self._parse_row(self._to_dict(row), ['ab_test_metrics'])
        return None

    async def get_prompt_versions(self, book_id: int, limit: int = 20) -> List[PromptVersionDbModel]:
        """本に紐づくプロンプトバージョン一覧を取得"""
        result = await self.session.execute(
            select(PromptVersion)
            .where(PromptVersion.book_id == book_id)
            .order_by(PromptVersion.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [self._parse_row(self._to_dict(r), ['ab_test_metrics']) for r in rows]

    async def get_active_prompt_version(self, book_id: int, prompt_key: str) -> Optional[PromptVersionDbModel]:
        """現在アクティブなプロンプトバージョンを取得"""
        result = await self.session.execute(
            select(PromptVersion)
            .where(PromptVersion.book_id == book_id)
            .where(PromptVersion.prompt_key == prompt_key)
            .where(PromptVersion.is_active == True)
        )
        row = result.scalar_one_or_none()
        if row:
            return self._parse_row(self._to_dict(row), ['ab_test_metrics'])
        return None

    @retry_on_lock()
    async def set_active_prompt_version(self, book_id: int, prompt_key: str, version_id: int) -> None:
        """指定したバージョンをアクティブに設定し、他を非アクティブにする"""
        # すべて非アクティブ化
        await self.session.execute(
            update(PromptVersion)
            .where(PromptVersion.book_id == book_id)
            .where(PromptVersion.prompt_key == prompt_key)
            .values(is_active=False)
        )
        # 指定したIDをアクティブ化
        await self.session.execute(
            update(PromptVersion)
            .where(PromptVersion.id == version_id)
            .values(is_active=True)
        )

    @retry_on_lock()
    async def update_score_after(self, version_id: int, score: float) -> None:
        """適用後のA/Bテストスコア（評価値）を更新"""
        await self.session.execute(
            update(PromptVersion)
            .where(PromptVersion.id == version_id)
            .values(score_after=score)
        )

    @retry_on_lock()
    async def update_ab_test_metrics(self, version_id: int, metrics: Dict[str, Any]) -> None:
        """A/Bテストのメトリクス(JSON)を更新する"""
        await self.session.execute(
            update(PromptVersion)
            .where(PromptVersion.id == version_id)
            .values(ab_test_metrics=json.dumps(metrics, ensure_ascii=False))
        )

    @retry_on_lock()
    async def record_rollback(self, version_id: int, reason: str) -> None:
        """ロールバック時の理由を記録し、非アクティブにする"""
        await self.session.execute(
            update(PromptVersion)
            .where(PromptVersion.id == version_id)
            .values(is_active=False, rollback_reason=reason)
        )
