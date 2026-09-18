"""
src/services/episode_context.py — エピソードコンテキスト生成サービス

3層ローリング記憶 (Layer 1: バイブル, Layer 2: 100字要約, Layer 3: 直前生文) を構築する。
"""

import logging
from typing import Any

from src.backend import database
from src.backend.database.models import Book as BookModel, Character as CharacterModel
from src.backend.database.models_foreshadowing import ForeshadowingModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EpisodeContextBuilder:
    """3層ローリング記憶ビルダー

    Layer 1（バイブル）: キャラクター・世界観設定（約1,000トークン）
    Layer 2（全話要約）: 過去全話の100文字事実要約＋未回収伏線一覧（累積しても数千トークン）
    Layer 3（直前文脈）: 直前1エピソードの生テキスト
    上記を合体させたプロンプトコンテキストを構築する。
    """

    def __init__(self, db: AsyncSession):
        """初期化"""
        self.db = db

    async def build_context(
        self,
        book_id: int,
        ep_num: int,
        target_word_count: int = 3000,
        previous_episode_text: str | None = None,
    ) -> dict[str, Any]:
        """3層コンテキストをビルド

        Args:
            book_id: 作品ID
            ep_num: エピソード番号
            target_word_count: 目標文字数
            previous_episode_text: 直前エピソードの生テキスト（Layer 3用）

        Returns:
            Dict[str, Any]: 3層コンテキストを含む辞書
        """
        is_first = ep_num == 1
        is_last = False  # 最終話は別途判定

        # Layer 1: バイブル（キャラクター・世界観設定）
        layer1_bible = await self._build_layer1_bible(book_id)

        # Layer 2: 全話要約＋未回収伏線
        layer2_summary = await self._build_layer2_summary(book_id, ep_num)

        # Layer 3: 直前生文
        layer3_raw = previous_episode_text or ""

        context = {
            "book_id": book_id,
            "ep_num": ep_num,
            "is_first": is_first,
            "is_last": is_last,
            "target_word_count": target_word_count,
            # 3層コンテキスト
            "layer1_bible": layer1_bible,
            "layer2_summary": layer2_summary,
            "layer3_raw": layer3_raw,
            # 後方互換性のため従来形式も保持
            "previous_episode": {
                "summary": layer2_summary.get("last_episode_summary", "") if layer2_summary else "",
                "ending": layer3_raw[-500:] if layer3_raw else "",
            } if not is_first else {},
        }

        return context

    async def _build_layer1_bible(self, book_id: int) -> dict[str, Any]:
        """Layer 1: バイブル（キャラクター・世界観設定）を構築"""
        # キャラクター一覧取得
        characters = await self.db.execute(
            select(CharacterModel).where(CharacterModel.book_id == book_id)
        )
        character_list = characters.scalars().all()

        # バイブル情報を構築（booksテーブルやbibleテーブルから取得想定）
        # 簡易実装：キャラ情報のみ
        character_bible = []
        for char in character_list:
            character_bible.append(
                f"【{char.name}】\n"
                f"役割: {char.role or '不明'}\n"
                f"性格: {char.personality or '未設定'}\n"
                f"能力: {char.ability or '未設定'}\n"
            )

        bible_text = "\n".join(character_bible) if character_bible else "キャラクター設定なし"

        return {
            "characters": [
                {
                    "id": char.id,
                    "name": char.name,
                    "role": char.role,
                    "personality": char.personality,
                    "ability": char.ability,
                }
                for char in character_list
            ],
            "text": bible_text,
            "token_estimate": len(bible_text) // 2,  # 概算トークン数
        }

    async def _build_layer2_summary(self, book_id: int, current_ep: int) -> dict[str, Any]:
        """Layer 2: 全話要約＋未回収伏線一覧を構築"""
        # 過去エピソードの要約を取得（chapterテーブルから想定）
        from src.backend.database.models import Chapter as ChapterModel
        
        chapters = await self.db.execute(
            select(ChapterModel)
            .where(ChapterModel.book_id == book_id)
            .where(ChapterModel.ep_num < current_ep)
            .order_by(ChapterModel.ep_num)
        )
        chapter_list = chapters.scalars().all()

        # 各話の100文字要約を生成（contentから抽出）
        episode_summaries = []
        for ch in chapter_list:
            if ch.content:
                summary = ch.content[:100].replace("\n", " ") + "..."
            else:
                summary = "(本文未登録)"
            episode_summaries.append(f"第{ch.ep_num}話: {summary}")

        # 未回収伏線を取得
        foreshadowings = await self.db.execute(
            select(ForeshadowingModel)
            .where(ForeshadowingModel.book_id == book_id)
            .where(ForeshadowingModel.status.in_(["planted", "progressed"]))
            .order_by(ForeshadowingModel.planted_episode)
        )
        foreshadowing_list = foreshadowings.scalars().all()

        unresolved_foreshadowings = [
            f"  - 「{f.title}」（第{f.planted_episode}話設置"
            f"{f', 第{f.target_episode}話回収目標' if f.target_episode else ''}）"
            for f in foreshadowing_list
        ]

        summary_text = "【過去エピソード要約】\n" + "\n".join(episode_summaries) if episode_summaries else "【過去エピソード要約】\n(過去エピソードなし)"
        
        if unresolved_foreshadowings:
            summary_text += "\n\n【未回収伏線一覧】\n" + "\n".join(unresolved_foreshadowings)
        else:
            summary_text += "\n\n【未回収伏線一覧】\n(なし)"

        last_episode_summary = ""
        if chapter_list:
            last_ch = chapter_list[-1]
            last_episode_summary = last_ch.content[:200] if last_ch.content else ""

        return {
            "episode_summaries": episode_summaries,
            "unresolved_foreshadowings": [
                {
                    "id": f.id,
                    "title": f.title,
                    "planted_episode": f.planted_episode,
                    "target_episode": f.target_episode,
                    "status": f.status,
                }
                for f in foreshadowing_list
            ],
            "text": summary_text,
            "last_episode_summary": last_episode_summary,
            "token_estimate": len(summary_text) // 2,
        }

    def get_history(self) -> list[dict[str, Any]]:
        """履歴を取得（互換性のため空実装）"""
        return []

    def clear_history(self):
        """履歴をクリア（互換性のため空実装）"""
        pass

    def set_final_episode(self, ep_num: int):
        """最終話フラグを設定（互換性のため空実装）"""
        pass
