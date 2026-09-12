from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.services.rag.context_retriever import (
    ForeshadowingStatus,
    ForeshadowingEntity,
    LongFormContextRetriever,
)
from src.services.graph.subgraph_extractor import (
    extract_character_subgraph,
    build_knowledge_graph_from_entities,
    KnowledgeGraphExtractor,
)
import networkx as nx


class MockChromaCollection:
    """Mock ChromaDB collection for testing"""
    
    def __init__(self):
        self.data = {}
    
    def upsert(self, ids, documents, metadatas):
        for id_, doc, meta in zip(ids, documents, metadatas):
            self.data[id_] = {"document": doc, "metadata": meta}
    
    def get(self, ids=None, where=None):
        if ids:
            return {
                "ids": ids,
                "metadatas": [self.data[id_]["metadata"] for id_ in ids if id_ in self.data],
                "documents": [self.data[id_]["document"] for id_ in ids if id_ in self.data],
            }
        return {
            "ids": list(self.data.keys()),
            "metadatas": [v["metadata"] for v in self.data.values()],
            "documents": [v["document"] for v in self.data.values()],
        }
    
    def query(self, query_texts, n_results=3, where=None):
        # 簡易的なモック: 全件返す
        items = list(self.data.values())
        return {
            "ids": [list(self.data.keys())[:n_results]],
            "metadatas": [[v["metadata"] for v in items[:n_results]]],
            "documents": [[v["document"] for v in items[:n_results]]],
            "distances": [[0.1] * min(n_results, len(items))],
        }
    
    def update(self, ids, metadatas):
        for id_, meta in zip(ids, metadatas):
            if id_ in self.data:
                self.data[id_]["metadata"] = meta


class MockChromaClient:
    """Mock ChromaDB client"""
    
    def __init__(self):
        self.collections = {}
    
    def get_collection(self, name):
        if name not in self.collections:
            raise ValueError(f"Collection {name} not found")
        return self.collections[name]
    
    def create_collection(self, name, embedding_function=None, metadata=None):
        collection = MockChromaCollection()
        self.collections[name] = collection
        return collection


def test_foreshadowing_entity_creation():
    entity = ForeshadowingEntity.create(
        description="主人公の剣に隠された力",
        introduced_in_ep=1,
        target_resolution_ep=10,
        related_characters=["主人公", "師匠"],
        keywords=["剣", "隠された力", "覚醒"],
    )
    
    assert entity.foreshadow_id is not None
    assert len(entity.foreshadow_id) == 8
    assert entity.description == "主人公の剣に隠された力"
    assert entity.introduced_in_ep == 1
    assert entity.target_resolution_ep == 10
    assert entity.status == ForeshadowingStatus.OPEN
    assert "主人公" in entity.related_characters
    assert "剣" in entity.keywords


def test_foreshadowing_entity_serialization():
    entity = ForeshadowingEntity.create(
        description="テスト伏線",
        introduced_in_ep=1,
    )
    
    # to_dict
    data = entity.to_dict()
    assert data["foreshadow_id"] == entity.foreshadow_id
    assert data["description"] == "テスト伏線"
    assert data["status"] == "open"
    
    # from_dict
    restored = ForeshadowingEntity.from_dict(data)
    assert restored.foreshadow_id == entity.foreshadow_id
    assert restored.description == entity.description
    assert restored.status == entity.status


def test_context_retriever_initialization():
    mock_client = MockChromaClient()
    retriever = LongFormContextRetriever(chroma_client=mock_client)
    
    assert retriever.chroma_client is not None


def test_upsert_foreshadowing():
    mock_client = MockChromaClient()
    retriever = LongFormContextRetriever(chroma_client=mock_client)
    
    entity = ForeshadowingEntity.create(
        description="主人公の出生の秘密",
        introduced_in_ep=1,
        target_resolution_ep=12,
        related_characters=["主人公", "実の父"],
        keywords=["出生", "秘密", "父"],
    )
    
    retriever.upsert_foreshadowing(1, entity)
    
    # コレクションが作成されているか確認
    assert 1 in retriever._collections


