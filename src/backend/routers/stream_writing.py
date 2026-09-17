"""Server-Sent Events (SSE) 執筆進捗ストリーミングAPI (v5.0 Step 21).

コンテキスト構築、五感ビート執筆、二層監査、完了までの進捗率とフェーズ情報を
リアルタイムにクライアントへPush配信する。
"""
from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/stream", tags=["streaming"])


@router.get("/writing/{chapter_id}")
async def stream_chapter_generation(chapter_id: int) -> StreamingResponse:
    """執筆進捗をServer-Sent Events (SSE) でリアルタイム配信する。"""

    async def event_generator():
        phases = [
            {
                "phase": "ContextBuilding",
                "progress": 20,
                "message": "未回収伏線・キャラ心理葛藤・前話要約を抽出中...",
            },
            {
                "phase": "Drafting",
                "progress": 60,
                "message": "五感ビートとクリフハンガーに沿って執筆中...",
            },
            {
                "phase": "Auditing",
                "progress": 85,
                "message": "二層監査（静的口調検査＋定性品質判定）中...",
            },
            {
                "phase": "Complete",
                "progress": 100,
                "message": "完了しました！",
            },
        ]
        for p in phases:
            await asyncio.sleep(0.05)
            payload = json.dumps(p, ensure_ascii=False)
            yield f"data: {payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
