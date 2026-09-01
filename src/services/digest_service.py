"""ダイジェスト生成サービスおよび章処理ユーティリティ。"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, Optional

from src.models.easy_mode_schemas import (
    DigestRequest,
    DigestResponse,
    DigestStatus,
)
from src.services.gacha_service import _GACHA_CACHE
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# ダイジェスト・作品のメモリ保存ストア（DB非依存時用）
_BOOK_STORE: Dict[str, Dict[str, Any]] = {}

CHAPTER_MAX_LENGTH = 1500


def process_chapter(chapter: str) -> str:
    """章本文から主要テキストを抽出する。"""
    return (
        (chapter[:CHAPTER_MAX_LENGTH].rstrip() + "...")
        if len(chapter) > CHAPTER_MAX_LENGTH
        else chapter
    )


async def generate_suggestions(chapter: str) -> list[str]:
    """章の文脈から意味的な提案を生成する。"""
    if not chapter:
        return ["続行: (空章のため先頭から再開)", "調査が必要な未確認な要素を指摘"]
    return [
        f"続行: {chapter[:100]}...",
        "調査が必要な未確認な要素を指摘",
    ]


class DigestService:
    """ファスト・ダイジェスト生成サービス"""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()

    async def create_digest(self, request: DigestRequest) -> DigestResponse:
        return await self.generate_digest(request)

    async def generate_digest(self, request: DigestRequest) -> DigestResponse:
        """選択された企画から高速でプロット・第1話・クライマックスプレビューを生成する"""
        gacha_data = _GACHA_CACHE.get(request.request_id)
        selected_plan = None

        if gacha_data:
            plans = gacha_data.get("response", {}).get("plans", [])
            for p in plans:
                if p.get("plan_id") == request.selected_plan_id:
                    selected_plan = p
                    break

        if not selected_plan:
            selected_plan = {
                "title": "選択された物語",
                "logline": "運命に立ち向かう主人公の冒険譚",
                "protagonist_summary": "強い意志を持った主人公",
                "charm_point": "圧倒的カタルシス",
            }

        title = selected_plan.get("title", "無題の物語")
        book_id = f"book_{uuid.uuid4().hex[:8]}"

        try:
            synopsis_prompt = f"""
タイトル: {title}
キャッチコピー: {selected_plan.get("logline")}
主人公: {selected_plan.get("protagonist_summary")}

上記作品の全体あらすじ（300文字程度）と全10話の章構成プロットを作成してください。
"""
            synopsis_text = await self.llm_service.generate_text(
                purpose="planning",
                prompt=synopsis_prompt,
            )

            ep1_prompt = f"""
タイトル: {title}
全体概要: {synopsis_text[:200]}

小説の「第1話」本文（1000文字〜1500文字程度）を執筆してください。
"""
            climax_prompt = f"""
タイトル: {title}
全体概要: {synopsis_text[:200]}

物語のクライマックス（見せ場）のプレビュー描写（800文字程度）を執筆してください。
"""

            ep1_task = self.llm_service.generate_text(purpose="writing", prompt=ep1_prompt)
            climax_task = self.llm_service.generate_text(purpose="climax", prompt=climax_prompt)

            ep1_text, climax_text = await asyncio.gather(ep1_task, climax_task)

            response = DigestResponse(
                book_id=book_id,
                title=title,
                synopsis=synopsis_text,
                episode_1_text=ep1_text,
                climax_preview_text=climax_text,
                status=DigestStatus.COMPLETED,
            )

            _BOOK_STORE[book_id] = {
                "book_id": book_id,
                "title": title,
                "selected_plan": selected_plan,
                "digest": response.model_dump(),
                "mode": "easy",
            }

            return response

        except Exception as e:
            logger.error(f"Digest generation failed for book_id {book_id}: {e}")
            fallback_response = DigestResponse(
                book_id=book_id,
                title=title,
                synopsis="生成中にエラーが発生しましたが、基本枠組みは作成されました。",
                episode_1_text="第1話の生成に失敗しました。再試行してください。",
                climax_preview_text="クライマックスプレビューの生成に失敗しました。",
                status=DigestStatus.FAILED,
            )
            _BOOK_STORE[book_id] = {
                "book_id": book_id,
                "title": title,
                "selected_plan": selected_plan,
                "digest": fallback_response.model_dump(),
                "mode": "easy",
            }
            return fallback_response


__all__ = ["process_chapter", "generate_suggestions", "DigestService"]
