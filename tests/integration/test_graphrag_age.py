"""GraphRAG 統合テスト (testcontainers + 実PostgreSQL+AGE+pgvector).

以下を検証:
- age_client: init_graph, upsert_node/edge, get_neighbors, batch operations
- vector_store: PgVectorStore add/search/hybrid_search
- graph_pipeline: process_chapter_knowledge, batch processing
- rag_service: hybrid_search, build_rag_context, reranking
- FastAPI endpoints (via TestClient)
"""
from __future__ import annotations

import socket
import time

import pytest

try:
    from testcontainers.postgres import PostgresContainer

    _HAS_TESTCONTAINERS = True
except Exception:
    _HAS_TESTCONTAINERS = False


def _docker_available() -> bool:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.close()
        return True
    except Exception:
        pass
    try:
        s = socket.create_connection(("localhost", 2375), timeout=0.5)
        s.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (_HAS_TESTCONTAINERS and _docker_available()),
    reason="testcontainers / Docker daemon not available",
)


@pytest.fixture(scope="module")
def age_container():
    """Apache AGE イメージを起動し、pgvector エクステンションをインストールし SQLAlchemy engine を返す."""
    from sqlalchemy import create_engine, text

    container = PostgresContainer("apache/age:latest")
    container.start()
    url = container.get_connection_url()
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(url)
    try:
        # Ensure age extension is available (should be in the image)
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS age;"))
            conn.commit()
        # Try to create vector extension; if it fails, we note that vector may not be available
        with engine.connect() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
            except Exception:
                # Vector extension not available; tests requiring it should skip
                pass
        yield engine
    finally:
        engine.dispose()
        container.stop()


@pytest.fixture(scope="module")
def age_session(age_container):
    """セッションフィクスチャ."""
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=age_container)
    session = Session()
    try:
        yield session
    finally:
        session.close()


# ============================================================
# age_client Tests
# ============================================================

def test_age_init_graph_idempotent(age_session):
    """init_graph を 2 回呼んでも両方 True でグラフ重複作成エラーにならない."""
    from src.services.age_client import AgeClient

    client = AgeClient(default_graph_name="test_graph_idem")
    assert client.init_graph(age_session) is True
    assert client.init_graph(age_session) is True


def test_age_upsert_node_dedup(age_session):
    """同じ (label, name) で 2 回 upsert_node してもノードは 1 つだけ."""
    from sqlalchemy import text

    from src.services.age_client import AgeClient

    client = AgeClient(default_graph_name="test_graph_dedup")
    assert client.init_graph(age_session) is True
    assert client.upsert_node(age_session, "Character", "アルス", {"age": 20}) is True
    assert client.upsert_node(age_session, "Character", "アルス", {"age": 21}) is True

    cnt = age_session.execute(
        text(
            "SELECT count(*)::text FROM cypher('test_graph_dedup', "
            "$$ MATCH (n:Character {name: 'アルス'}) RETURN n $$) as (c agtype);"
        )
    ).scalar()
    assert int(str(cnt).strip('"')) == 1


def test_age_sqlstate_duplicate_graph_returns_true(age_session):
    """pgcode 42P04 (duplicate_graph) が出ても init_graph は True を返す (SQLSTATE ベース)."""
    from sqlalchemy import text

    from src.services.age_client import AgeClient

    client = AgeClient(default_graph_name="test_graph_pgcode")
    assert client.init_graph(age_session) is True
    assert client.init_graph(age_session) is True
    age_session.execute(text('SET search_path = ag_catalog, "$user", public;'))
    rows = age_session.execute(
        text("SELECT name FROM ag_graph WHERE name = 'test_graph_pgcode';")
    ).fetchall()
    assert any(r[0] == "test_graph_pgcode" for r in rows)


def test_age_upsert_node_with_properties(age_session):
    """プロパティ付きノードのUPSERTと取得."""
    from src.services.age_client import AgeClient

    client = AgeClient(default_graph_name="test_graph_props")
    assert client.init_graph(age_session) is True

    props = {"age": 25, "is_alive": True, "title": "勇者", "tags": ["main", "sword"]}
    assert client.upsert_node(age_session, "Character", "アルス", props) is True

    # 取得確認
    result = client.execute_cypher(
        age_session,
        "MATCH (n:Character {name: $name}) RETURN n",
        parameters={"name": "アルス"},
        graph_name="test_graph_props",
    )
    assert len(result.records) == 1
    node = result.records[0]["n"]
    assert node["name"] == "アルス"
    assert node["age"] == 25
    assert node["is_alive"] is True


