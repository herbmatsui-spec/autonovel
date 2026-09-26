"""40話商業ビートシート生成ワークフロー（SSOT接続版）。

- フェーズ定義は src.config.commercial_beat_sheet.COMMERCIAL_40EP_BEATS を使う
- データ仕様は src.models.beat_sheet.EpisodeBeat を使う
- LLM 呼び出しは PlanningAgent.generate_commercial_beat_sheet に委譲する
"""
from __future__ import annotations

import logging
from typing import Any

from src.agents.planning import PlanningAgent
from src.backend.database.uow import UnitOfWork
from src.backend.workflows.base_workflow import BaseWorkflow
from src.models.beat_sheet import EpisodeBeat
from src.shared.utils import StatusReporter

logger = logging.getLogger(__name__)

DEFAULT_BRANCH_ID = 1


class CommercialBeatSheetWorkflow(BaseWorkflow):
    """BaseWorkflow の __init__（repo= / prompt_manager= / llm= 等）を受ける。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.prompt_manager = kwargs.pop("prompt_manager", None) or getattr(self, "pm", None)
        self.llm = kwargs.pop("llm", None) or getattr(self, "llm_client", None)
        super().__init__(*args, **kwargs)

    async def execute(self, reporter: StatusReporter, **kwargs: Any) -> dict[str, Any]:
        """BaseWorkflow の抽象メソッド実装。"""
        book_id = kwargs.pop("book_id", 1)
        title = kwargs.pop("title", "")
        synopsis = kwargs.pop("synopsis", "")
        beats = await self.generate(
            book_id=book_id,
            title=title,
            synopsis=synopsis,
            reporter=reporter,
            **kwargs,
        )
        return {"beats": [b.model_dump() for b in beats]}

    async def generate(
        self,
        *,
        book_id: int,
        title: str,
        synopsis: str,
        genre: str = "fantasy",
        target_episodes: int = 40,
        branch_id: int = DEFAULT_BRANCH_ID,
        reporter: StatusReporter | None = None,
    ) -> list[EpisodeBeat]:
        """ビートシートを生成し、Plot として保存して返す。"""
        if reporter:
            reporter.set_message("40話ビートシートを生成中...")

        agent = PlanningAgent(repo=self.repo, llm=self.llm, prompt_manager=self.prompt_manager)
        beats = await agent.generate_commercial_beat_sheet(
            title=title,
            synopsis=synopsis,
            genre=genre,
        )
        normalized = self._normalize(beats, target_episodes)
        await self._persist(book_id=book_id, beats=normalized, branch_id=branch_id)
        return normalized

    @staticmethod
    def _normalize(beats: list[EpisodeBeat], target_episodes: int) -> list[EpisodeBeat]:
        """話数の重複・欠損・範囲外を正規化する。"""
        by_ep: dict[int, EpisodeBeat] = {}
        for beat in beats:
            ep = int(getattr(beat, "ep_num", 0) or 0)
            if ep < 1 or ep > target_episodes:
                continue
            by_ep.setdefault(ep, beat)
        return [by_ep[ep] for ep in sorted(by_ep)]

    @staticmethod
    async def _persist(*, book_id: int, beats: list[EpisodeBeat], branch_id: int) -> None:
        """既存 Plot を消さずに upsert する（全削除はしない）。"""
        from src.core.container import AppContainer

        async with UnitOfWork(AppContainer.db()) as uow:
            for beat in beats:
                await uow.plots.create_or_replace_plot(
                    book_id=book_id,
                    ep_num=beat.ep_num,
                    thought_process="commercial_beat_sheet_workflow",
                    title=f"第{beat.ep_num}話",
                    summary=beat.mission,
                    detailed_blueprint=beat.visual_scene_focus,
                    next_hook="",
                    tension=int(round(beat.tension_target * 100)),
                    branch_id=branch_id,
                )
