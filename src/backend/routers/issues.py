from fastapi import APIRouter
from typing import Any
import json
import time

from config.container import Container
from src.backend.database.uow import UnitOfWork
from src.core.exceptions import NotFoundError, ValidationError

router = APIRouter(prefix="/api/issues", tags=["issues"])

@router.get("/books/{book_id}")
async def get_issues(book_id: int):
    async with UnitOfWork(Container.db()) as uow:
        return await uow.issues.get_book_issues(book_id)

@router.post("/{issue_id}/resolve")
async def resolve_issue(issue_id: int, req: Any):
    # Note: ResolveIssueRequest should be imported from api_schemas
    async with UnitOfWork(Container.db()) as uow:
        issue = await uow.audit.get_issue(issue_id)
        if not issue:
            raise NotFoundError("Issue not found", resource_type="AuditIssue", resource_id=str(issue_id))

        book_id = issue["book_id"]
        ep_num = issue["ep_num"]

        if req.action == "Auto-Fix":
            # Auto-Fix: Mark resolved and we can trigger rewrite or let user know
            await uow.audit.update_issue_status(issue_id, "resolved", resolved_note="Auto-Fix triggered")
            return {"status": "success", "message": "Issue marked as resolved via Auto-Fix."}

        elif req.action == "Foreshadowing":
            # Foreshadowing: Mark as foreshadowed in DB and add to WorldBible foreshadowing_map
            await uow.audit.update_issue_status(issue_id, "foreshadowed", resolved_note="Marked as Foreshadowing")

            # Add to Bible settings
            bible = await uow.bible.get_latest_bible(book_id)
            if bible:
                settings = json.loads(bible.settings or "{}") if isinstance(bible.settings, str) else bible.settings or {}
                f_map = settings.get("foreshadowing_map", [])

                # Check if already exists to prevent duplicate
                if not any(f.get("description") == issue["description"] for f in f_map):
                    f_map.append({
                        "setup_ep": f"第{ep_num}話",
                        "payoff_ep": f"第{ep_num + 5}話",  # arbitrary offset
                        "description": issue["description"],
                        "exposure_level": 3
                    })
                    settings["foreshadowing_map"] = f_map
                    await uow.bible.create_bible(
                        book_id=book_id,
                        settings=settings,
                        version=(bible.version or 0) + 1,
                        last_updated=time.strftime('%Y-%m-%dT%H:%M:%S')
                    )
            return {"status": "success", "message": "Issue registered as Foreshadowing in WorldBible."}

        elif req.action == "Ignore":
            # Ignore: Mark as ignored, add to exception rules
            await uow.audit.update_issue_status(issue_id, "ignored", resolved_note="Ignored (Rule of Cool)")

            # Record exceptions in rules table
            await uow.rules.create_rule(
                target_word=issue["category"],
                instruction=f"許容された例外 (Rule of Cool): {issue['description']}",
                level="project",
                domain="all",
                character_name=None,
                status="active"
            )
            return {"status": "success", "message": "Issue ignored and logged under Rule of Cool exceptions."}

        else:
            raise ValidationError(f"Invalid action type: {req.action}")
