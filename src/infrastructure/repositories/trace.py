"""
database/repositories/trace.py - 生成実行記録(GenerationRun)用リポジトリ
"""

from __future__ import annotations

from sqlalchemy import select

from src.backend.database.models import GenerationRun
from src.services.errors import retry_on_lock


class TraceRepository:
    def __init__(self, session):
        self.session = session

    @retry_on_lock()
    async def add(self, record: dict) -> int:
        run = GenerationRun(
            book_id=record["book_id"],
            chapter_ep=record.get("chapter_ep"),
            task_type=record.get("task_type", "writing"),
            prompt_version=record.get("prompt_version", ""),
            model_name=record.get("model_name", ""),
            params_json=record.get("params_json", "{}"),
            input_hash=record.get("input_hash", ""),
            output_preview=record.get("output_preview", ""),
            trace_id=record.get("trace_id", ""),
        )
        self.session.add(run)
        await self.session.flush()
        return run.id

    @retry_on_lock()
    async def list_by_book(
        self, book_id: int, chapter_ep: int | None = None
    ) -> list[GenerationRun]:
        stmt = select(GenerationRun).where(GenerationRun.book_id == book_id)
        if chapter_ep is not None:
            stmt = stmt.where(GenerationRun.chapter_ep == chapter_ep)
        stmt = stmt.order_by(GenerationRun.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def to_dict(self, run: GenerationRun) -> dict:
        return {
            "id": run.id,
            "chapter_ep": run.chapter_ep,
            "task_type": run.task_type,
            "prompt_version": run.prompt_version,
            "model_name": run.model_name,
            "params_json": run.params_json,
            "input_hash": run.input_hash,
            "output_preview": run.output_preview,
            "trace_id": run.trace_id,
            "created_at": str(run.created_at),
        }