def test_get_pending_foreshadowings():
    mock_client = MockChromaClient()
    retriever = LongFormContextRetriever(chroma_client=mock_client)
    
    # 複数の伏線を登録
    entities = [
        ForeshadowingEntity.create(
            description="伏線A",
            introduced_in_ep=1,
            target_resolution_ep=5,
        ),
        ForeshadowingEntity.create(
            description="伏線B",
            introduced_in_ep=2,
            target_resolution_ep=10,
        ),
        ForeshadowingEntity.create(
            description="伏線C（回収済み）",
            introduced_in_ep=1,
            target_resolution_ep=3,
        ),
    ]
    
    for e in entities:
        retriever.upsert_foreshadowing(1, e)
    
    # 3番目を回収済みに
    retriever.resolve_foreshadowing(1, entities[2].foreshadow_id, 3)
    
    # 第4話時点での未回収伏線取得
    pending = retriever.get_pending_foreshadowings(1, current_ep=4)
    
    # 伏線Cは回収済み、伏線Aは目標5話（現在4話なので含まれる）、伏線Bは目標10話
    assert len(pending) == 2
    assert all(e.status == ForeshadowingStatus.OPEN for e in pending)
    
    # 目標話数が近い順（伏線Aが先）
    assert pending[0].foreshadow_id == entities[0].foreshadow_id


def test_search_relevant_context():
    mock_client = MockChromaClient()
    retriever = LongFormContextRetriever(chroma_client=mock_client)
    
    entity = ForeshadowingEntity.create(
        description="古代遺跡で見つかった紋章",
        introduced_in_ep=3,
        target_resolution_ep=8,
        keywords=["遺跡", "紋章", "古代"],
    )
    retriever.upsert_foreshadowing(1, entity)
    
    results = retriever.search_relevant_context(
        book_id=1,
        plot_summary="主人公が古い遺跡で紋章を発見する",
        top_k=3,
    )
    
    assert len(results) > 0
    assert "entity" in results[0]
    assert "similarity" in results[0]


def test_retrieve_writing_context():
    mock_client = MockChromaClient()
    retriever = LongFormContextRetriever(chroma_client=mock_client)
    
    entity = ForeshadowingEntity.create(
        description="魔王の弱点は光の剣",
        introduced_in_ep=1,
        target_resolution_ep=10,
        related_characters=["主人公", "魔王"],
        keywords=["魔王", "弱点", "光の剣"],
    )
    retriever.upsert_foreshadowing(1, entity)
    
    context = retriever.retrieve_writing_context(
        book_id=1,
        current_ep=5,
        plot_outline="主人公が魔王と対決する",
        character_names=["主人公", "魔王"],
    )
    
    assert "pending_foreshadowings" in context
    assert "relevant_foreshadowings" in context
    assert "subgraph_edges" in context
    assert "character_states" in context
    assert context["current_episode"] == 5


def test_format_context_for_prompt():
    mock_client = MockChromaClient()
    retriever = LongFormContextRetriever(chroma_client=mock_client)
    
    entity = ForeshadowingEntity.create(
        description="テスト伏線",
        introduced_in_ep=1,
        target_resolution_ep=5,
        related_characters=["A", "B"],
        keywords=["キーワード1", "キーワード2"],
    )
    retriever.upsert_foreshadowing(1, entity)
    
    context = retriever.retrieve_writing_context(
        book_id=1,
        current_ep=3,
        plot_outline="テスト",
        character_names=["A"],
    )
    
    formatted = retriever.format_context_for_prompt(context)
    
    assert "## 本話で意識・回収すべき伏線・設定" in formatted
    assert "回収必須の伏線" in formatted
    assert "テスト伏線" in formatted
    assert "第1話提示" in formatted
    assert "第5話回収予定" in formatted


def test_resolve_foreshadowing():
    mock_client = MockChromaClient()
    retriever = LongFormContextRetriever(chroma_client=mock_client)
    
    entity = ForeshadowingEntity.create(
        description="回収される伏線",
        introduced_in_ep=1,
        target_resolution_ep=5,
    )
    retriever.upsert_foreshadowing(1, entity)
    
    # 回収前
    pending_before = retriever.get_pending_foreshadowings(1, current_ep=3)
    assert len(pending_before) == 1
    assert pending_before[0].status == ForeshadowingStatus.OPEN
    
    # 回収実行
    result = retriever.resolve_foreshadowing(1, entity.foreshadow_id, 5)
    assert result is True
    
    # 回収後
    pending_after = retriever.get_pending_foreshadowings(1, current_ep=6)
    assert len(pending_after) == 0


