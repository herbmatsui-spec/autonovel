"""backend/routers/consistency.py - 整合性チェック API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from src.backend.auth import require_api_key
from src.consistency.engine import ConsistencyEngine
from src.consistency.findings import Finding
from src.consistency.checkers.base import CheckContext
from src.consistency.filters import filter_intentional
from src.consistency.dismissed_store import add_dismissal, get_all_dismissals
from src.consistency.checkers import get_default_checkers

router = APIRouter(prefix="/api/consistency", tags=["consistency"])


class CheckRequest(BaseModel):
    ep_num: Optional[int] = None
    branch_id: int = 1


class DismissRequest(BaseModel):
    finding_key: str
    reason: str = ""


@router.post("/{book_id}/check", dependencies=[Depends(require_api_key)])
async def check_consistency(book_id: int, req: CheckRequest):
    engine = ConsistencyEngine(get_default_checkers())
    context = CheckContext(book_id=book_id, branch_id=req.branch_id, ep_num=req.ep_num)
    findings = engine.run(context)
    dismissed = get_all_dismissals(book_id, req.branch_id)
    filtered = filter_intentional(findings, set(dismissed.keys()))
    return {
        "findings": [f.dict() for f in filtered],
        "total": len(filtered),
        "summary": {
            "high": sum(1 for f in filtered if f.severity == "high"),
            "medium": sum(1 for f in filtered if f.severity == "medium"),
            "low": sum(1 for f in filtered if f.severity == "low"),
        },
    }


@router.post("/{book_id}/dismiss", dependencies=[Depends(require_api_key)])
async def dismiss_finding(book_id: int, req: DismissRequest):
    add_dismissal(book_id, req.finding_key, req.reason)
    return {"message": "dismissed", "finding_key": req.finding_key}


@router.get("/{book_id}/dismissed", dependencies=[Depends(require_api_key)])
async def list_dismissed(book_id: int, branch_id: int = 1):
    return {"dismissed": get_all_dismissals(book_id, branch_id)}
