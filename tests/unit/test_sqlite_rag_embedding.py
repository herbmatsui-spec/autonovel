"""Tests for SQLite RAG embedding persistence and fast batch vector search (Phase 3 / Steps 25-36)."""
import time
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import src.backend.database.models
from src.infrastructure.database.models.base_orm import Base
from src.infrastructure.database.models.chunk import ChapterChunk
from src.services.rag_service import GraphRAGService
from src.services.chunk_ingestion import backfill_missing_embeddings


def _make_vector(seed: float, dim: int = 64) -> list[float]:
    """テスト用の正規化ベクトル生成ヘルパー"""
    import math
    vec = [(seed + i * 0.1) for i in range(dim)]
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec]


class DummyEmbeddingService:
    def __init__(self, target_vec: list[float], other_vec: list[float]):
        self.target_vec = target_vec
        self.other_vec = other_vec
        self.call_count = 0

    def get_embedding(self, text_str: str) -> list[float]:
        self.call_count += 1
        if "聖剣" in text_str or "エクスカリバー" in text_str:
            return list(self.target_vec)
        return list(self.other_vec)

    def embed_texts(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        return [self.get_embedding(t) for t in texts]


def test_sqlite_rag_batch_vector_search_and_no_truncation(monkeypatch):
    """Steps 28-36: SQLite RAG uses pre-stored embeddings, scans beyond limit*3, and returns correct rank."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    target_vec = _make_vector(1.0)
    other_vec = _make_vector(-1.0)
    dummy_embedder = DummyEmbeddingService(target_vec, other_vec)

    monkeypatch.setattr("src.services.rag_service.embedding_service", dummy_embedder)
    monkeypatch.setattr("src.services.chunk_ingestion.embedding_service", dummy_embedder)

    with Session(engine) as session:
        session.execute(text("PRAGMA foreign_keys=OFF"))
        # 1. 50個のチャンクを作成
        # 最も古いチャンク（ID 0）をターゲットとする（従来の limit*3=15 だと完全に足切りされていた）
        oldest_target = ChapterChunk(
            id="target-chunk-0",
            chapter_id=1,
            chunk_index=0,
            content="勇者は聖剣エクスカリバーの封印を解いた。",
            embedding=target_vec,
            chunk_metadata={"chapter": 1},
        )
        session.add(oldest_target)

        for i in range(1, 50):
            c = ChapterChunk(
                id=f"filler-chunk-{i}",
                chapter_id=1,
                chunk_index=i,
                content=f"日常の風景とその{i}番目の出来事。",
                embedding=other_vec,
                chunk_metadata={"chapter": 1},
            )
            session.add(c)
        session.commit()

        rag = GraphRAGService()

        # Step 30 & 36: 検索実行（外部APIの逐次再計算なし、高速）
        start_t = time.perf_counter()
        results = rag.search_vectors(
            session=session,
            query="伝説の聖剣エクスカリバーについて",
            limit=5,
            min_score=0.5,
        )
        elapsed_ms = (time.perf_counter() - start_t) * 1000

        stats = rag.get_last_stats()

        # Step 29 & 35: 50件前の最古チャンクがヒットすること
        assert len(results) > 0
        assert results[0].id == "target-chunk-0"
        assert "聖剣エクスカリバー" in results[0].content
        assert results[0].score > 0.95
        assert results[0].source == "sqlite_vector"

        # Step 30: 事前保存 embedding がキャッシュヒットしたこと
        assert stats["cached_embeddings_hits"] >= 50
        assert stats["chunks_scanned"] == 50
        assert stats["backend"] == "sqlite_vector"

        # クエリEmbeddingの1回のみ取得されたこと（全チャンク50件の逐次Embedding再計算が行われていないこと）
        assert dummy_embedder.call_count == 1

        # Step 36: 高速であること (50ms〜200ms以内)
        assert elapsed_ms < 500


def test_backfill_missing_embeddings(monkeypatch):
    """Step 27, 31: backfill_missing_embeddings successfully generates and stores embeddings for NULL chunks."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    vec = _make_vector(0.5)
    dummy_embedder = DummyEmbeddingService(vec, vec)
    monkeypatch.setattr("src.services.chunk_ingestion.embedding_service", dummy_embedder)

    with Session(engine) as session:
        session.execute(text("PRAGMA foreign_keys=OFF"))
        c1 = ChapterChunk(id="c1", chapter_id=1, chunk_index=0, content="テキスト1", embedding=None)
        c2 = ChapterChunk(id="c2", chapter_id=1, chunk_index=1, content="テキスト2", embedding=None)
        session.add_all([c1, c2])
        session.commit()

        updated_count = backfill_missing_embeddings(session)
        assert updated_count == 2

        # Verify persisted
        reloaded = session.query(ChapterChunk).all()
        for c in reloaded:
            assert isinstance(c.embedding, list)
            assert len(c.embedding) == 64
