"""
critique_service.py - CritiqueService: 品質分析・論理監査を担当するドメインサービス。

UltimateHegemonyEngine から分離し、CritiquePort インターフェースを実装する。
"""
from typing import Any, Optional, Tuple
from src.backend.protocols import CritiquePort

class CritiqueService(CritiquePort):
    """品質最適化・論理監査を担当するサービス。"""

    def __init__(
        self,
        critique: Any,  # CritiqueAgent 実体
        repo: Any,       # DataRepository
        pm: Any,         # PromptManager
    ) -> None:
        self.critique = critique
        self.repo = repo
        self.pm = pm

    async def run_iterative_gap_analysis(
        self, 
        book_id: int, 
        *args: Any, 
        **kwargs: Any
    ) -> Any:
        """
        反復的なギャップ分析を実行する。
        実際の実行は critique.run_iterative_gap_analysis に委譲。
        """
        return await self.critique.run_iterative_gap_analysis(
            book_id=book_id,
            *args,
            **kwargs
        )

    async def audit_plot_as_issues(
        self, 
        *args: Any, 
        **kwargs: Any
    ) -> Any:
        """
        プロットを論理的な問題点として監査する。
        実際の実行は critique.audit_plot_as_issues に委譲。
        """
        return await self.critique.audit_plot_as_issues(
            *args,
            **kwargs
        )
