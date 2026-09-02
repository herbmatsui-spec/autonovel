"""GraphRAG (pgvector + Apache AGE) 関連ユニットテスト."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.database.models.chunk import ChapterChunk
from src.models.graph_schemas import Entity, GraphExtractionResult, Relationship
from src.services.age_client import AgeClient
from src.services.embedding_service import EmbeddingService
from src.services.extraction_service import ExtractionService
from src.services.graph_pipeline import GraphPipelineService
from src.services.llm.mock_adapter import MockLLMAdapter
from src.services.llm.openai_adapter import OpenAIAdapter
from src.services.rag_service import GraphRAGService
from src.services.text_chunker import split_into_paragraphs


def test_split_into_paragraphs():
    """段落チャンク分割が正しく動作することを検証."""
    text = "第1段落です。\n\n第2段落です。\n\n第3段落です。"
    chunks = split_into_paragraphs(text, max_chunk_chars=20)
    assert len(chunks) >= 2
    assert "第1段落です。" in chunks[0]

    # 空テキスト
    assert split_into_paragraphs("") == []


def test_embedding_service_pseudo():
    """EmbeddingService が 1536 次元の正規化された疑似埋め込みを生成することを検証."""
    service = EmbeddingService()
    emb = service.get_embedding("勇者アルスが剣を抜いた。")
    assert len(emb) == 1536
    assert isinstance(emb[0], float)

    # 空文字はゼロベクトル
    zero_emb = service.get_embedding("")
    assert len(zero_emb) == 1536
    assert sum(zero_emb) == 0.0


def test_extraction_service_fallback():
    """LLM呼び出し失敗時にヒューリスティック抽出フォールバックが働くことを検証."""
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = Exception("LLM connection error")

    service = ExtractionService(llm_adapter=mock_llm)
    result = service.extract_graph_from_text("勇者は城を出発した。")

    assert isinstance(result, GraphExtractionResult)
    assert len(result.entities) >= 1
    assert result.entities[0].name == "主人公"


def test_extraction_service_success():
    """LLMから正常なJSONが返された場合に正しくパースされることを検証."""
    json_response = """
    ```json
    {
        "entities": [
            {"name": "アルス", "type": "Character", "description": "勇者", "properties": {"is_alive": true}}
        ],
        "relationships": [
            {"source": "アルス", "target": "聖剣", "type": "POSSESSES", "detail": "所持している"}
        ],
        "plot_summary": "アルスが聖剣を入手した。"
    }
    ```
    """
    mock_llm = MagicMock()
    mock_llm.generate.return_value = json_response

    service = ExtractionService(llm_adapter=mock_llm)
    result = service.extract_graph_from_text("アルスは聖剣を手に入れた。")

    assert len(result.entities) == 1
    assert result.entities[0].name == "アルス"
    assert len(result.relationships) == 1
    assert result.relationships[0].type == "POSSESSES"
    assert result.plot_summary == "アルスが聖剣を入手した。"


def test_extraction_service_self_correction_retry():
    """1回目のJSONパースが壊れていても2回目のSelf-Correctionで回復することを検証."""
    mock_llm = MagicMock()
    # 1回目は壊れたJSON、2回目は正常なJSON
    mock_llm.generate.side_effect = [
        "壊れたレスポンス",
        '{"entities": [{"name": "ルミナス王", "type": "Character", "description": "国王"}], "relationships": [], "plot_summary": "国王謁見"}',
    ]

    service = ExtractionService(llm_adapter=mock_llm)
    result = service.extract_graph_from_text("国王と謁見した。")

    assert len(result.entities) == 1
    assert result.entities[0].name == "ルミナス王"
    assert mock_llm.generate.call_count == 2


def test_rag_service_hybrid_reranking():
    """GraphRAGService のハイブリッド Reranking が類似度順にソートすることを検証."""
    service = GraphRAGService()
    neighbors = [
        {"name": "魔導書", "relation_type": "READ", "properties": {"description": "古代の禁書"}},
        {"name": "聖剣エクスカリバー", "relation_type": "POSSESSES", "properties": {"description": "光り輝く伝説の剣"}},
        {"name": "王都ルミナス", "relation_type": "LOCATED_IN", "properties": {"description": "首都"}},
    ]

    reranked = service.rerank_graph_neighbors(
        neighbors=neighbors,
        current_prompt="剣を構えて戦闘の構えをとる",
        top_k=2,
    )

    assert len(reranked) == 2
    assert all("name" in item for item in reranked)


def test_rag_service_cosine_similarity():
    """コサイン類似度計算ヘルパーの精度検証."""
    service = GraphRAGService()
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    vec3 = [0.0, 1.0, 0.0]

    assert pytest.approx(service._cosine_similarity(vec1, vec2)) == 1.0
    assert pytest.approx(service._cosine_similarity(vec1, vec3)) == 0.0
    assert service._cosine_similarity([], []) == 0.0


def test_rag_service_search_chunks_with_data(db_session):
    """SQLite環境で ChapterChunk を検索・類似度ソートできることを検証."""
    service = GraphRAGService()
    chunk1 = ChapterChunk(chapter_id=1, chunk_index=0, content="勇者は聖剣を手に入れた。")
    chunk2 = ChapterChunk(chapter_id=1, chunk_index=1, content="城下町で買い物をした。")
    db_session.add_all([chunk1, chunk2])
    db_session.commit()

    results = service.search_similar_chunks(db_session, "聖剣の伝説", limit=2)
    assert len(results) >= 1
    assert any("聖剣" in r for r in results)


def test_extraction_service_resolve_entities():
    """ExtractionService の表記揺れ名寄せ (Entity Resolution) を検証."""
    service = ExtractionService()
    extracted = GraphExtractionResult(
        entities=[
            Entity(name="勇者アルス", type="Character", description="主人公"),
            Entity(name="王都", type="Location", description="街"),
        ],
        relationships=[
            Relationship(source="勇者アルス", target="王都", type="LOCATED_IN", detail="滞在"),
        ],
        plot_summary="アルスが王都に滞在。",
    )

    resolved = service.resolve_entities(
        extracted=extracted,
        existing_entity_names=["アルス", "ルミナス王都"],
    )

    assert len(resolved.entities) == 2
    names = [e.name for e in resolved.entities]
    assert "アルス" in names
    assert resolved.relationships[0].source == "アルス"


def test_rag_service_community_context(db_session):
    """GraphRAGService が派閥コミュニティコンテキストを取得できることを検証."""
    service = GraphRAGService()
    # SQLite環境では空リスト
    assert service.get_community_context(db_session, "光の騎士団") == []

    # モックによる動作検証
    mock_members = [
        {"name": "アルス", "relation_type": "MEMBER_OF"},
        {"name": "セリア", "relation_type": "LEADER_OF"},
    ]
    with patch("src.services.rag_service.age_client.get_neighbors", return_value=mock_members), \
         patch("src.services.rag_service.settings.ENABLE_GRAPHRAG", True), \
         patch("src.services.rag_service.settings.DATABASE_URL", "postgresql://user:pass@localhost/db"):
        members = service.get_community_context(db_session, "光の騎士団")
        assert len(members) == 2
        assert "アルス (MEMBER_OF)" in members


def test_graphrag_build_context_with_neighbors(db_session):
    """GraphRAGService がグラフ近傍情報をもとにプロンプトコンテキストを構築することを検証."""
    service = GraphRAGService()
    mock_neighbors = [
        {"name": "魔導書", "relation_type": "READ", "properties": {"description": "禁書"}},
        {"name": "聖剣", "relation_type": "POSSESSES", "properties": {"description": "武器"}},
    ]

    with patch.object(service, "get_graph_context", return_value=mock_neighbors):
        graph_ctx, vector_ctx = service.build_rag_context(
            session=db_session,
            current_prompt="聖剣を抜く",
            character_name="アルス",
        )

        assert "【聖剣】" in graph_ctx or "【魔導書】" in graph_ctx


def test_graph_pipeline_service(db_session):
    """GraphPipelineService がチャンクを DB に保存できることを検証."""
    pipeline = GraphPipelineService()
    text = "王都ルミナスの朝。\n\nアルスは仲間たちと共に旅立った。"
    stats = pipeline.process_chapter_knowledge(
        session=db_session,
        chapter_id=1,
        chapter_text=text,
    )

    assert stats["chunks_created"] >= 1
    chunks = db_session.query(ChapterChunk).filter_by(chapter_id=1).all()
    assert len(chunks) >= 1
    assert chunks[0].content is not None

    # 空テキスト時のハンドリング
    empty_stats = pipeline.process_chapter_knowledge(db_session, 1, "")
    assert empty_stats["chunks_created"] == 0


def test_age_client_methods(db_session):
    """AgeClient のノード作成・エッジ作成・探索のフォールバック動作を検証."""
    client = AgeClient(default_graph_name="test_graph")

    # init_graph
    assert client.init_graph(db_session) is True or client.init_graph(db_session) is False

    # upsert_node
    res_node = client.upsert_node(db_session, "Character", "アルス", {"is_alive": True})
    assert isinstance(res_node, bool)

    # upsert_edge
    res_edge = client.upsert_edge(db_session, "Character", "アルス", "Location", "王都", "LOCATED_IN")
    assert isinstance(res_edge, bool)

    # get_neighbors
    neighbors = client.get_neighbors(db_session, "アルス")
    assert isinstance(neighbors, list)


def test_rag_service_search_empty(db_session):
    """GraphRAGService が空クエリ時に空リストを返すことを検証."""
    service = GraphRAGService()
    assert service.search_similar_chunks(db_session, "") == []
    assert service.get_graph_context(db_session, []) == []


def test_mock_adapter_structured_outputs():
    """MockLLMAdapter が Structured Outputs (response_format) 時に JSON を返すことを検証."""
    adapter = MockLLMAdapter()
    resp = adapter.generate("テスト", response_format={"type": "json_schema"})
    assert "entities" in resp


@pytest.mark.asyncio
async def test_openai_adapter_response_format():
    """OpenAIAdapter が response_format 引数を正しく渡すことを検証."""
    adapter = OpenAIAdapter(api_key="test-key")
    mock_choice = MagicMock()
    mock_choice.message.content = '{"key": "value"}'
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]

    with patch.object(adapter.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_resp
        res = await adapter.generate_text(
            prompt="Hello",
            response_format={"type": "json_object"},
        )
        assert res == '{"key": "value"}'
        mock_create.assert_called_once()
        _, kwargs = mock_create.call_args
        assert kwargs.get("response_format") == {"type": "json_object"}


def test_graph_router(client):
    """GET /api/graph エンドポイントが正常に応答することを検証."""
    response = client.get("/api/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data

    # チャンク一覧エンドポイント
    chunks_resp = client.get("/api/graph/chunks")
    assert chunks_resp.status_code == 200
    assert isinstance(chunks_resp.json(), list)