def test_age_upsert_edge(age_session):
    """エッジのUPSERT."""
    from src.services.age_client import AgeClient

    client = AgeClient(default_graph_name="test_graph_edge")
    assert client.init_graph(age_session) is True

    # ノード作成
    client.upsert_node(age_session, "Character", "アルス", {"role": "hero"})
    client.upsert_node(age_session, "Item", "聖剣", {"rarity": "legendary"})

    # エッジ作成
    assert client.upsert_edge(
        age_session, "Character", "アルス", "Item", "聖剣", "POSSESSES", {"since": "chapter_1"}
    ) is True

    # 検証
    result = client.execute_cypher(
        age_session,
        "MATCH (a:Character {name: 'アルス'})-[r:POSSESSES]->(b:Item {name: '聖剣'}) RETURN r",
        graph_name="test_graph_edge",
    )
    assert len(result.records) == 1
    edge = result.records[0]["r"]
    assert edge["since"] == "chapter_1"


def test_age_get_neighbors(age_session):
    """近傍ノード探索."""
    from src.services.age_client import AgeClient

    client = AgeClient(default_graph_name="test_graph_neighbors")
    assert client.init_graph(age_session) is True

    # グラフ構築: アルス -> 聖剣 -> 竜 -> 王都
    client.upsert_node(age_session, "Character", "アルス", {})
    client.upsert_node(age_session, "Item", "聖剣", {})
    client.upsert_node(age_session, "Character", "竜", {})
    client.upsert_node(age_session, "Location", "王都", {})

    client.upsert_edge(age_session, "Character", "アルス", "Item", "聖剣", "POSSESSES")
    client.upsert_edge(age_session, "Item", "聖剣", "Character", "竜", "CONTROLS")
    client.upsert_edge(age_session, "Character", "竜", "Location", "王都", "LOCATED_IN")

    # 1ホップ
    neighbors = client.get_neighbors(age_session, "アルス", max_depth=1)
    assert len(neighbors) >= 1
    assert any(n["name"] == "聖剣" for n in neighbors)

    # 2ホップ
    neighbors = client.get_neighbors(age_session, "アルス", max_depth=2)
    names = {n["name"] for n in neighbors}
    assert "聖剣" in names
    assert "竜" in names


def test_age_batch_upsert(age_session):
    """バッチUPSERT."""
    from src.services.age_client import AgeClient

    client = AgeClient(default_graph_name="test_graph_batch")
    assert client.init_graph(age_session) is True

    nodes = [
        {"label": "Character", "name": f"キャラ{i}", "properties": {"idx": i}}
        for i in range(10)
    ]
    count = client.upsert_nodes_batch(age_session, nodes)
    assert count == 10

    edges = [
        {
            "source_label": "Character",
            "source_name": f"キャラ{i}",
            "target_label": "Character",
            "target_name": f"キャラ{i+1}",
            "relation_type": "KNOWS",
        }
        for i in range(9)
    ]
    count = client.upsert_edges_batch(age_session, edges)
    assert count == 9


def test_age_cypher_parameters(age_session):
    """パラメータ化Cypherクエリ（SQLインジェクション対策）."""
    from src.services.age_client import AgeClient

    client = AgeClient(default_graph_name="test_graph_param")
    assert client.init_graph(age_session) is True

    client.upsert_node(age_session, "Character", "テスト", {"secret": "value"})

    # パラメータ化クエリ
    result = client.execute_cypher(
        age_session,
        "MATCH (n:Character {name: $name}) RETURN n.secret as secret",
        parameters={"name": "テスト"},
        graph_name="test_graph_param",
    )
    assert len(result.records) == 1
    assert result.records[0]["secret"] == "value"

    # SQLインジェクション試行（パラメータ化されていれば安全）
    result = client.execute_cypher(
        age_session,
        "MATCH (n:Character {name: $name}) RETURN n",
        parameters={"name": "テスト' OR '1'='1"},
        graph_name="test_graph_param",
    )
    # 結果は空（該当ノードなし）
    assert len(result.records) == 0


