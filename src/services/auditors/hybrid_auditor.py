"""Two-Tier Hybrid Auditor サービス (v5.0 A4 Step 23 連携).

静的ルール解析（語尾・禁忌・NG表現・0ms/0円）と定性評価判定を行い、
IntegratedAuditReport ドメインモデルを返却する。
"""
from __future__ import annotations

import time
from typing import List, Optional
from src.agents.specialists.unified_auditor import UnifiedAuditor
from src.domain.schemas.audit import (
    IntegratedAuditReport,
    StaticAuditResult,
    QualitativeAuditResult,
    AuditIssue,
)


class TwoTierAuditor:
    """二層ハイブリッド監査ファサード。"""

    @classmethod
    async def audit_chapter(
        cls,
        text: str,
        forbidden_words: Optional[List[str]] = None,
        character_profiles: str = "",
        plot_spec: str = "",
    ) -> IntegratedAuditReport:
        t0 = time.perf_counter()
        auditor = UnifiedAuditor()
        q_score, meta = auditor.audit_quantitative(text)

        issues: List[AuditIssue] = []
        # NGワード検査
        if forbidden_words:
            for word in forbidden_words:
                if word in text:
                    issues.append(
                        AuditIssue(
                            rule_id="forbidden_word",
                            severity="error",
                            message=f"禁止語句が検出されました: {word}",
                            suggested_fix=f"該当箇所を削除または修正してください",
                        )
                    )

        static_passed = len(issues) == 0 and len(meta.get("cliches", [])) < 3
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        static_res = StaticAuditResult(
            passed=static_passed,
            execution_time_ms=round(elapsed_ms, 2),
            issues=issues,
        )

        qual_model = await auditor.audit_qualitative(text, character_profiles, plot_spec)
        qual_res = QualitativeAuditResult(
            score=int(qual_model.overall_score),
            pacing_comment=f"Hook score: {qual_model.hook_score}",
            character_voice_comment=f"Character consistency: {qual_model.character_consistency}",
            entertaining_hook_comment=f"Emotional score: {qual_model.emotional_score}",
            suggested_patch=qual_model.actionable_patch or "",
        )

        final_decision = "pass" if (static_passed and qual_res.score >= 70) else "patch_required"

        return IntegratedAuditReport(
            static_audit=static_res,
            qualitative_audit=qual_res,
            final_decision=final_decision,
        )
