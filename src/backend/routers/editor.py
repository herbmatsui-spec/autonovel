"""上級者エディタ用 API ルーターモジュール.

インラインAI（五感拡張・Show Don't Tell・リライト）、
GraphRAG 専属AI編集者（Ask Bible・矛盾診断）、
Next Beats 3バリエーション分岐生成エンドポイントを提供。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.backend.database import get_db
from src.models.editor import (
    AskBibleRequest,
    AskBibleResponse,
    AssistRequest,
    AssistResponse,
    ConsistencyAuditRequest,
    ConsistencyAuditResponse,
    NextBeatsRequest,
    NextBeatsResponse,
)
from src.services.editor_assist_service import EditorAssistService
from src.services.editorial_assistant_service import EditorialAssistantService
from src.services.next_beats_service import NextBeatsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/editor", tags=["editor"])

# サービスインスタンスの初期化
assist_service = EditorAssistService()
editorial_service = EditorialAssistantService()
next_beats_service = NextBeatsService()


@router.post("/assist", response_model=AssistResponse)
async def assist_content(req: AssistRequest) -> AssistResponse:
    """選択テキストに対するインラインAI推敲・五感描写拡張・Show Don't Tell・トーン変換"""
    try:
        return await assist_service.assist(req)
    except Exception as e:
        logger.error(f"Error in assist_content endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask-bible", response_model=AskBibleResponse)
async def ask_bible(
    req: AskBibleRequest,
    session: Session = Depends(get_db),
) -> AskBibleResponse:
    """GraphRAG（ベクトル検索 + ナレッジグラフ）を活用した世界観設定資料・過去章 Q&A"""
    try:
        return await editorial_service.ask_bible(session, req)
    except Exception as e:
        logger.error(f"Error in ask_bible endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audit-consistency", response_model=ConsistencyAuditResponse)
async def audit_consistency(
    req: ConsistencyAuditRequest,
    session: Session = Depends(get_db),
) -> ConsistencyAuditResponse:
    """執筆中の本文と GraphRAG 設定情報とのリアルタイム矛盾診断"""
    try:
        return await editorial_service.audit_consistency(session, req)
    except Exception as e:
        logger.error(f"Error in audit_consistency endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/next-beats", response_model=NextBeatsResponse)
async def generate_next_beats(req: NextBeatsRequest) -> NextBeatsResponse:
    """直前までの本文から、王道・サスペンス・心情の3つの展開バリエーションを並列生成"""
    try:
        return await next_beats_service.generate_three_beats(req)
    except Exception as e:
        logger.error(f"Error in generate_next_beats endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
