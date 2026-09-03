"""GraphRAG パフォーマンス回帰テスト.

ベンチマーク閾値を超えた場合に失敗し、速度劣化を検知する。
"""
import time
import pytest

from src.services.age_client import AgeClient
from src.services.vector_store import PgVectorStore, get_default_store
from src.services.graph_pipeline import GraphPipelineService
from src.services.rag_service import GraphRAGService
from src.services.embedding_service import embedding_service

# ベンチマーク閾値（ミリ秒）
THRESHOLDS = {
    "age_upsert_1000_nodes_ms": 5000,
    "age_upsert_10000_edges_ms": 10000,
    "pgvector_ingest_1000_docs_ms": 3000,
    "pgvector_search_1000_docs_ms": 100,
    "rag_hybrid_search_ms": 200,
    "pipeline_single_chapter_ms": 5000,
    "embedding_generation_1000_texts_ms": 5000,
}


def _now_ms():
    return time.perf_counter() * 1000


@pytest.mark.perf
def test_age_upsert_1000_nodes_performance(db_session):
    """1000ノード一括 UPSERT が閾値以内"""
    client = AgeClient(default_graph_name="perf_test_nodes")
    assert client.init_graph(db_session) is True

    nodes = [
        {"label": "Character", "name": f"キャラ{i}", "properties": {"idx": i}}
        for i in range(1000)
    ]

    start = _now_ms()
    count = client.upsert_nodes_batch(db_session, nodes)
    elapsed = _now_ms() - start

    assert count == 1000
    assert elapsed < THRESHOLDS["age_upsert_1000_nodes_ms"], \
        f"UPSERT 1000 nodes took {elapsed:.0f}ms, threshold {THRESHOLDS['age_upsert_1000_nodes_ms']}ms"


@pytest.mark.perf
def test_age_upsert_10000_edges_performance(db_session):
    """10000エッジ一括 UPSERT が閾値以内"""
    client = AgeClient(default_graph_name="perf_test_edges")
    assert client.init_graph(db_session) is True

    # ノード事前作成
    for i in range(200):
        client.upsert_node(db_session, "Character", f"C{i}", {})

    edges = [
        {
            "source_label": "Character",
            "source_name": f"C{i}",
            "target_label": "Character",
            "target_name": f"C{i+1}",
            "relation_type": "KNOWS",
        }
        for i in range(199)
    ]
    # 10000エッジに拡張
    edges = edges * 50 + edges[:50]  # 10000

    start = _now_ms()
    count = client.upsert_edges_batch(db_session, edges)
    elapsed = _now_ms() - start

    assert count == 10000
    assert elapsed < THRESHOLDS["age_upsert_10000_edges_ms"]


@pytest.mark.perf
def test_pgvector_ingest_1000_docs_performance(pgvector_store):
    """1000ドキュメント取り込みが閾値以内"""
    docs = [f"ドキュメント {i} の内容です。" * 10 for i in range(1000)]
    embeddings = [embedding_service.get_embedding(doc) for doc in docs]
    ids = [f"doc{i}" for i in range(1000)]

    import asyncio
    start = _now_ms()
    asyncio.run(pgvector_store.add_documents("perf_ingest", ids, docs, embeddings))
    elapsed = _now_ms() - start

    assert elapsed < THRESHOLDS["pgvector_ingest_1000_docs_ms"], \
        f"Ingest 1000 docs took {elapsed:.0f}ms, threshold {THRESHOLDS['pgvector_ingest_1000_docs_ms']}ms"


@pytest.mark.perf
def test_pgvector_search_1000_docs_performance(pgvector_store):
    """1000ドキュメント検索が閾値以内"""
    import asyncio

    # データ投入
    docs = [f"検索対象ドキュメント {i}" for i in range(1000)]
    embeddings = [embedding_service.get_embedding(doc) for doc in docs]
    ids = [f"search_doc{i}" for i in range(1000)]
    asyncio.run(pgvector_store.add_documents("perf_search", ids, docs, embeddings))

    query_emb = embedding_service.get_embedding("検索クエリ")

    start = _now_ms()
    results = asyncio.run(pgvector_store.search("perf_search", query_emb, top_k=10))
    elapsed = _now_ms() - start

    assert len(results) == 10
    assert elapsed < THRESHOLDS["pgvector_search_1000_docs_ms"], \
        f"Search 1000 docs took {elapsed:.0f}ms, threshold {THRESHOLDS['pgvector_search_1000_docs_ms']}ms"


