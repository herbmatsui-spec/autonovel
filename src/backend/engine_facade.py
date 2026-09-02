"""
engine_facade.py - UltimateHegemonyEngine の後方互換ファサード。

背景:
    UltimateHegemonyEngine は 42 引数の「神クラス」となっている。
    本モジュールは、既存の engine.* 呼び出し側 (workflows / routers / streamlit)
    を壊さずに済むよう、engine インスタンスを内包して同じインターフェースを
    提供する薄いファサードである。

    今後のフェーズ (ADR-0004) で、内包する engine を
    CoreEngine + 5つのドメインサービスへ段階的に置換していく。
"""

from __future__ import annotations

import logging
from typing import Any

from src.backend.engine_config import EngineConfig

logger = logging.getLogger(__name__)


class EngineFacade:
    """
    既存の UltimateHegemonyEngine を内包し、そのまま委譲するファサード。

    将来的なサービス分割 (PlanningService / WritingService 等) への
    移行足場となる。現在は engine への純粋な転送層。
    """

    def __init__(
        self,
        config: EngineConfig,
        engine: Any,
    ) -> None:
        self._config = config
        self._engine = engine

    # ---- 後方互換プロパティ (engine の属性をそのまま公開) ----
    @property
    def api_key(self) -> str:
        return self._config.api_key

    @property
    def cooldown(self) -> Any:  # noqa: ANN401
        return self._config.cooldown

    @property
    def engine_impl(self) -> Any:  # noqa: ANN401
        """内包する実体エンジン (今後の置換で消える一時的なアクセサ)。"""
        return self._engine

    @property
    def repo(self) -> Any:  # noqa: ANN401
        return self._engine.repo

    @property
    def llm(self) -> Any:  # noqa: ANN401
        return self._engine.llm

    @property
    def pm(self) -> Any:  # noqa: ANN401
        return self._engine.pm

    @property
    def ctx_mgr(self) -> Any:  # noqa: ANN401
        return self._engine.ctx_mgr

    @property
    def formatter(self) -> Any:  # noqa: ANN401
        return self._engine.formatter

    @property
    def validator(self) -> Any:  # noqa: ANN401
        return self._engine.validator

    @property
    def auditor(self) -> Any:  # noqa: ANN401
        return self._engine.auditor

    @property
    def narrative(self) -> Any:  # noqa: ANN401
        return self._engine.narrative

    @property
    def critique(self) -> Any:  # noqa: ANN401
        return self._engine.critique

    @property
    def marketing(self) -> Any:  # noqa: ANN401
        return self._engine.marketing

    @property
    def bible_agent(self) -> Any:  # noqa: ANN401
        return self._engine.bible_agent

    @property
    def plot_agent(self) -> Any:  # noqa: ANN401
        return self._engine.plot_agent

    @property
    def style_rag(self) -> Any:  # noqa: ANN401
        return self._engine.style_rag

    @property
    def db(self) -> Any:  # noqa: ANN401
        return self._engine.db

    @property
    def planner(self) -> Any:  # noqa: ANN401
        return self._engine.planner

    @property
    def writer(self) -> Any:  # noqa: ANN401
        return self._engine.writer

    @property
    def plot_service(self) -> Any:  # noqa: ANN401
        return self._engine.plot_service

    @property
    def logic_validator(self) -> Any:  # noqa: ANN401
        return self._engine.validator

    @property
    def generate_json(self) -> Any:  # noqa: ANN401
        return self._engine.llm.generate_json

    def dispose(self) -> None:
        if hasattr(self._engine.db, "engine"):
            self._engine.db.engine.dispose()

    # ---- 明示的に委譲するメソッド (可読性・将来の置換のため) ----

    async def sync_bible(self, book_id: int, reporter: Any | None = None) -> Any:  # noqa: ANN401
        return await self._engine.sync_bible(book_id, reporter=reporter)

    async def resolve_bible_setting(self, setting_id: int, status: str) -> None:
        return await self._engine.resolve_bible_setting(setting_id, status)

    async def determine_target_tension(
        self,
        book_id: int,
        ep_num: int,
        genre: str,
        story_type: str | None = None,
    ) -> float:
        return await self._engine.determine_target_tension(book_id, ep_num, genre, story_type)

    async def validate_tension_deviation(
        self,
        ep_num: int,
        generated_tension: float,
        book_id: int,
        tolerance: float = 0.2,
    ) -> tuple[bool, float]:
        return await self._engine.validate_tension_deviation(
            ep_num, generated_tension, book_id, tolerance
        )
