"""
src/services/episode_context.py — エピソードコンテキスト生成サービス

3層ローリング記憶 (Layer 1: バイブル, Layer 2: 100字要約, Layer 3: 直前生文) を構築する。
同期呼び出し（メモリ履歴）と非同期呼び出し（DBセッション連携）の両方に対応。
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.models import Character as CharacterModel
from src.backend.database.models_foreshadowing import ForeshadowingModel

logger = logging.getLogger(__name__)


class EpisodeContextBuilder:
    """3層ローリング記憶ビルダー

    Layer 1（バイブル）: キャラクター・世界観設定（約1,000トークン）
    Layer 2（全話要約）: 過去全話の100文字事実要約＋未回収伏線一覧（累積しても数千トークン）
    Layer 3（直前文脈）: 直前1エピソードの生テキスト
    上記を合体させたプロンプトコンテキストを構築する。
    """

    def __init__(self, db: AsyncSession | None = None):
        """初期化"""
        self.db = db
        self._episode_history: list[dict[str, Any]] = []

    def build_context(
        self,
        book_id: int,
        ep_num: int,
        target_word_count: int = 3000,
        previous_episode: dict[str, Any] | None = None,
        previous_episode_text: str | None = None,
    ) -> Any:
        """コンテキストをビルド（同期・非同期両対応）"""
        if self.db is None:
            return self._sync_build_context(
                book_id=book_id,
                ep_num=ep_num,
                target_word_count=target_word_count,
                previous_episode=previous_episode,
            )
        return self._async_build_context(
            book_id=book_id,
            ep_num=ep_num,
            target_word_count=target_word_count,
            previous_episode_text=previous_episode_text,
        )

    def _sync_build_context(
        self,
        book_id: int,
        ep_num: int,
        target_word_count: int = 3000,
        previous_episode: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        is_first = ep_num == 1
        is_last = False

        context: dict[str, Any] = {
            "book_id": book_id,
            "ep_num": ep_num,
            "is_first": is_first,
            "is_last": is_last,
            "target_word_count": target_word_count,
        }

        if previous_episode is not None:
            prev = dict(previous_episode)
            if "title" not in prev:
                prev["title"] = f"第{ep_num - 1}話"
            if "key_events" not in prev:
                prev["key_events"] = []
            context["previous_episode"] = prev
        elif not is_first:
            last_summary = self._get_last_episode_summary()
            context["previous_episode"] = {
                "title": last_summary.get("title", ""),
                "ending": last_summary.get("ending", ""),
                "summary": last_summary.get("summary", ""),
                "key_events": last_summary.get("key_events", []),
            }

        self._add_to_history(ep_num, context)
        return context

    async def _async_build_context(
        self,
        book_id: int,
        ep_num: int,
        target_word_count: int = 3000,
        previous_episode_text: str | None = None,
    ) -> dict[str, Any]:
        """3層コンテキストをビルド"""
        is_first = ep_num == 1
        is_last = False

        layer1_bible = await self._build_layer1_bible(book_id)
        layer2_summary = await self._build_layer2_summary(book_id, ep_num)
        layer3_raw = previous_episode_text or ""

        context = {
            "book_id": book_id,
            "ep_num": ep_num,
            "is_first": is_first,
            "is_last": is_last,
            "target_word_count": target_word_count,
            "layer1_bible": layer1_bible,
            "layer2_summary": layer2_summary,
            "layer3_raw": layer3_raw,
            "previous_episode": {
                "summary": layer2_summary.get("last_episode_summary", "") if layer2_summary else "",
                "ending": layer3_raw[-500:] if layer3_raw else "",
            } if not is_first else {},
        }
        self._add_to_history(ep_num, context)
        return context

    def _add_to_history(self, ep_num: int, context: dict[str, Any]):
        """履歴に追加"""
        self._episode_history.append({"ep_num": ep_num, "context": context})
        if len(self._episode_history) > 10:
            self._episode_history = self._episode_history[-10:]

    def _get_last_episode_summary(self) -> dict[str, str]:
        """最後のエピソードの概要を取得"""
        if not self._episode_history:
            return {"title": "", "ending": "", "summary": ""}
        last = self._episode_history[-1]
        prev = last["context"].get("previous_episode", {})
        return {
            "title": prev.get("title", ""),
            "ending": prev.get("ending", ""),
            "summary": prev.get("summary", ""),
        }

    def get_history(self) -> list[dict[str, Any]]:
        """履歴を取得"""
        return self._episode_history.copy()

    def clear_history(self):
        """履歴をクリア"""
        self._episode_history = []

    def set_final_episode(self, ep_num: int):
        """最終話フラグを設定"""
        for item in self._episode_history:
            if item["ep_num"] == ep_num:
                item["context"]["is_last"] = True

    async def _safe_execute(self, query: Any) -> list[Any]:
        """安全にクエリを実行してエンティティリストを返す（AsyncSession, Sync, Mock両対応）"""
        import inspect
        if self.db is None or not hasattr(self.db, "execute"):
            return []
        try:
            res = self.db.execute(query)
            if inspect.isawaitable(res):
                res = await res
            if hasattr(res, "scalars"):
                scalars_res = res.scalars()
                if hasattr(scalars_res, "all"):
                    return list(scalars_res.all())
            return []
        except Exception:
            return []

    async def _build_layer1_bible(self, book_id: int) -> dict[str, Any]:
        """Layer 1: バイブル（キャラクター・世界観設定）を構築"""
        character_list = await self._safe_execute(
            select(CharacterModel).where(CharacterModel.book_id == book_id)
        )

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
                    "id": getattr(char, "id", None),
                    "name": getattr(char, "name", "不明"),
                    "role": getattr(char, "role", ""),
                    "personality": getattr(char, "personality", ""),
                    "ability": getattr(char, "ability", ""),
                }
                for char in character_list
            ],
            "text": bible_text,
            "token_estimate": len(bible_text) // 2,
        }

    async def _build_layer2_summary(self, book_id: int, current_ep: int) -> dict[str, Any]:
        """Layer 2: 全話要約＋未回収伏線一覧を構築"""
        from src.backend.database.models import Chapter as ChapterModel

        chapter_list = await self._safe_execute(
            select(ChapterModel)
            .where(ChapterModel.book_id == book_id)
            .where(ChapterModel.ep_num < current_ep)
            .order_by(ChapterModel.ep_num)
        )

        episode_summaries = []
        for ch in chapter_list:
            if getattr(ch, "content", None):
                summary = ch.content[:100].replace("\n", " ") + "..."
            else:
                summary = "(本文未登録)"
            episode_summaries.append(f"第{getattr(ch, 'ep_num', '?')}話: {summary}")

        foreshadowing_list = await self._safe_execute(
            select(ForeshadowingModel)
            .where(ForeshadowingModel.book_id == book_id)
            .where(ForeshadowingModel.status.in_(["planted", "progressed"]))
            .order_by(ForeshadowingModel.planted_episode)
        )

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
