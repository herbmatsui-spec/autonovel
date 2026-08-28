"""
src/prototype/foreshadow_adapter.py - novel_50ep 用 永続化伏線マネージャ
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

try:
    from novel_50ep.foreshadow_manager import ForeshadowItem, ForeshadowManager
except ImportError:
    from foreshadow_manager import ForeshadowItem, ForeshadowManager


class PersistentForeshadowManager(ForeshadowManager):
    """ForeshadowManager を拡張し、DB (MiscRepository / InternalState) への永続化に対応したクラス"""

    async def persist(
        self,
        book_id: int,
        branch_id: int,
        repo: Optional[Any] = None,
    ) -> None:
        """伏線台帳のデータを DB に永続化する"""
        key = f"fs:{book_id}:{branch_id}"
        # dict / item リストをシリアライズ可能な dict リストへ変換
        serialized: List[Dict[str, Any]] = []
        if self.foreshadows:
            for item in self.foreshadows:
                if isinstance(item, dict):
                    serialized.append(item)
                elif hasattr(item, "__dict__"):
                    serialized.append(dict(item.__dict__))
        else:
            for item in self.load_all():
                if isinstance(item, dict):
                    serialized.append(item)
                elif hasattr(item, "__dict__"):
                    serialized.append(dict(item.__dict__))

        if repo is not None:
            if hasattr(repo, "save_internal_state"):
                await repo.save_internal_state(key, serialized)
        else:
            try:
                from src.backend.database.repositories.misc import MiscRepository
                from src.backend.database.uow import UnitOfWork
                from src.core.container import AppContainer

                async with UnitOfWork(AppContainer.db()) as uow:
                    await uow.misc.save_internal_state(key, serialized)
            except Exception:
                pass

    async def load_persistent(
        self,
        book_id: int,
        branch_id: int,
        repo: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """DB から永続化された伏線データを読み込み、内部リストを更新する"""
        key = f"fs:{book_id}:{branch_id}"
        data: Optional[Any] = None

        if repo is not None:
            if hasattr(repo, "get_internal_state"):
                data = await repo.get_internal_state(key)
        else:
            try:
                from src.backend.database.uow import UnitOfWork
                from src.core.container import AppContainer

                async with UnitOfWork(AppContainer.db()) as uow:
                    data = await uow.misc.get_internal_state(key)
            except Exception:
                data = None

        if data and isinstance(data, list):
            self.foreshadows = list(data)
            return list(data)
        return []

    def persist_sync(self, book_id: int, branch_id: int, repo: Optional[Any] = None) -> None:
        """同期永続化"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(lambda: asyncio.run(self.persist(book_id, branch_id, repo))).result()
        else:
            asyncio.run(self.persist(book_id, branch_id, repo))

    def load_persistent_sync(self, book_id: int, branch_id: int, repo: Optional[Any] = None) -> List[Dict[str, Any]]:
        """同期読み込み"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(lambda: asyncio.run(self.load_persistent(book_id, branch_id, repo))).result()
        else:
            return asyncio.run(self.load_persistent(book_id, branch_id, repo))