@pytest.mark.perf
def test_rag_hybrid_search_performance(db_session):
    """ハイブリッド検索が閾値以内"""
    # テストデータ準備
    from src.infrastructure.database.models.chunk import ChapterChunk
    chunks = [
        ChapterChunk(chapter_id=1, chunk_index=i, content=f"チャンク {i} の内容", embedding=[0.1]*1536)
        for i in range(100)
    ]
    db_session.add_all(chunks)
    db_session.commit()

    # グラフデータ
    client = AgeClient(default_graph_name="perf_rag")
    client.init_graph(db_session)
    for i in range(20):
        client.upsert_node(db_session, "Character", f"キャラ{i}", {})
        client.upsert_edge(db_session, "Character", f"キャラ{i}", "Character", f"キャラ{i+1}", "KNOWS", {})
    db_session.commit()

    service = GraphRAGService()

    start = _now_ms()
    results = service.hybrid_search(db_session, "検索クエリ", core_entities=["キャラ5"], top_k=10)
    elapsed = _now_ms() - start

    assert len(results) > 0
    assert elapsed < THRESHOLDS["rag_hybrid_search_ms"], \
        f"Hybrid search took {elapsed:.0f}ms, threshold {THRESHOLDS['rag_hybrid_search_ms']}ms"


@pytest.mark.perf
def test_pipeline_single_chapter_performance(db_session):
    """単章パイプライン処理が閾値以内"""
    from unittest.mock import patch
    from src.models.graph_schemas import GraphExtractionResult, Entity, Relationship

    pipeline = GraphPipelineService()
    text = "テスト本文。" * 100  # 約 500 文字

    mock_extraction = GraphExtractionResult(
        entities=[Entity(name=f"エンティティ{i}", type="Character", description="", properties={}) for i in range(20)],
        relationships=[Relationship(source=f"エンティティ{i}", target=f"エンティティ{i+1}", type="KNOWS", detail="") for i in range(19)],
        plot_summary="テスト要約"
    )

    with patch("src.services.graph_pipeline.extraction_service.extract_graph_from_text", return_value=mock_extraction), \
         patch("src.services.graph_pipeline.extraction_service.resolve_entities", return_value=mock_extraction), \
         patch("src.services.graph_pipeline.settings.ENABLE_GRAPHRAG", True):
        start = _now_ms()
        result = pipeline.process_chapter_knowledge(db_session, 999, text)
        elapsed = _now_ms() - start

    assert result["success"] is True
    assert elapsed < THRESHOLDS["pipeline_single_chapter_ms"], \
        f"Pipeline single chapter took {elapsed:.0f}ms, threshold {THRESHOLDS['pipeline_single_chapter_ms']}ms"


@pytest.mark.perf
def test_embedding_generation_1000_texts_performance():
    """1000テキストの埋め込み生成が閾値以内"""
    texts = [f"テキスト {i} の内容です。" * 5 for i in range(1000)]

    start = _now_ms()
    embeddings = [embedding_service.get_embedding(text) for text in texts]
    elapsed = _now_ms() - start

    assert len(embeddings) == 1000
    assert all(len(e) == 1536 for e in embeddings)
    assert elapsed < THRESHOLDS["embedding_generation_1000_texts_ms"], \
        f"Embedding 1000 texts took {elapsed:.0f}ms, threshold {THRESHOLDS['embedding_generation_1000_texts_ms']}ms"


# ベンチマーク基準値管理用
def test_thresholds_are_reasonable():
    """閾値が妥当な範囲内か確認（CI で変更検知用）"""
    # 閾値が正の整数
    for key, value in THRESHOLDS.items():
        assert isinstance(value, int), f"{key} must be int"
        assert value > 0, f"{key} must be positive"

    # 既知のベースラインとの比較（大幅な緩和防止）
    # これらの値は実測ベースラインから算出
    assert THRESHOLDS["age_upsert_1000_nodes_ms"] <= 5000
    assert THRESHOLDS["pgvector_search_1000_docs_ms"] <= 100
    assert THRESHOLDS["rag_hybrid_search_ms"] <= 200