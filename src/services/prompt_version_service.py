from __future__ import annotations

import logging
from typing import Optional

from dependency_injector import providers
from dependency_injector.wiring import inject, Provide

from src.backend.database.repositories.prompt_versions import PromptVersionRepository
from src.backend.database.uow import UnitOfWork

logger = logging.getLogger(__name__)

class PromptVersionService:
    """プロンプトのバージョン管理とA/Bテストを行うサービス"""

    @inject
    def __init__(
        self,
        uow: UnitOfWork = Provide["config.container.AppContainer.uow"],
        prompt_repo: PromptVersionRepository = Provide["config.container.AppContainer.prompt_repo"]
    ):
        self.uow = uow
        self.prompt_repo = prompt_repo

    async def register_prompt_version(self, book_id: int, prompt_key: str, version_tag: str, content: str, is_active: bool = False) -> int:
        """新しいプロンプトバージョンを登録する"""
        async with self.uow:
            # アクティブにする場合は他のバージョンを非アクティブ化
            if is_active:
                # set_active_prompt_versionに-1を渡すことで全非アクティブ化
                await self.prompt_repo.set_active_prompt_version(book_id, prompt_key, -1)

            version = await self.prompt_repo.create_prompt_version(
                book_id=book_id,
                prompt_key=prompt_key,
                version_tag=version_tag,
                content=content,
                is_active=is_active
            )
            await self.uow.commit()
            return version.id

    async def get_active_prompt(self, book_id: int, prompt_key: str) -> Optional[str]:
        """現在アクティブなプロンプトを取得する"""
        version = await self.prompt_repo.get_active_prompt_version(book_id, prompt_key)
        return version["content"] if version else None

    async def update_ab_test_metrics(self, version_id: int, score: float, samples: int = 1):
        """A/Bテストのメトリクスを更新する"""
        async with self.uow:
            version = await self.prompt_repo.get_prompt_version(version_id)
            if version:
                metrics = version.get("ab_test_metrics", {})
                current_score = metrics.get("avg_score", 0.0)
                current_samples = metrics.get("samples", 0)

                new_samples = current_samples + samples
                new_score = ((current_score * current_samples) + (score * samples)) / new_samples

                metrics["avg_score"] = new_score
                metrics["samples"] = new_samples

                await self.prompt_repo.update_ab_test_metrics(version_id, metrics)
            await self.uow.commit()
