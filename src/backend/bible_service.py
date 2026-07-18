"""
bible_service.py - BibleService: 設定集 (Bible) の同期・承認管理を担当するドメインサービス。

UltimateHegemonyEngine から分離し、BiblePort インターフェースを実装する。
"""
from typing import Any, Optional, Tuple
from src.backend.protocols import BiblePort

class BibleService(BiblePort):
    """設定集の同期・承認管理を担当するサービス。"""

    def __init__(
        self,
        bible_agent: Any,  # WorldBibleGenerator 実体
        repo: Any,         # DataRepository
        pm: Any,           # PromptManager
    ) -> None:
        self.bible_agent = bible_agent
        self.repo = repo
        self.pm = pm

    async def sync_bible_lifecycle(
        self, 
        book_id: int, 
        reporter: Any = None
    ) -> Any:
        """
        設定集のライフサイクル同期を実行する。
        実際の実行は bible_agent.sync_bible_lifecycle に委譲。
        """
        return await self.bible_agent.sync_bible_lifecycle(
            book_id=book_id,
            reporter=reporter
        )

    async def resolve_pending_setting(
        self, 
        setting_id: int, 
        status: str
    ) -> None:
        """
        保留中の設定を解決する。
        実際の実行は bible_agent.resolve_pending_setting に委譲。
        """
        return await self.bible_agent.resolve_pending_setting(
            setting_id=setting_id,
            status=status
        )

    async def get_latest_bible(
        self, 
        book_id: int
    ) -> Optional[Any]:
        """
        最新の設定集を取得する。
        実際の実行は bible_agent.get_latest_bible に委譲。
        """
        return await self.bible_agent.get_latest_bible(
            book_id=book_id
        )
