"""
RAG Prefetch Service - プロット確定時にRAG検索を先行実行し、
結果をメモリにキャッシュするサービス。

v4.0: 執筆時のRAG検索待ち時間をゼロにする先行キャッシュ基盤
"""
from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class RagPrefetchService:
    """プロット確定時にRAG検索結果を先行キャッシュする。
    
    プロットが確定した時点で、執筆に必要な以下の3種類のRAG検索を
    バックグラウンドで並列実行し、結果をメモリにキャッシュする:
    1. スタイルサンプル検索（文体RAG）
    2. 過去ログからの関連コンテキスト検索
    3. プロジェクトインテリジェンス
    """

    def __init__(self, max_cache_size: int = 50):
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_cache_size = max_cache_size
        self._pending_tasks: Dict[str, asyncio.Task] = {}

    def cache_key(self, book_id: int, ep_num: int) -> str:
        return f"{book_id}_{ep_num}"

    async def prefetch_for_episode(
        self,
        engine: Any,
        book_id: int,
        branch_id: int,
        ep_num: int,
        plot_blueprint: str
    ) -> None:
        """プロット確定直後に呼び出す。RAG検索をバックグラウンドで開始する。
        
        Args:
            engine: UltimateHegemonyEngine インスタンス
            book_id: 作品ID
            branch_id: ブランチID
            ep_num: エピソード番号
            plot_blueprint: プロットの設計図テキスト（検索クエリとして使用）
        """
        key = self.cache_key(book_id, ep_num)
        if key in self._cache or key in self._pending_tasks:
            return

        from src.core.async_utils import fire_and_forget
        task = fire_and_forget(
            self._do_prefetch(engine, book_id, branch_id, ep_num, plot_blueprint),
            name=f"prefetch_ep_{ep_num}"
        )
        self._pending_tasks[key] = task

    async def _do_prefetch(self, engine: Any, book_id: int, branch_id: int,
                           ep_num: int, blueprint: str) -> None:
        """バックグラウンドで3種類のRAG検索を並列実行する"""
        key = self.cache_key(book_id, ep_num)
        try:
            tasks = []

            # 1. スタイルRAG検索
            if hasattr(engine, 'style_rag') and engine.style_rag:
                tasks.append(
                    engine.style_rag.find_best_samples(
                        scene_description=blueprint, phase="Prep", top_k=3
                    )
                )
            else:
                tasks.append(asyncio.coroutine(lambda: [])())

            # 2. 過去ログRAG検索
            if hasattr(engine, 'repo') and hasattr(engine.repo, 'get_relevant_past_logs'):
                tasks.append(
                    engine.repo.get_relevant_past_logs(
                        branch_id, ep_num, query_text=blueprint
                    )
                )
            else:
                tasks.append(asyncio.coroutine(lambda: "")())

            # 3. プロジェクトインテリジェンス
            if hasattr(engine, 'get_project_intelligence'):
                tasks.append(
                    engine.get_project_intelligence(book_id, context=blueprint)
                )
            else:
                tasks.append(asyncio.coroutine(lambda: {})())

            from src.core.async_utils import run_parallel
            results = await run_parallel(tasks, return_exceptions=True)

            style_samples = results[0] if not isinstance(results[0], Exception) else []
            rag_ctx = results[1] if not isinstance(results[1], Exception) else ""
            intel = results[2] if not isinstance(results[2], Exception) else {}

            self._cache[key] = {
                "style_samples": style_samples,
                "rag_context": rag_ctx,
                "intelligence": intel,
                "prefetched": True
            }

            # LRU: 古いキャッシュを破棄
            while len(self._cache) > self._max_cache_size:
                self._cache.popitem(last=False)

            logger.info(f"[RAG PREFETCH] Ep.{ep_num} prefetched successfully")
        except Exception as e:
            logger.warning(f"[RAG PREFETCH] Ep.{ep_num} failed: {e}")
        finally:
            self._pending_tasks.pop(key, None)

    async def get_cached(self, book_id: int, ep_num: int) -> Optional[Dict[str, Any]]:
        """キャッシュされたRAG結果を取得。未完了のタスクがあれば待機する。"""
        key = self.cache_key(book_id, ep_num)

        # 進行中のタスクがあれば待機
        if key in self._pending_tasks:
            try:
                await self._pending_tasks[key]
            except Exception:
                pass

        result = self._cache.get(key)
        if result:
            logger.info(f"[RAG CACHE HIT] Ep.{ep_num}")
        return result

    def invalidate(self, book_id: int, ep_num: int) -> None:
        """指定エピソードのキャッシュを無効化する"""
        key = self.cache_key(book_id, ep_num)
        self._cache.pop(key, None)
        # 進行中のタスクもキャンセル
        task = self._pending_tasks.pop(key, None)
        if task and not task.done():
            task.cancel()

    def get_stats(self) -> Dict[str, Any]:
        """キャッシュの統計情報を返す"""
        return {
            "cached_episodes": len(self._cache),
            "pending_tasks": len(self._pending_tasks),
            "max_size": self._max_cache_size,
            "keys": list(self._cache.keys())
        }
