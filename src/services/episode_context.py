"""
src/services/episode_context.py — エピソードコンテキスト生成サービス
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EpisodeContextBuilder:
    """エピソードコンテキスト生成サービス
    
    前話の情報などを含めた執筆コンテキストを生成する。
    """

    def __init__(self):
        """初期化"""
        self._episode_history: List[Dict[str, Any]] = []

    def build_context(
        self,
        book_id: int,
        ep_num: int,
        target_word_count: int = 3000,
        previous_episode: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """コンテキストをビルド
        
        Args:
            book_id: 作品ID
            ep_num: エピソード番号
            target_word_count: 目標文字数
            previous_episode: 前話の情報（任意）
            
        Returns:
            Dict[str, Any]: コンテキスト辞書
        """
        is_first = ep_num == 1
        is_last = False  # 最終話は別途判定
        
        context = {
            "book_id": book_id,
            "ep_num": ep_num,
            "is_first": is_first,
            "is_last": is_last,
            "target_word_count": target_word_count
        }
        
        # 前話の情報を追加
        if previous_episode:
            context["previous_episode"] = {
                "title": previous_episode.get("title", f"第{ep_num-1}話"),
                "ending": previous_episode.get("ending", ""),
                "summary": previous_episode.get("summary", ""),
                "key_events": previous_episode.get("key_events", [])
            }
        elif not is_first:
            # 前話の情報がないが最初でもない場合
            context["previous_episode"] = self._get_last_episode_summary()
        
        # ヒストリーに追加
        self._add_to_history(ep_num, context)
        
        return context

    def _add_to_history(self, ep_num: int, context: Dict[str, Any]):
        """履歴に追加
        
        Args:
            ep_num: エピソード番号
            context: コンテキスト
        """
        self._episode_history.append({
            "ep_num": ep_num,
            "context": context
        })
        
        # 最近の10話分のみ保持
        if len(self._episode_history) > 10:
            self._episode_history = self._episode_history[-10:]

    def _get_last_episode_summary(self) -> Dict[str, str]:
        """最後のエピソードの概要を取得
        
        Returns:
            Dict[str, str]: 最後のエピソードの概要
        """
        if not self._episode_history:
            return {"title": "", "ending": "", "summary": ""}
        
        last = self._episode_history[-1]
        return {
            "title": last["context"].get("previous_episode", {}).get("title", ""),
            "ending": last["context"].get("previous_episode", {}).get("ending", ""),
            "summary": last["context"].get("previous_episode", {}).get("summary", "")
        }

    def get_history(self) -> List[Dict[str, Any]]:
        """履歴を取得
        
        Returns:
            List[Dict[str, Any]]: エピソード履歴
        """
        return self._episode_history.copy()

    def clear_history(self):
        """履歴をクリア"""
        self._episode_history = []

    def set_final_episode(self, ep_num: int):
        """最終話フラグを設定
        
        Args:
            ep_num: 最終話の番号
        """
        for item in self._episode_history:
            if item["ep_num"] == ep_num:
                item["context"]["is_last"] = True