def test_resolve_nonexistent_foreshadowing():
    mock_client = MockChromaClient()
    retriever = LongFormContextRetriever(chroma_client=mock_client)
    
    result = retriever.resolve_foreshadowing(1, "nonexistent", 5)
    assert result is False


def test_subgraph_extraction():
    """サブグラフ抽出のテスト"""
    # テスト用グラフ構築
    G = nx.Graph()
    G.add_edge("主人公", "師匠", relation="師弟", weight=1.0)
    G.add_edge("師匠", "古い友人", relation="友人", weight=0.8)
    G.add_edge("主人公", "ライバル", relation="ライバル", weight=0.9)
    G.add_edge("ライバル", "魔王", relation="部下", weight=0.7)
    G.add_edge("魔王", "四天王", relation="配下", weight=0.6)
    
    # 主人公から2ホップ以内を抽出
    edges = extract_character_subgraph(G, ["主人公"], max_hops=2)
    
    # 主人公-師匠、主人公-ライバル、師匠-古い友人、ライバル-魔王 が含まれるはず
    assert len(edges) >= 3
    
    sources = {e["source"] for e in edges}
    targets = {e["target"] for e in edges}
    all_nodes = sources | targets
    
    assert "主人公" in all_nodes
    assert "師匠" in all_nodes
    assert "ライバル" in all_nodes
    # 2ホップなので魔王も含まれる
    assert "魔王" in all_nodes


def test_build_knowledge_graph():
    characters = [
        {"name": "主人公", "role": "hero"},
        {"name": "ヒロイン", "role": "heroine"},
    ]
    settings = [
        {"name": "魔法学園", "category": "location"},
        {"name": "光の剣", "category": "item"},
    ]
    relationships = [
        {"source": "主人公", "target": "ヒロイン", "relation": "恋人", "weight": 1.0},
        {"source": "主人公", "target": "光の剣", "relation": "所持", "weight": 0.8},
    ]
    
    G = build_knowledge_graph_from_entities(characters, settings, relationships)
    
    assert G.has_node("主人公")
    assert G.has_node("ヒロイン")
    assert G.has_node("魔法学園")
    assert G.has_node("光の剣")
    assert G.has_edge("主人公", "ヒロイン")
    assert G.has_edge("主人公", "光の剣")
    
    edge_data = G.get_edge_data("主人公", "ヒロイン")
    assert edge_data["relation"] == "恋人"


def test_knowledge_graph_extractor():
    G = nx.Graph()
    G.add_edge("A", "B", relation="友人", weight=1.0)
    G.add_edge("B", "C", relation="敵", weight=0.5)
    G.add_edge("C", "D", relation="家族", weight=1.0)
    
    extractor = KnowledgeGraphExtractor(G)
    
    # Aからの直接関係
    relations = extractor.get_character_relations("A")
    assert len(relations) == 1
    assert relations[0]["related_to"] == "B"
    assert relations[0]["relation"] == "友人"
    
    # パス探索
    path = extractor.find_path("A", "D")
    assert path == ["A", "B", "C", "D"]
    
    # 連結成分
    components = extractor.get_connected_components()
    assert len(components) == 1


def test_subgraph_with_max_hops():
    G = nx.Graph()
    G.add_edge("A", "B", relation="1")
    G.add_edge("B", "C", relation="2")
    G.add_edge("C", "D", relation="3")
    G.add_edge("D", "E", relation="4")
    
    # 1ホップ
    edges_1 = extract_character_subgraph(G, ["A"], max_hops=1)
    nodes_1 = set()
    for e in edges_1:
        nodes_1.add(e["source"])
        nodes_1.add(e["target"])
    assert nodes_1 == {"A", "B"}
    
    # 2ホップ
    edges_2 = extract_character_subgraph(G, ["A"], max_hops=2)
    nodes_2 = set()
    for e in edges_2:
        nodes_2.add(e["source"])
        nodes_2.add(e["target"])
    assert nodes_2 == {"A", "B", "C"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])