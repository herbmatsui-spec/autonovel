"""GraphRAG バックグラウンド更新パイプラインサービス."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.backend.config import settings
from src.backend.logging_config import get_logger
from src.infrastructure.database.models.chunk import ChapterChunk
from src.services.age_client import age_client
from src.services.embedding_service import embedding_service
from src.services.extraction_service import extraction_service
from src.services.text_chunker import split_into_paragraphs

logger = get_logger("graph_pipeline")


class GraphPipelineService:
    """章生成後のベクトル保存およびナレッジグラフ更新を実行するパイプライン."""

    def process_chapter_knowledge(
        self,
        session: Session,
        chapter_id: int,
        chapter_text: str,
    ) -> dict[str, Any]:
        """指定された章のベクトル化とグラフ更新を一括実行する."""
        if not chapter_text or not chapter_text.strip():
            return {"chunks_created": 0, "entities_created": 0, "relationships_created": 0}

        logger.info("Processing GraphRAG knowledge for chapter_id=%s", chapter_id)

        # 1. チャンク化とベクトル保存
        chunks_count = self.save_chapter_chunks(session, chapter_id, chapter_text)

        # 2. ナレッジグラフの抽出と更新
        graph_stats = self.update_knowledge_graph(session, chapter_id, chapter_text)

        return {
            "chunks_created": chunks_count,
            "entities_created": graph_stats.get("entities", 0),
            "relationships_created": graph_stats.get("relationships", 0),
        }

    def save_chapter_chunks(
        self,
        session: Session,
        chapter_id: int,
        chapter_text: str,
    ) -> int:
        """本文をチャンク分割して埋め込みベクトルとともに保存する."""
        paragraphs = split_into_paragraphs(chapter_text)
        if not paragraphs:
            return 0

        created_count = 0
        for idx, para in enumerate(paragraphs):
            try:
                emb = embedding_service.get_embedding(para)
                chunk = ChapterChunk(
                    chapter_id=chapter_id,
                    chunk_index=idx,
                    content=para,
                    embedding=emb,
                    chunk_metadata={"length": len(para)},
                )
                session.add(chunk)
                created_count += 1
            except Exception as e:
                logger.warning("Failed to save chunk %d for chapter_id=%s: %s", idx, chapter_id, e)

        try:
            session.commit()
            logger.info("Saved %d chunks for chapter_id=%s", created_count, chapter_id)
        except Exception as e:
            session.rollback()
            logger.error("Failed to commit chunks for chapter_id=%s: %s", chapter_id, e)
            return 0

        return created_count

    def update_knowledge_graph(
        self,
        session: Session,
        chapter_id: int,
        chapter_text: str,
    ) -> dict[str, int]:
        """本文からナレッジグラフを抽出して Apache AGE に更新・保存する."""
        if not settings.ENABLE_GRAPHRAG:
            return {"entities": 0, "relationships": 0}

        # 1. LLM 抽出
        raw_extraction = extraction_service.extract_graph_from_text(chapter_text)

        # 既存エンティティ名との名寄せ（Entity Resolution）
        existing_nodes = age_client.get_all_nodes(session) if settings.DATABASE_URL.startswith("postgresql") else []
        existing_names = [n.get("name", "") for n in existing_nodes if isinstance(n, dict) and n.get("name")]
        extraction = extraction_service.resolve_entities(raw_extraction, existing_names)

        entities_count = 0
        relationships_count = 0

        # 2. ノードの UPSERT
        for entity in extraction.entities:
            props = dict(entity.properties)
            if entity.description:
                props["description"] = entity.description
            props["last_chapter_id"] = chapter_id

            success = age_client.upsert_node(
                session=session,
                label=entity.type,
                name=entity.name,
                properties=props,
            )
            if success:
                entities_count += 1

        # 3. エッジの UPSERT
        for rel in extraction.relationships:
            props = {"detail": rel.detail, "chapter_id": chapter_id}
            # ラベルの特定（見つからない場合は Generic な Entity とする）
            source_entity = next((e for e in extraction.entities if e.name == rel.source), None)
            target_entity = next((e for e in extraction.entities if e.name == rel.target), None)

            source_label = source_entity.type if source_entity else "Entity"
            target_label = target_entity.type if target_entity else "Entity"

            success = age_client.upsert_edge(
                session=session,
                source_label=source_label,
                source_name=rel.source,
                target_label=target_label,
                target_name=rel.target,
                relation_type=rel.type,
                properties=props,
            )
            if success:
                relationships_count += 1

        try:
            session.commit()
            logger.info(
                "Graph updated for chapter_id=%s: entities=%d, relationships=%d",
                chapter_id,
                entities_count,
                relationships_count,
            )
        except Exception as e:
            session.rollback()
            logger.error("Failed to commit graph update for chapter_id=%s: %s", chapter_id, e)

        return {"entities": entities_count, "relationships": relationships_count}


graph_pipeline_service = GraphPipelineService()

__all__ = ["GraphPipelineService", "graph_pipeline_service"]
