"""伏線回収ステータス自動更新サービス (v5.0 Relational Memory)

執筆完了時に本文を解析し、回収された伏線を自動的に
ForeshadowingStatus.RESOLVED に更新する。
"""
from __future__ import annotations

import logging
from typing import Any

from src.infrastructure.repositories.foreshadowing_repo import DbForeshadowingRepository
from src.models.foreshadowing_status import ForeshadowingStatus
from src.services.foreshadowing_parser import detect_foreshadowing_mentions

logger = logging.getLogger(__name__)


class ForeshadowingService:
    """伏線の回収検出・ステータス更新を一括で行うサービス。

    章の執筆完了後に呼び出され、本文中に回収が検出された伏線を
    自動的にDBで resolved に更新する。
    """

    def __init__(self, repo: DbForeshadowingRepository):
        self.repo = repo

    async def check_and_resolve(
        self,
        book_id: int,
        episode_num: int,
        draft_text: str,
    ) -> list[str]:
        """本文を解析し、回収された伏線を自動更新する。

        Args:
            book_id: 作品ID
            episode_num: 現在の話数
            draft_text: 生成された本文テキスト

        Returns:
            回収された伏線タイトルのリスト
        """
        # 未回収伏線を取得
        unresolved = await self.repo.get_unresolved(book_id)
        if not unresolved:
            return []

        # 本文中の伏線言及を検出
        mentions = detect_foreshadowing_mentions(draft_text, unresolved)

        resolved_titles: list[str] = []

        for mention in mentions:
            # 回収候補と判定された伏線のみ自動回収
            if not mention.is_resolution_candidate:
                continue

            # 回収対象の伏線を検索
            foreshadowing = self._find_by_id(unresolved, mention.foreshadowing_id)
            if foreshadowing is None:
                continue

            # 回収目標話数を超えているか、目標未設定の場合は回収
            target_ep = getattr(foreshadowing, "target_episode", None)
            if target_ep is not None and episode_num < target_ep:
                # まだ目標話数に到達していないので進展扱い
                await self.repo.progress(mention.foreshadowing_id)
                logger.info(
                    f"伏線「{mention.title}」を PROGRESSED に更新 "
                    f"(book_id={book_id}, ep={episode_num}, target={target_ep})"
                )
                continue

            # 回収処理
            success = await self.repo.resolve(mention.foreshadowing_id, episode_num)
            if success:
                resolved_titles.append(mention.title)
                logger.info(
                    f"伏線「{mention.title}」を RESOLVED に更新 "
                    f"(book_id={book_id}, ep={episode_num})"
                )

        return resolved_titles

    async def get_writing_context(self, book_id: int) -> list[dict[str, Any]]:
        """未回収伏線をプロンプト注入用の辞書リストとして取得する。

        Returns:
            [{"id": int, "title": str, "description": str, "planted_episode": int, ...}, ...]
        """
        unresolved = await self.repo.get_unresolved(book_id)
        return [
            {
                "id": f.id,
                "title": f.title,
                "description": f.description,
                "planted_episode": f.planted_episode,
                "target_episode": f.target_episode,
                "status": f.status,
            }
            for f in unresolved
        ]

    async def get_overdue_warnings(self, book_id: int, current_episode: int) -> list[str]:
        """回収期限を超過した伏線の警告メッセージを返す"""
        overdue = await self.repo.get_overdue(book_id, current_episode)
        return [
            f"⚠ 伏線「{f.title}」が回収期限（第{f.target_episode}話）を"
            f"{current_episode - f.target_episode}話超過しています"
            for f in overdue
        ]

    @staticmethod
    def _find_by_id(foreshadowings: list, foreshadowing_id: int) -> Any:
        """IDで伏線を検索"""
        for f in foreshadowings:
            f_id = f.get("id") if isinstance(f, dict) else getattr(f, "id", None)
            if f_id == foreshadowing_id:
                return f
        return None
