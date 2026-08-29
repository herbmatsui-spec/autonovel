from typing import Any, Optional

from src.easy_mode.spice_guard import SpiceGuard
from src.shared.errors import GenerationError
from src.shared.result import Result


class RewriteOrchestrator:
    def __init__(self, writer: Any, auditor: Optional[Any] = None, spice_guard: Optional[SpiceGuard] = None):
        self.writer = writer
        self.auditor = auditor
        self.spice_guard = spice_guard

    async def rewrite_until_pass(
        self, content: str, context: dict, max_iter: int = 3, target_score: float = 95.0
    ) -> Result[dict, GenerationError]:
        """
        指定スコアに達するまでリライトを繰り返す。

        Args:
            content: 元の本文
            context: プロット情報などのコンテキスト
            max_iter: 最大リライト回数
            target_score: 目標スコア

        Returns:
            Result.ok({"content": str, "iterations": int, "needs_human_review": bool})
            または Result.err(GenerationError)
        """
        if self.auditor is None:
            # auditor が未設定の場合はリライトをスキップして現状維持を返す
            return Result.ok({"content": content, "iterations": 0, "needs_human_review": False})

        current = content
        for i in range(max_iter):
            audit = await self.auditor.audit(current, context)
            if audit.get("score", 0) >= target_score:
                return Result.ok({"content": current, "iterations": i})
            spice = self.spice_guard.extract_spice(current) if self.spice_guard else ""
            if hasattr(self.writer, "rewrite"):
                current = await self.writer.rewrite(current, audit.get("improvements", []), spice)
            else:
                break
        return Result.ok({"content": current, "iterations": max_iter, "needs_human_review": True})
