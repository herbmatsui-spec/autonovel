# src/agents/audit_agent.py
from __future__ import annotations

from typing import Any

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName
from src.agents.audit import (
    LogicalAuditor,
    DeAIAuditor,
    FastPlotScreener,
    AbilityConsistencyChecker,
    PlotIntegrityMonitor,
)
from src.services.learning_data_service import LearningDataService


class AuditAgent(SkillAgent):
    """品質監査を担当するエージェント（ファサード）。
    既存の複数の監査クラスを統合し、統一インターフェースを提供する。
    学習データ（ネガティブサンプル）を活用して監査精度を動的に調整する。
    """

    def __init__(
        self,
        repo: Any = None,
        llm: Any = None,
        prompt_manager: Any = None,
        edge_preserver: Any = None,
        **kwargs,
    ):
        super().__init__(repo=repo, llm=llm)
        self.prompt_manager = prompt_manager

        # 内部監査コンポーネントを初期化
        self._logical_auditor = LogicalAuditor(
            repo=repo, llm=llm, pm=prompt_manager, generate_json=llm
        )
        self._deai_auditor = DeAIAuditor(
            repo=repo, llm=llm, prompt_manager=prompt_manager, edge_preserver=edge_preserver
        )
        self._fast_screener = FastPlotScreener(llm=llm, prompt_manager=prompt_manager)
        self._ability_checker = AbilityConsistencyChecker(llm=llm, prompt_manager=prompt_manager)
        self._plot_monitor = PlotIntegrityMonitor()

        # 学習データサービス
        self._learning_service = LearningDataService(repo=repo)

    async def _check_learning_adjustment(
        self, audit_type: str, field_path: str | None = None
    ) -> tuple[bool, float]:
        """学習データに基づく監査調整をチェック

        Returns:
            (should_downgrade, confidence_adjustment)
            - should_downgrade: True の場合、この監査失敗を warning 扱いにして auto-retry しない
            - confidence_adjustment: 信頼度調整値 (-1.0 ~ 1.0)
        """
        if self.repo is None:
            return False, 0.0

        try:
            return await self._learning_service.should_skip_audit_type(audit_type, field_path)
        except Exception:
            # 学習サービスエラーは無視してデフォルト動作
            return False, 0.0

    async def _create_patch_review(
        self,
        book_id: int,
        ep_num: int,
        patch_type: str,
        original_content: str,
        proposed_content: str,
        audit_issues: list[dict],
        learning_metadata: dict | None = None,
    ) -> int:
        """PatchReview レコードを作成し、IDを返す"""
        if self.repo is None:
            return 0

        # diff_json を生成（簡易版）
        diff_json = {
            "type": "audit_failure",
            "issues": audit_issues,
        }

        return await self.repo.misc.create_patch_review(
            book_id=book_id,
            ep_num=ep_num,
            patch_type=patch_type,
            original_content=original_content,
            proposed_content=proposed_content,
            diff_json=diff_json,
            audit_issue_ids=[
                issue.get("issue_id", 0) for issue in audit_issues if issue.get("issue_id")
            ],
            learning_metadata=learning_metadata,
        )

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """スキル実行エントリーポイント。"""
        writing_context = ctx.artifacts.get("writing_context")
        drafted_text = ctx.artifacts.get("drafted_text")

        if not writing_context or not drafted_text:
            return AgentResult(
                next_agent=None,
                artifacts={},
                error="writing_context and drafted_text are required in artifacts",
            )

        book_id = ctx.book_id
        ep_num = ctx.ep_num

        failed_audits = []
        learning_adjusted_audits = []  # 学習データで調整された監査

        try:
            # 1. プロット高速スクリーニング
            blueprint = writing_context.get("plot", {}).get("detailed_blueprint", "")
            if blueprint:
                is_valid, feedback = await self._fast_screener.screen_plot(blueprint)
                if not is_valid:
                    should_downgrade, conf_adj = await self._check_learning_adjustment(
                        "fast_screen"
                    )
                    failed_audits.append(
                        {
                            "type": "fast_screen",
                            "feedback": feedback,
                            "severity": "high",
                            "learning_adjusted": should_downgrade,
                            "confidence_adjustment": conf_adj,
                        }
                    )
                    if should_downgrade:
                        learning_adjusted_audits.append("fast_screen")

            # 2. 論理整合性監査
            logical_ok, logical_feedback, _ = await self._logical_auditor.audit_logical_consistency(
                book_id=book_id, ep_num=ep_num, blueprint=blueprint
            )
            if not logical_ok:
                should_downgrade, conf_adj = await self._check_learning_adjustment(
                    "logical_consistency"
                )
                failed_audits.append(
                    {
                        "type": "logical_consistency",
                        "feedback": logical_feedback,
                        "severity": "high",
                        "learning_adjusted": should_downgrade,
                        "confidence_adjustment": conf_adj,
                    }
                )
                if should_downgrade:
                    learning_adjusted_audits.append("logical_consistency")

            # 3. AI感除去監査（DeAI）
            edges = writing_context.get("sharp_edges", [])
            emotional_hook = writing_context.get("emotional_hook")
            deai_ok, deai_feedback = await self._deai_auditor.audit(
                content=drafted_text,
                before_content=writing_context.get("prev_ctx", ""),
                edges=edges,
                emotional_hook=emotional_hook,
            )
            if not deai_ok:
                should_downgrade, conf_adj = await self._check_learning_adjustment("deai")
                failed_audits.append(
                    {
                        "type": "deai",
                        "feedback": deai_feedback,
                        "severity": "medium",
                        "learning_adjusted": should_downgrade,
                        "confidence_adjustment": conf_adj,
                    }
                )
                if should_downgrade:
                    learning_adjusted_audits.append("deai")

            # 4. 能力整合性チェック
            settings_json = writing_context.get("world_settings", "{}")
            chars_json = writing_context.get("characters_json", "[]")
            ability_ok, ability_feedback, _ = await self._ability_checker.audit_ability_consistency(
                blueprint=drafted_text, settings_json=settings_json, characters_json=chars_json
            )
            if not ability_ok:
                should_downgrade, conf_adj = await self._check_learning_adjustment(
                    "ability_consistency"
                )
                failed_audits.append(
                    {
                        "type": "ability_consistency",
                        "feedback": ability_feedback,
                        "severity": "medium",
                        "learning_adjusted": should_downgrade,
                        "confidence_adjustment": conf_adj,
                    }
                )
                if should_downgrade:
                    learning_adjusted_audits.append("ability_consistency")

            # 5. プロット整合性モニター（因果律）
            keywords = self._plot_monitor.extract_keywords(drafted_text)
            causal_ok, score, failures = await self._plot_monitor.check_integrity(
                keywords=keywords,
                blueprint=blueprint,
                content=drafted_text,
                threshold=0.7,
            )
            if not causal_ok:
                should_downgrade, conf_adj = await self._check_learning_adjustment(
                    "causal_integrity"
                )
                failed_audits.append(
                    {
                        "type": "causal_integrity",
                        "feedback": str(failures),
                        "severity": "high",
                        "learning_adjusted": should_downgrade,
                        "confidence_adjustment": conf_adj,
                    }
                )
                if should_downgrade:
                    learning_adjusted_audits.append("causal_integrity")

            # 学習調整された監査がある場合のログ
            if learning_adjusted_audits:
                # ログ出力（実際の実装では適切なロガーを使用）
                import logging

                logger = logging.getLogger(__name__)
                logger.info(f"Learning-adjusted audits for Ep.{ep_num}: {learning_adjusted_audits}")

            # 監査失敗がある場合：PatchReview を作成してユーザー確認を要求
            if failed_audits:
                # 既存の AuditIssue レコードを作成（Shadow Mode 用）
                issue_ids = []
                if self.repo:
                    for audit in failed_audits:
                        # 学習調整された場合は severity を下げる
                        severity = audit["severity"]
                        if audit.get("learning_adjusted"):
                            severity = "medium" if severity == "high" else "low"

                        issue_id = await self.repo.audit.create_audit_issue(
                            book_id=book_id,
                            ep_num=ep_num,
                            category=audit["type"],
                            severity=severity,
                            description=audit["feedback"],
                        )
                        issue_ids.append(issue_id)

                # PatchReview 作成
                patch_review_id = await self._create_patch_review(
                    book_id=book_id,
                    ep_num=ep_num,
                    patch_type="audit_failure",
                    original_content=drafted_text,
                    proposed_content="",  # ユーザーが修正案を提示するまで空
                    audit_issues=[
                        {"type": a["type"], "feedback": a["feedback"], "issue_id": iid}
                        for a, iid in zip(failed_audits, issue_ids)
                    ],
                    learning_metadata={
                        "negative_sample_candidates": [a["type"] for a in failed_audits],
                        "learning_adjusted": learning_adjusted_audits,
                    },
                )

                return AgentResult(
                    next_agent=AgentName.WRITING,
                    should_retry=False,  # 自動リトライせず、ユーザー承認待ち
                    artifacts={
                        "audit_feedback": "Audit failed - user review required",
                        "requires_user_review": True,
                        "patch_review_id": patch_review_id,
                        "failed_audits": failed_audits,
                        "learning_adjusted_audits": learning_adjusted_audits,
                    },
                )

            # 全監査合格
            return AgentResult(
                next_agent=AgentName.ILLUSTRATION,
                artifacts={
                    "audit_report": {
                        "logical": "passed",
                        "deai": "passed",
                        "ability": "passed",
                        "causal": "passed",
                    }
                },
            )

        except Exception as e:
            return AgentResult(
                next_agent=None,
                artifacts={},
                error=f"Audit failed with exception: {e}",
            )

    async def run(self, ctx: AgentContext) -> AgentResult:
        """Orchestrator 用エントリーポイント。execute をラップする。"""
        return await self.execute(ctx)
