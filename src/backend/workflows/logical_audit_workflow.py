from typing import Any, Dict

from src.shared.utils import StatusReporter

from .base_workflow import BaseWorkflow


class LogicalAuditWorkflow(BaseWorkflow):
    """論理監査ワークフロー (Shadow Mode): 非同期でエピソードを監査し、不整合をDBにIssueとして保存する"""
    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        book_id = kwargs["book_id"]
        branch_id = kwargs.get("branch_id", 1)
        ep_from = kwargs["ep_from"]
        ep_to = kwargs["ep_to"]

        reporter.report(f"⚖️ 非同期監査 (Shadow Mode) 開始: 第{ep_from}話 〜 第{ep_to}話", "info")

        issues_count = 0
        from src.backend.database import UnitOfWork
        async with UnitOfWork(self.repo.db) as uow:
            for ep in range(ep_from, ep_to + 1):
                plot = await uow.plots.get_plot(branch_id, ep)
                chapter = await uow.chapters.get_chapter(branch_id, ep)
                if not plot or not chapter:
                    continue

                # Run the auditor agent
                issue_list = await self.auditor.audit_plot_as_issues(
                    book_id=book_id,
                    branch_id=branch_id,
                    ep_num=ep,
                    plot_bp=plot.detailed_blueprint or "",
                    script=chapter.content or ""
                )

                if not issue_list.is_consistent:
                    for issue in issue_list.issues:
                        await uow.audit.create_audit_issue(
                            book_id=book_id,
                            ep_num=ep,
                            category=issue.category,
                            severity=issue.severity,
                            description=issue.description,
                            evidence_past=issue.evidence_past,
                            evidence_current=issue.evidence_current,
                            constraint_for_next_ep=issue.constraint_for_next_ep
                        )
                        issues_count += 1
                        reporter.report(f"⚠️ 矛盾を検出 (第{ep}話): {issue.description}", "warning")

        reporter.report(f"⚖️ 監査完了: {issues_count} 件のIssueが記録されました。", "info")
        return {"issues_found": issues_count, "book_id": book_id}
