from typing import Any, Dict, List, Optional
from src.shared.result import Result
from src.shared.errors import GenerationError
from src.easy_mode.spice_guard import SpiceGuard, SpiceElement


class RewriteOrchestrator:
    def __init__(self, writer, auditor, spice_guard: SpiceGuard):
        self.writer = writer
        self.auditor = auditor
        self.spice_guard = spice_guard

    async def rewrite_until_pass(self, content: str, context: dict,
                                  max_iter: int = 3,
                                  target_score: float = 95.0
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
        current = content
        for i in range(max_iter):
            audit = await self.auditor.audit(current, context)
            if audit.get("score", 0) >= target_score:
                return Result.ok({"content": current, "iterations": i})
            spice = self.spice_guard.extract_spice(current)
            current = await self.writer.rewrite(current, 
                                                  audit.get("improvements", []),
                                                  spice)
        return Result.ok({"content": current, "iterations": max_iter,
                          "needs_human_review": True})