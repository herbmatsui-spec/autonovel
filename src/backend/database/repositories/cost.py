"""
database/repositories/cost.py - コスト記録(CostRecord)操作用リポジトリ
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from src.services.errors import retry_on_lock
from src.backend.database.models import CostRecord


class CostRepository:
    def __init__(self, session):
        self.session = session

    @retry_on_lock()
    async def add(
        self,
        book_id: int,
        branch_id: int,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        est_cost_usd: float,
        ep_num: Optional[int] = None,
    ) -> int:
        rec = CostRecord(
            book_id=book_id,
            branch_id=branch_id,
            task_type=task_type,
            ep_num=ep_num,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            est_cost_usd=est_cost_usd,
        )
        self.session.add(rec)
        await self.session.flush()
        return rec.id

    @retry_on_lock()
    async def list_by_book(self, book_id: int, branch_id: int = 1) -> List[CostRecord]:
        result = await self.session.execute(
            select(CostRecord)
            .where(CostRecord.book_id == book_id)
            .where(CostRecord.branch_id == branch_id)
            .order_by(CostRecord.created_at)
        )
        return list(result.scalars().all())

    @retry_on_lock()
    async def set_budget(self, book_id: int, budget_usd: float) -> None:
        """予算を内部状態へ保存する（簡易実装）。"""
        await self.session.execute(
            __import__("sqlalchemy").text(
                "INSERT INTO internal_state(key, value) VALUES (:k, :v) "
                "ON CONFLICT(key) DO UPDATE SET value=:v"
            ),
            {"k": f"budget_usd:{book_id}", "v": str(budget_usd)},
        )

    async def aggregate(self, book_id: int, branch_id: int = 1) -> dict:
        rows = await self.list_by_book(book_id, branch_id)
        total_tokens = sum(r.total_tokens for r in rows)
        total_cost = sum(r.est_cost_usd for r in rows)
        by_task = {}
        for r in rows:
            by_task.setdefault(r.task_type, {"tokens": 0, "cost": 0.0, "calls": 0})
            by_task[r.task_type]["tokens"] += r.total_tokens
            by_task[r.task_type]["cost"] += r.est_cost_usd
            by_task[r.task_type]["calls"] += 1
        return {
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "record_count": len(rows),
            "by_task": by_task,
            "timeseries": [
                {
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "total_tokens": r.total_tokens,
                    "est_cost_usd": r.est_cost_usd,
                    "task_type": r.task_type,
                }
                for r in rows
            ],
        }
