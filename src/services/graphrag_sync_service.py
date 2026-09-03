"""GraphRAG 同期サービス - SettingDelta を ChromaDB と Knowledge Graph に反映"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class GraphRAGSyncService:
    """設定変更差分を GraphRAG (ChromaDB + Knowledge Graph) に自動マージするサービス"""

    def __init__(self, repo=None, chroma_client=None, kg_client=None):
        self.repo = repo
        self.chroma_client = chroma_client
        self.kg_client = kg_client

    async def merge_setting_delta(self, delta_id: int) -> bool:
        """単一の SettingDelta を GraphRAG にマージ"""
        if self.repo is None:
            return False

        delta = await self.repo.misc.get_setting_delta(delta_id)
        if not delta:
            logger.warning(f"SettingDelta {delta_id} not found")
            return False

        if delta.get("merged_to_graphrag"):
            logger.info(f"Delta {delta_id} already merged, skipping")
            return True

        try:
            # 1. ChromaDB ベクトル更新
            await self._update_chromadb(delta)

            # 2. Knowledge Graph ノード/エッジ属性更新
            await self._update_knowledge_graph(delta)

            # 3. マージ済みフラグ更新
            await self.repo.misc.mark_delta_merged(delta_id)

            logger.info(f"Successfully merged delta {delta_id} to GraphRAG")
            return True
        except Exception as e:
            logger.error(f"Failed to merge delta {delta_id} to GraphRAG: {e}")
            return False

    async def merge_pending_deltas(self, book_id: int, batch_size: int = 50) -> int:
        """未マージの差分をバッチでマージ"""
        if self.repo is None:
            return 0

        deltas = await self.repo.misc.get_setting_deltas(book_id, merged_only=False)
        pending = [d for d in deltas if not d.get("merged_to_graphrag")]

        merged_count = 0
        for delta in pending[:batch_size]:
            if await self.merge_setting_delta(delta["id"]):
                merged_count += 1

        logger.info(f"Batch merged {merged_count}/{len(pending)} deltas for book_id={book_id}")
        return merged_count

    async def _update_chromadb(self, delta: dict[str, Any]) -> None:
        """ChromaDB のベクトルを更新"""
        if self.chroma_client is None:
            logger.debug("ChromaDB client not available, skipping vector update")
            return

        field_path = delta.get("field_path", "")
        new_value = delta.get("new_value")
        book_id = delta.get("book_id")

        try:
            # 既存のベクトルを検索・削除
            collection = self.chroma_client.get_collection(f"bible_settings_{book_id}")
            if collection:
                # 古いベクトルを削除 (field_path で検索)
                collection.delete(where={"field_path": field_path})

                # 新しいベクトルを追加
                if new_value is not None:
                    import hashlib

                    doc_id = hashlib.md5(f"{book_id}_{field_path}".encode()).hexdigest()
                    collection.add(
                        documents=[f"{field_path}: {new_value}"],
                        metadatas=[
                            {
                                "book_id": book_id,
                                "field_path": field_path,
                                "value": new_value,
                                "source": delta.get("source"),
                                "delta_type": delta.get("delta_type"),
                            }
                        ],
                        ids=[doc_id],
                    )
                    logger.debug(f"Updated ChromaDB vector for {field_path}")
        except Exception as e:
            logger.warning(f"ChromaDB update failed for {field_path}: {e}")

    async def _update_knowledge_graph(self, delta: dict[str, Any]) -> None:
        """Knowledge Graph のノード/エッジ属性を更新"""
        if self.kg_client is None:
            logger.debug("Knowledge Graph client not available, skipping KG update")
            return

        field_path = delta.get("field_path", "")
        new_value = delta.get("new_value")
        book_id = delta.get("book_id")

        try:
            # field_path をノードパスとして解釈し、属性を更新
            # 例: "world_rules.magic_system.mana_cost" → WorldRules ノードの magic_system.mana_cost 属性
            parts = field_path.split(".")
            if len(parts) >= 2:
                node_type = parts[0]  # world_rules, characters, etc.
                attr_path = ".".join(parts[1:])

                # Cypher/Gremlin クエリでノード属性更新
                query = """
                MATCH (n {book_id: $book_id, type: $node_type})
                SET n.$attr_path = $new_value
                RETURN n
                """
                await self.kg_client.execute_query(
                    query,
                    {
                        "book_id": book_id,
                        "node_type": node_type,
                        "attr_path": attr_path,
                        "new_value": new_value,
                    },
                )
                logger.debug(f"Updated Knowledge Graph node {node_type}.{attr_path}")
        except Exception as e:
            logger.warning(f"Knowledge Graph update failed for {field_path}: {e}")

    async def reindex_book_settings(self, book_id: int) -> bool:
        """書籍の全設定を再インデックス（初回セットアップや完全リビルド用）"""
        if self.repo is None or self.chroma_client is None:
            return False

        try:
            bible = await self.repo.bible.get_bible(book_id)
            if not bible:
                return False

            # Bible 全体をフラット化してベクトル化
            settings_dict = bible.model_dump() if hasattr(bible, "model_dump") else bible
            flat_settings = self._flatten_dict(settings_dict)

            collection = self.chroma_client.get_or_create_collection(f"bible_settings_{book_id}")
            collection.delete(where={"book_id": book_id})  # 全削除

            import hashlib

            for field_path, value in flat_settings.items():
                if value is not None and str(value).strip():
                    doc_id = hashlib.md5(f"{book_id}_{field_path}".encode()).hexdigest()
                    collection.add(
                        documents=[f"{field_path}: {value}"],
                        metadatas=[
                            {
                                "book_id": book_id,
                                "field_path": field_path,
                                "value": str(value),
                            }
                        ],
                        ids=[doc_id],
                    )

            logger.info(f"Reindexed {len(flat_settings)} settings for book_id={book_id}")
            return True
        except Exception as e:
            logger.error(f"Reindex failed for book_id={book_id}: {e}")
            return False

    def _flatten_dict(self, d: dict, parent_key: str = "", sep: str = ".") -> dict[str, Any]:
        """ネストした辞書をフラット化"""
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(self._flatten_dict(v, new_key, sep=sep))
            elif isinstance(v, list):
                # リストは JSON 文字列として保存
                items[new_key] = json.dumps(v, ensure_ascii=False)
            else:
                items[new_key] = v
        return items
