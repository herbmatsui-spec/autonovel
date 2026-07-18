import logging
from typing import Any

from dependency_injector.wiring import Provide, inject

from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer

logger = logging.getLogger(__name__)

class StateManager:
    """アプリケーション状態の管理を行うサービス"""

    @inject
    def __init__(self, uow: UnitOfWork = Provide[AppContainer.uow]):
        self.uow = uow

    async def save_state(self, key: str, value: Any):
        """状態の保存"""
        async with self.uow:
            await self.uow.misc.save_internal_state(key, value)
            await self.uow.commit()

    async def get_state(self, key: str) -> Any:
        """状態の取得"""
        return await self.uow.misc.get_internal_state(key)