def test_age_graph_stats(age_session):
    """グラフ統計取得."""
    from src.services.age_client import AgeClient

    client = AgeClient(default_graph_name="test_graph_stats")
    assert client.init_graph(age_session) is True

    client.upsert_node(age_session, "Character", "A", {})
    client.upsert_node(age_session, "Item", "B", {})
    client.upsert_edge(age_session, "Character", "A", "Item", "B", "HAS")

    stats = client.get_graph_stats(age_session)
    assert stats.node_count >= 2
    assert stats.edge_count >= 1
    assert "Character" in stats.labels
    assert "Item" in stats.labels
    assert "HAS" in stats.relationship_types


# ============================================================
# PgVectorStore Tests
# ============================================================

def test_pgvector_store_init(age_container):
    """PgVectorStore 初期化."""
    from src.services.vector_store import PgVectorStore, HAS_PGVECTOR

    if not HAS_PGVECTOR:
        pytest.skip("pgvector not installed")

    url = str(age_container.url).replace("postgresql+psycopg2://", "postgresql://")
    store = PgVectorStore(url, dimension=1536)
    import asyncio
    asyncio.run(store._ensure_table("test_collection"))
    # テーブル作成確認
    from sqlalchemy import text
    with age_container.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'vec_test_collection'
            )
        """))
        assert result.scalar() is True


@pytest.mark.asyncio
async def test_pgvector_store_add_search(age_container):
    """PgVectorStore 追加と検索."""
    from src.services.vector_store import PgVectorStore, HAS_PGVECTOR

    if not HAS_PGVECTOR:
        pytest.skip("pgvector not installed")

    url = str(age_container.url).replace("postgresql+psycopg2://", "postgresql://")
    store = PgVectorStore(url, dimension=4)  # 小さな次元でテスト

    # テスト用エンベディング
    docs = ["勇者は聖剣を手に入れた", "王都で仲間と出会った", "魔獣と戦闘した"]
    embeddings = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    ]
    ids = ["doc1", "doc2", "doc3"]
    metas = [{"source": "ep1"}, {"source": "ep2"}, {"source": "ep3"}]

    await store.add_documents("test_search", ids, docs, embeddings, metas)

    # 類似検索
    query_emb = [0.9, 0.1, 0.0, 0.0]  # doc1に近い
    results = await store.search("test_search", query_emb, top_k=2)
    assert len(results) == 2
    assert results[0]["content"] == "勇者は聖剣を手に入れた"
    assert results[0]["similarity"] > results[1]["similarity"]


@pytest.mark.asyncio
async def test_pgvector_store_hybrid_search(age_container):
    """PgVectorStore ハイブリッド検索 (ベクトル + 全文)."""
    from src.services.vector_store import PgVectorStore, HAS_PGVECTOR

    if not HAS_PGVECTOR:
        pytest.skip("pgvector not installed")

    url = str(age_container.url).replace("postgresql+psycopg2://", "postgresql://")
    store = PgVectorStore(url, dimension=4)

    docs = [
        "勇者アルスが聖剣エクスカリバーを手に入れた",
        "王都ルミナスで魔法使いセリアと出会った",
        "魔獣グリフォンと激しい戦闘を繰り広げた",
    ]
    embeddings = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    ]
    ids = ["doc1", "doc2", "doc3"]

    await store.add_documents("test_hybrid", ids, docs, embeddings)

    # ハイブリッド検索
    query = "聖剣 エクスカリバー"
    query_emb = [0.9, 0.1, 0.0, 0.0]
    results = await store.hybrid_search("test_hybrid", query, query_emb, top_k=2, alpha=0.5)

    assert len(results) >= 1
    assert results[0]["content"] == "勇者アルスが聖剣エクスカリバーを手に入れた"
    assert "rrf_score" in results[0]


# ============================================================
# graph_pipeline Tests
# ============================================================

def test_graph_pipeline_process_chapter(age_session):
    """単章処理パイプライン."""
    from src.services.graph_pipeline import GraphPipelineService

    pipeline = GraphPipelineService()
    text = "勇者アルスは聖剣エクスカリバーを手に入れ、王都ルミナスへ向かった。\n\n門番のガレスが出迎えた。"

    # モックLLMを使用するため、extraction_serviceをパッチ
    from unittest.mock import patch, MagicMock
    from src.models.graph_schemas import GraphExtractionResult, Entity, Relationship

    mock_extraction = GraphExtractionResult(
        entities=[
            Entity(name="アルス", type="Character", description="主人公", properties={"is_alive": True}),
            Entity(name="聖剣エクスカリバー", type="Item", description="伝説の剣", properties={}),
            Entity(name="王都ルミナス", type="Location", description="首都", properties={}),
        ],
        relationships=[
            Relationship(source="アルス", target="聖剣エクスカリバー", type="POSSESSES", detail="所持"),
            Relationship(source="アルス", target="王都ルミナス", type="LOCATED_IN", detail="向かう"),
        ],
        plot_summary="アルスが聖剣を得て王都へ向かう",
    )

    with patch("src.services.graph_pipeline.extraction_service.extract_graph_from_text", return_value=mock_extraction), \
         patch("src.services.graph_pipeline.extraction_service.resolve_entities", return_value=mock_extraction), \
         patch("src.services.graph_pipeline.settings.ENABLE_GRAPHRAG", True):
        result = pipeline.process_chapter_knowledge(age_session, 1, text)

    assert result["chunks_created"] >= 1
    assert result["entities_created"] >= 2
    assert result["relationships_created"] >= 1


def test_graph_pipeline_batch(age_session):
    """バッチ処理パイプライン."""
    from src.services.graph_pipeline import GraphPipelineService
    from unittest.mock import patch
    from src.models.graph_schemas import GraphExtractionResult, Entity, Relationship

    pipeline = GraphPipelineService()
    chapters = [
        (1, "第1話: アルスが旅立ち聖剣を得る。"),
        (2, "第2話: 王都でセリアと出会う。"),
        (3, "第3話: 魔獣と戦う。"),
    ]

    mock_extraction = GraphExtractionResult(
        entities=[Entity(name="テスト", type="Character", description="テスト", properties={})],
        relationships=[],
        plot_summary="テスト",
    )

    with patch("src.services.graph_pipeline.extraction_service.extract_graph_from_text", return_value=mock_extraction), \
         patch("src.services.graph_pipeline.extraction_service.resolve_entities", return_value=mock_extraction), \
         patch("src.services.graph_pipeline.settings.ENABLE_GRAPHRAG", True):
        stats = pipeline.process_chapters_batch(age_session, chapters)

    assert stats.chapters_processed == 3
    assert stats.chunks_created >= 3


# ============================================================
# rag_service Tests
# ============================================================

def test_rag_hybrid_search(age_session):
    """ハイブリッド検索 (Vector + Graph + Fulltext)."""
    from src.services.rag_service import GraphRAGService
    from unittest.mock import patch, MagicMock
    from src.models.graph_schemas import GraphExtractionResult, Entity, Relationship

    service = GraphRAGService()

    # チャンクデータ準備
    from src.infrastructure.database.models.chunk import ChapterChunk
    chunk1 = ChapterChunk(chapter_id=1, chunk_index=0, content="アルスが聖剣を手に入れた", embedding=[1.0]*1536)
    chunk2 = ChapterChunk(chapter_id=1, chunk_index=1, content="王都でセリアと出会った", embedding=[0.0]*1536 + [1.0]*1536)
    age_session.add_all([chunk1, chunk2])
    age_session.commit()

    # グラフデータ準備
    from src.services.age_client import AgeClient
    client = AgeClient(default_graph_name="test_rag_graph")
    client.init_graph(age_session)
    client.upsert_node(age_session, "Character", "アルス", {})
    client.upsert_node(age_session, "Item", "聖剣", {})

    with patch.object(service, "get_reranker") as mock_reranker:
        mock_reranker.return_value.rerank.return_value = [(0, 0.9), (1, 0.5)]
        results = service.hybrid_search(age_session, "聖剣", core_entities=["アルス"], top_k=5)

    assert len(results) > 0
    assert any(r.source in ("vector", "graph", "fulltext") for r in results)


def test_rag_build_context(age_session):
    """RAGコンテキスト構築."""
    from src.services.rag_service import GraphRAGService
    from unittest.mock import patch
    from src.models.graph_schemas import GraphExtractionResult, Entity, Relationship

    service = GraphRAGService()

    # グラフデータ
    from src.services.age_client import AgeClient
    client = AgeClient(default_graph_name="test_rag_ctx")
    client.init_graph(age_session)
    client.upsert_node(age_session, "Character", "アルス", {"description": "主人公"})
    client.upsert_node(age_session, "Item", "聖剣", {"description": "伝説の剣"})

    # チャンク
    from src.infrastructure.database.models.chunk import ChapterChunk
    chunk = ChapterChunk(chapter_id=1, chunk_index=0, content="アルスは聖剣を抜いた", embedding=[0.5]*1536)
    age_session.add(chunk)
    age_session.commit()

    with patch("src.services.rag_service.settings.ENABLE_GRAPHRAG", True), \
         patch("src.services.rag_service.settings.DATABASE_URL", "postgresql://test"):
        context = service.build_rag_context(
            age_session,
            current_prompt="聖剣を構える",
            character_name="アルス",
        )

    assert "アルス" in context.graph_context
    assert "聖剣" in context.vector_context or "アルス" in context.vector_context


# ============================================================
# FastAPI Endpoint Tests
# ============================================================

def test_graph_api_endpoints(age_container):
    """FastAPI エンドポイントテスト."""
    from fastapi.testclient import TestClient
    from src.backend.server import app
    from sqlalchemy.orm import sessionmaker

    # テスト用DB接続設定
    url = str(age_container.url).replace("postgresql+psycopg2://", "postgresql://")
    import os
    os.environ["DATABASE_URL"] = url
    os.environ["ENABLE_GRAPHRAG"] = "true"

    # アプリの再初期化が必要な場合があるため、コンテナごとに新しいクライアント
    client = TestClient(app)

    # ヘルスチェック
    resp = client.get("/health")
    assert resp.status_code == 200

    # グラフデータ取得
    resp = client.get("/api/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data


# ============================================================
# Performance Tests
# ============================================================

@pytest.mark.perf
def test_age_performance_1000_nodes(age_session):
    """1000ノードでのパフォーマンステスト."""
    from src.services.age_client import AgeClient

    client = AgeClient(default_graph_name="test_perf")
    assert client.init_graph(age_session) is True

    # 1000ノード一括作成
    nodes = [
        {"label": "Character", "name": f"キャラ{i}", "properties": {"idx": i}}
        for i in range(1000)
    ]

    start = time.perf_counter()
    count = client.upsert_nodes_batch(age_session, nodes)
    elapsed = (time.perf_counter() - start) * 1000

    assert count == 1000
    print(f"1000 nodes batch upsert: {elapsed:.2f}ms")
    # 目安: 5秒以内
    assert elapsed < 5000


@pytest.mark.perf
def test_pgvector_performance_1000_docs(age_container):
    """1000ドキュメントでのベクトル検索パフォーマンス."""
    from src.services.vector_store import PgVectorStore, HAS_PGVECTOR

    if not HAS_PGVECTOR:
        pytest.skip("pgvector not installed")

    url = str(age_container.url).replace("postgresql+psycopg2://", "postgresql://")
    store = PgVectorStore(url, dimension=128)

    docs = [f"ドキュメント {i} の内容です。" for i in range(1000)]
    embeddings = [[float(i % 128) / 128.0] * 128 for i in range(1000)]
    ids = [f"doc{i}" for i in range(1000)]

    import asyncio
    start = time.perf_counter()
    asyncio.run(store.add_documents("perf_test", ids, docs, embeddings))
    ingest_elapsed = (time.perf_counter() - start) * 1000

    query_emb = [0.5] * 128
    start = time.perf_counter()
    results = asyncio.run(store.search("perf_test", query_emb, top_k=10))
    search_elapsed = (time.perf_counter() - start) * 1000

    assert len(results) == 10
    print(f"1000 docs ingest: {ingest_elapsed:.2f}ms, search: {search_elapsed:.2f}ms")
    assert search_elapsed < 100  # 100ms以内


# ============================================================
# Error Handling Tests
# ============================================================

def test_age_invalid_cypher(age_session):
    """無効なCypherクエリのエラーハンドリング."""
    from src.services.age_client import AgeClient

    client = AgeClient(default_graph_name="test_error")
    client.init_graph(age_session)

    with pytest.raises(Exception):
        client.execute_cypher(age_session, "INVALID CYPHER QUERY", graph_name="test_error")


def test_age_connection_retry(age_container):
    """接続リトライ動作."""
    from src.services.age_client import AgeClient
    from sqlalchemy import create_engine

    # 正常な接続でリトライが不要なことを確認
    client = AgeClient(default_graph_name="test_retry")
    session_factory = create_engine(str(age_container.url).replace("postgresql+psycopg2://", "postgresql+psycopg2://")).connect()
    session = session_factory

    # 複数回実行してもエラーにならない
    for _ in range(3):
        assert client.init_graph(session, "test_retry") is True

    session.close()


# ============================================================
# Full E2E Test
# ============================================================

def test_graphrag_e2e(age_session):
    """GraphRAG エンドツーエンドテスト:
    1. チャプターテキストを入力
    2. エンティティ抽出
    3. チャンク保存 + ベクトル化
    4. グラフ更新
    5. ハイブリッド検索で関連情報取得
    6. RAGコンテキスト生成
    """
    from src.services.graph_pipeline import GraphPipelineService
    from src.services.rag_service import GraphRAGService
    from src.services.age_client import AgeClient
    from unittest.mock import patch
    from src.models.graph_schemas import GraphExtractionResult, Entity, Relationship
    from src.infrastructure.database.models.chunk import ChapterChunk

    # 1. テストデータ
    chapter_text = """
    勇者アルスは聖剣エクスカリバーを手に入れた。
    王都ルミナスの門をくぐると、門番のガレスが懐かしそうに微笑んだ。
    「よく戻ったな、アルス」とガレスは言った。
    アルスは聖剣を掲げ、新たな旅の始まりを感じた。
    """

    # 2. モック抽出結果
    mock_extraction = GraphExtractionResult(
        entities=[
            Entity(name="アルス", type="Character", description="勇者。聖剣所持", properties={"is_alive": True}),
            Entity(name="聖剣エクスカリバー", type="Item", description="伝説の聖剣", properties={"rarity": "legendary"}),
            Entity(name="王都ルミナス", type="Location", description="王国の首都", properties={}),
            Entity(name="ガレス", type="Character", description="門番。アルスの知り合い", properties={"role": "gatekeeper"}),
        ],
        relationships=[
            Relationship(source="アルス", target="聖剣エクスカリバー", type="POSSESSES", detail="手に入れた"),
            Relationship(source="アルス", target="王都ルミナス", type="LOCATED_IN", detail="門をくぐった"),
            Relationship(source="ガレス", target="アルス", type="KNOWS", detail="知り合い"),
        ],
        plot_summary="アルスが聖剣を得て王都に帰還",
    )

    # 3. パイプライン実行
    pipeline = GraphPipelineService()
    with patch("src.services.graph_pipeline.extraction_service.extract_graph_from_text", return_value=mock_extraction), \
         patch("src.services.graph_pipeline.extraction_service.resolve_entities", return_value=mock_extraction), \
         patch("src.services.graph_pipeline.settings.ENABLE_GRAPHRAG", True):
        result = pipeline.process_chapter_knowledge(age_session, 1, chapter_text)

    assert result["chunks_created"] >= 1
    assert result["entities_created"] >= 4
    assert result["relationships_created"] >= 3

    # 4. ハイブリッド検索
    rag = GraphRAGService()

    # グラフデータ確認
    client = AgeClient(default_graph_name="autonovel_graph")
    neighbors = client.get_neighbors(age_session, "アルス", max_depth=2)
    names = {n["name"] for n in neighbors}
    assert "聖剣エクスカリバー" in names
    assert "王都ルミナス" in names
    assert "ガレス" in names

    # 5. RAGコンテキスト生成
    with patch("src.services.rag_service.settings.ENABLE_GRAPHRAG", True), \
         patch("src.services.rag_service.settings.DATABASE_URL", "postgresql://test"):
        context = rag.build_rag_context(
            age_session,
            current_prompt="聖剣を構えて戦闘の構えをとる",
            character_name="アルス",
        )

    assert "アルス" in context.graph_context
    assert "聖剣" in context.graph_context or "聖剣" in context.vector_context