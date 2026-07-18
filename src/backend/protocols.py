"""
protocols.py - エンジン分解 (ADR-0004) のための共有インターフェース定義。

各ドメインサービス (PlanningService / WritingService / CritiqueService /
BibleService / TensionService) が実装し、ワークフローが依存する Protocol を定義する。
Protocol を使うことで、実装の置換・モックが import サイクルなしで可能になる。
"""
from __future__ import annotations

from typing import Any, Optional, Protocol, Tuple


# ---------------------------------------------------------------------------
# PlanningPort: 企画・プロット生成
# ---------------------------------------------------------------------------
class PlanningPort(Protocol):
    """企画立案・プロット展開を担当するサービスのインターフェース。"""

    async def create_hegemony_plan(
        self,
        genre: str = None,
        keywords: str = None,
        style_key: str = None,
        concept: str = None,
        title: str = "",
        cheat_scale: int = 4,
        growth_curve: str = "最初からカンスト(無双)",
        system_assist: int = 70,
        cost_severity: int = 2,
        target_eps: int = 10,
        initial_plot_limit: int = 3,
        config: Any = None,
        reporter: Any = None,
    ) -> Tuple[int, Any]:
        ...

    async def expand_plots(self, *args: Any, **kwargs: Any) -> Any:
        ...

    async def rebuild_hegemony_plot(self, *args: Any, **kwargs: Any) -> Any:
        ...

    async def audit_bible_completeness(self, bible: Any, reporter: Any = None) -> bool:
        ...


# ---------------------------------------------------------------------------
# WritingPort: 本文執筆・研磨
# ---------------------------------------------------------------------------
class WritingPort(Protocol):
    """本文生成・パイプライン執筆を担当するサービスのインターフェース。"""

    async def generate_episodes_pipeline(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Any,
        branch_id: int = 1,
        style_tag: Any = None,
    ) -> Tuple[int, list]:
        ...

    async def generate_episodes(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Any,
        branch_id: int = 1,
        style_tag: Any = None,
    ) -> int:
        ...

    async def analyze_and_import_chapter(self, *args: Any, **kwargs: Any) -> Any:
        ...


# ---------------------------------------------------------------------------
# CritiquePort: 品質分析・論理監査
# ---------------------------------------------------------------------------
class CritiquePort(Protocol):
    """品質最適化・論理監査を担当するサービスのインターフェース。"""

    async def run_iterative_gap_analysis(self, book_id: int, *args: Any, **kwargs: Any) -> Any:
        ...

    async def audit_plot_as_issues(self, *args: Any, **kwargs: Any) -> Any:
        ...


# ---------------------------------------------------------------------------
# BiblePort: 設定集ライフサイクル
# ---------------------------------------------------------------------------
class BiblePort(Protocol):
    """設定集 (Bible) の同期・承認管理を担当するサービスのインターフェース。"""

    async def sync_bible_lifecycle(self, book_id: int, reporter: Any = None) -> Any:
        ...

    async def resolve_pending_setting(self, setting_id: int, status: str) -> None:
        ...

    async def get_latest_bible(self, book_id: int) -> Optional[Any]:
        ...


# ---------------------------------------------------------------------------
# TensionPort: テンション曲線・カタルシス
# ---------------------------------------------------------------------------
class TensionPort(Protocol):
    """テンション目標値の算出・検証を担当するサービスのインターフェース。"""

    async def determine_target_tension(
        self,
        book_id: int,
        ep_num: int,
        genre: str,
        story_type: Optional[str] = None,
    ) -> float:
        ...

    async def validate_tension_deviation(
        self,
        ep_num: int,
        generated_tension: float,
        book_id: int,
        tolerance: float = 0.2,
    ) -> Tuple[bool, float]:
        ...


# ---------------------------------------------------------------------------
# DataRepositoryPort: ワークフローが参照するリポジトリ操作
# ---------------------------------------------------------------------------
class DataRepositoryPort(Protocol):
    """ワークフローが読み取りで利用するリポジトリ操作のインターフェース。"""

    async def get_book(self, book_id: int) -> Optional[Any]:
        ...

    async def get_total_episodes(self, book_id: int) -> int:
        ...

    async def get_latest_bible(self, book_id: int) -> Optional[Any]:
        ...

    @property
    def plots(self) -> Any:
        ...

    @property
    def books(self) -> Any:
        ...


__all__ = [
    "PlanningPort",
    "WritingPort",
    "CritiquePort",
    "BiblePort",
    "TensionPort",
    "DataRepositoryPort",
]
