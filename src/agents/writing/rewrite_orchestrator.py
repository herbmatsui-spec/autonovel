from typing import Any
from src.easy_mode.spice_guard import SpiceGuard
from src.shared.errors import GenerationError
from src.shared.result import Result


class RewriteOrchestrator:
    def __init__(self, writer, auditor, spice_guard: SpiceGuard):
        self.writer = writer
        self.auditor = auditor
        self.spice_guard = spice_guard

    async def rewrite_until_pass(
        self, content: str, context: dict, max_iter: int = 3, target_score: float = 95.0, budget_tracker: Any = None
    ) -> Result[dict, GenerationError]:
        """
        指定スコアに達するまでリライトを繰り返す。予算超過時は最高スコア版を返す。

        Args:
            content: 元の本文
            context: プロット情報などのコンテキスト
            max_iter: 最大リライト回数
            target_score: 目標スコア
            budget_tracker: オプションのトークンバジェットトラッカー

        Returns:
            Result.ok({"content": str, "iterations": int, "needs_human_review": bool})
            または Result.err(GenerationError)
        """
        current = content
        best_content = content
        best_score = -1.0

        for i in range(max_iter):
            try:
                if budget_tracker is not None and not budget_tracker.is_within_budget():
                    break
                audit = await self.auditor.audit(current, context)
                score = audit.get("score", 0)
                if score > best_score:
                    best_score = score
                    best_content = current

                if score >= target_score:
                    return Result.ok({"content": current, "iterations": i})
                spice = self.spice_guard.extract_spice(current)
                current = await self.writer.rewrite(current, audit.get("improvements", []), spice)
            except Exception as e:
                from src.services.billing.token_budget_tracker import CostBudgetExceededError
                if isinstance(e, CostBudgetExceededError):
                    break
                raise e

        return Result.ok({"content": best_content, "iterations": max_iter, "needs_human_review": True})
