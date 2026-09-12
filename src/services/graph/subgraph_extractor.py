from __future__ import annotations

from typing import Any
import networkx as nx


def extract_character_subgraph(
    graph: nx.Graph,
    character_names: list[str],
    max_hops: int = 2,
) -> list[dict[str, Any]]:
    """
    知識グラフから指定キャラクターの関連サブグラフを抽出
    
    Args:
        graph: NetworkXグラフ
        character_names: 対象キャラクター名リスト
        max_hops: 最大ホップ数（デフォルト2）
    
    Returns:
        関連エッジのリスト
    """
    if not character_names:
        return []
    
    # グラフにノードが存在するか確認
    existing_nodes = [n for n in character_names if graph.has_node(n)]
    if not existing_nodes:
        return []
    
    subgraph_nodes = set(existing_nodes)
    
    # 指定ホップ数以内のノードを追加
    for _ in range(max_hops):
        new_nodes = set()
        for node in subgraph_nodes:
            if graph.has_node(node):
                new_nodes.update(graph.neighbors(node))
        subgraph_nodes.update(new_nodes)
    
    # サブグラフのエッジを抽出
    edges = []
    subgraph = graph.subgraph(subgraph_nodes)
    
    for u, v, data in subgraph.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "relation": data.get("relation", "related"),
            "weight": data.get("weight", 1.0),
            "metadata": data.get("metadata", {}),
        })
    
    return edges


def build_knowledge_graph_from_entities(
    characters: list[dict[str, Any]],
    settings: list[dict[str, Any]],
    relationships: list[dict[str, Any]] = None,
) -> nx.Graph:
    """エンティティ情報から知識グラフを構築"""
    G = nx.Graph()
    
    # キャラクターノード追加
    for char in characters:
        name = char.get("name", "")
        attrs = {k: v for k, v in char.items() if k != "name"}
        G.add_node(name, type="character", **attrs)
    
    # 設定ノード追加
    for setting in settings:
        name = setting.get("name", "")
        attrs = {k: v for k, v in setting.items() if k != "name"}
        G.add_node(name, type="setting", **attrs)
    
    # 関係エッジ追加
    if relationships:
        for rel in relationships:
            G.add_edge(
                rel["source"],
                rel["target"],
                relation=rel.get("relation", "related"),
                weight=rel.get("weight", 1.0),
                metadata=rel.get("metadata", {}),
            )
    
    return G


class KnowledgeGraphExtractor:
    """知識グラフからのサブグラフ抽出ユーティリティ"""
    
    def __init__(self, graph: nx.Graph):
        self.graph = graph
    
    def extract_subgraph(
        self,
        character_names: list[str],
        max_hops: int = 2,
        min_weight: float = 0.0,
    ) -> list[dict[str, Any]]:
        return extract_character_subgraph(self.graph, character_names, max_hops)
    
    def get_character_relations(self, character_name: str) -> list[dict[str, Any]]:
        """特定キャラクターの直接的な関係を取得"""
        if not self.graph.has_node(character_name):
            return []
        
        relations = []
        for neighbor in self.graph.neighbors(character_name):
            edge_data = self.graph.get_edge_data(character_name, neighbor)
            relations.append({
                "character": character_name,
                "related_to": neighbor,
                "relation": edge_data.get("relation", "related"),
                "weight": edge_data.get("weight", 1.0),
            })
        return relations
    
    def find_path(self, source: str, target: str) -> list[str] | None:
        """2キャラクター間の最短パスを探索"""
        try:
            return nx.shortest_path(self.graph, source, target)
        except nx.NetworkXNoPath:
            return None
    
    def get_connected_components(self) -> list[list[str]]:
        """連結成分を取得（孤立したグループの検出用）"""
        return list(nx.connected_components(self.graph))