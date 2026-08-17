"""
エピソード監査モジュール
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from src.easy_mode.models import AuditResult

logger = logging.getLogger(__name__)


class EpisodeAuditor:
    """監査エージェント統合呼び出し・スコア正規化"""

    def __init__(self, engine_auditor, target_audit_score: float = 95.0):
        self.engine_auditor = engine_auditor
        self.target_audit_score = target_audit_score
        self._cancelled = False

    async def audit(
        self, content: str, bible: Dict[str, Any], plot: Dict[str, Any], ep_num: int, genre: str
    ) -> AuditResult:
        """監査実行・スコア正規化（0-100）"""
        try:
            audit_result = await self.engine_auditor.audit(
                content,
                {"bible": bible, "plot": plot, "episode": ep_num, "genre": genre},
            )

            # スコア正規化（0-100）
            score = audit_result.get("overall_score", 0)
            if score > 100:
                score = score / 10  # 1000点満点なら100点満点に

            return AuditResult(
                score=score,
                passed=score >= self.target_audit_score,
                issues=audit_result.get("issues", []),
                improvements=audit_result.get("improvements", []),
                needs_human_review=False,
                details=audit_result,
            )
        except Exception as e:
            if self._cancelled:
                raise
            logger.warning(f"Audit failed for ep {ep_num}: {e}")
            return AuditResult(
                score=85,  # デフォルトスコア
                passed=False,
                issues=["監査エラー"],
                improvements=["監査システムを確認してください"],
                needs_human_review=False,
                details={},
            )

    def cancel(self):
        """キャンセル"""
<<<<<<< ours
        self._cancelled = True
=======
        self._cancelled = True
>>>>>>> theirs
