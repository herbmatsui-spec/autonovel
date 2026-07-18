"""
tension_service.py - TensionService: テンション曲線・カタルシス管理を担当するドメインサービス。

UltimateHegemonyEngine から分離し、TensionPort インターフェースを実装する。
"""
from typing import Any, Optional, Tuple
from src.backend.protocols import TensionPort

class TensionService(TensionPort):
    """テンション目標値の算出・検証を担当するサービス。"""

    def __init__(
        self,
        tension_agent: Any,  # TensionAgent 実体 (Engine内部実装)
        repo: Any,            # DataRepository
    ) -> None:
        self.tension_agent = tension_agent
        self.repo = repo

    async def determine_target_tension(
        self,
        book_id: int,
        ep_num: int,
        genre: str,
        story_type: Optional[str] = None,
    ) -> float:
        """
        エピソードの目標テンション値を算出する。
        実際の実行は tension_agent.determine_target_tension に委譲。
        """
        return await self.tension_agent.determine_target_tension(
            book_id=book_id,
            ep_num=ep_num,
            genre=genre,
            story_type=story_type,
        )

    async def validate_tension_deviation(
        self,
        ep_num: int,
        generated_tension: float,
        book_id: int,
        tolerance: float = 0.2,
    ) -> Tuple[bool, float]:
        """
        生成されたテンション値が目標値から許容範囲内にあるか検証する。
        実際の実行は tension_agent.validate_tension_deviation に委譲。
        """
        return await self.tension_agent.validate_tension_deviation(
            ep_num=ep_num,
            generated_tension=generated_tension,
            book_id=book_id,
            tolerance=tolerance,
        )
