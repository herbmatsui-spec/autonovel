"""Layer 2: Apache AGE 2-Hop Subgraph Extractor & Edge Pruner (Steps 27 & 28)."""
from __future__ import annotations

import logging
from typing import Any, List, Dict, Set
from sqlalchemy.orm import Session

from src.services.compression.models import SubgraphLayerOutput

logger = logging.getLogger(__name__)

RELATION_WEIGHTS = {
    "対立": 1.5,
    "敵対": 1.5,
    "親子": 1.5,
    "主従": 1.4,
    "師弟": 1.4,
    "所属": 1.3,
    "所持": 1.2,
    "使用": 1.2,
    "同行": 1.1,
    "協力": 1.1,
    "関連": 1.0,
    "目撃": 0.8,
    "雑談": 0.7,
}


class Layer2SubgraphExtractor:
    """Extracts 2-hop neighborhood subgraph and prunes low-relevance edges/nodes."""

    def __init__(
        self,
        max_hops: int = 2,
        relevance_threshold: float = 0.5,
        max_nodes: int = 30,
        max_edges: int = 50,
        age_client: Any = None,
    ) -> None:
        self.max_hops = max_hops
        self.relevance_threshold = relevance_threshold
        self.max_nodes = max_nodes
        self.max_edges = max_edges
        self.age_client = age_client

    def extract_from_age(
        self,
        session: Session,
        graph_name: str,
        seed_names: list[str],
        keyword_scores: dict[str, float] | None = None,
    ) -> SubgraphLayerOutput:
        """Step 27: Query Apache AGE for 2-hop neighborhood using Cypher."""
        if not seed_names or not self.age_client or not graph_name:
            return SubgraphLayerOutput(
                nodes=[],
                edges=[],
                seed_entity_names=seed_names,
                pruned_edge_count=0,
                stats={"source": "age_empty"},
            )

        # AGE Cypher クエリの構築
        safe_names = [n.replace("'", "\\'") for n in seed_names if n]
        if not safe_names:
            return SubgraphLayerOutput(seed_entity_names=seed_names)

        in_clause = ", ".join(f"'{n}'" for n in safe_names)
        cypher = f"""
            MATCH (n)
            WHERE n.name IN [{in_clause}]
            OPTIONAL MATCH (n)-[r*1..{self.max_hops}]-(m)
            RETURN n.name, labels(n), properties(n), m.name, labels(m), properties(m),
                   [x IN r | type(x)] as rel_types
            LIMIT 100
        """

        raw_nodes: dict[str, dict[str, Any]] = {}
        raw_edges: list[dict[str, Any]] = []

        try:
            from sqlalchemy import text
            from src.services.age_client import _parse_agtype

            sql = f"SELECT * FROM cypher('{graph_name}', $$ {cypher} $$) as (n_name agtype, n_labels agtype, n_props agtype, m_name agtype, m_labels agtype, m_props agtype, rel_types agtype);"
            result = session.execute(text(sql))

            for row in result:
                n_name = str(row[0]).strip('"') if row[0] is not None else None
                m_name = str(row[3]).strip('"') if row[3] is not None else None

                if n_name and n_name not in raw_nodes:
                    raw_nodes[n_name] = {
                        "id": n_name,
                        "name": n_name,
                        "labels": _parse_agtype(row[1]) if row[1] else [],
                        "properties": _parse_agtype(row[2]) if row[2] else {},
                        "hop": 0,
                    }

                if m_name and m_name not in raw_nodes:
                    raw_nodes[m_name] = {
                        "id": m_name,
                        "name": m_name,
                        "labels": _parse_agtype(row[4]) if row[4] else [],
                        "properties": _parse_agtype(row[5]) if row[5] else {},
                        "hop": 1,
                    }

                if n_name and m_name:
                    rel_types = _parse_agtype(row[6]) if row[6] else ["related"]
                    rel_type = rel_types[0] if isinstance(rel_types, list) and rel_types else "related"
                    raw_edges.append({
                        "source": n_name,
                        "target": m_name,
                        "type": str(rel_type),
                        "hop": len(rel_types) if isinstance(rel_types, list) else 1,
                    })

        except Exception as e:
            logger.warning(f"AGE Cypher query failed: {e}")

        # Step 28: エッジプリューニングの適用
        return self.prune_subgraph(
            nodes=list(raw_nodes.values()),
            edges=raw_edges,
            seed_names=seed_names,
            keyword_scores=keyword_scores or {},
        )

    def extract_from_memory(
        self,
        entities: list[dict[str, Any]],
        relations: list[dict[str, Any]],
        seed_names: list[str],
        keyword_scores: dict[str, float] | None = None,
    ) -> SubgraphLayerOutput:
        """Step 27: In-memory BFS 2-hop graph traversal (fallback / unit test)."""
        if not entities or not seed_names:
            return SubgraphLayerOutput(
                nodes=[],
                edges=[],
                seed_entity_names=seed_names,
                pruned_edge_count=0,
                stats={"source": "memory_empty"},
            )

        # 1. シードノード特定
        seed_node_ids = set()
        node_by_id = {e.get("id", e.get("name")): e for e in entities}
        name_to_id = {e.get("name", ""): e.get("id", e.get("name")) for e in entities}

        for s in seed_names:
            s_lower = s.lower()
            for e in entities:
                ename = e.get("name", "").lower()
                aliases = [a.lower() for a in e.get("aliases", [])]
                if s_lower == ename or s_lower in aliases or ename in s_lower:
                    eid = e.get("id", e.get("name"))
                    if eid:
                        seed_node_ids.add(eid)

        if not seed_node_ids:
            return SubgraphLayerOutput(
                nodes=[],
                edges=[],
                seed_entity_names=seed_names,
                pruned_edge_count=0,
                stats={"source": "no_seeds_found"},
            )

        # 2. 隣接リスト構築
        adj: dict[str, list[tuple[str, dict]]] = {}
        for r in relations:
            src = r.get("source")
            tgt = r.get("target")
            if src and tgt:
                adj.setdefault(src, []).append((tgt, r))
                adj.setdefault(tgt, []).append((src, r))

        # 3. BFSで max_hops 以内を探索
        visited_nodes: set[str] = set(seed_node_ids)
        current_layer: set[str] = set(seed_node_ids)
        node_hops: dict[str, int] = {nid: 0 for nid in seed_node_ids}
        collected_edges: list[dict[str, Any]] = []

        for hop in range(1, self.max_hops + 1):
            next_layer = set()
            for u in current_layer:
                for v, rel in adj.get(u, []):
                    if v not in visited_nodes:
                        visited_nodes.add(v)
                        next_layer.add(v)
                        node_hops[v] = hop
                    collected_edges.append({
                        "source": rel.get("source"),
                        "target": rel.get("target"),
                        "type": rel.get("type", "related"),
                        "hop": hop,
                    })
            current_layer = next_layer
            if not current_layer:
                break

        # 重複エッジ除去
        unique_edges = []
        seen_edge_keys = set()
        for e in collected_edges:
            pair = tuple(sorted([e["source"], e["target"]]))
            key = (pair, e["type"])
            if key not in seen_edge_keys:
                seen_edge_keys.add(key)
                unique_edges.append(e)

        nodes_list = []
        for nid in visited_nodes:
            if nid in node_by_id:
                n = dict(node_by_id[nid])
                n["hop"] = node_hops.get(nid, 2)
                nodes_list.append(n)

        # Step 28: エッジプリューニングの適用
        return self.prune_subgraph(
            nodes=nodes_list,
            edges=unique_edges,
            seed_names=seed_names,
            keyword_scores=keyword_scores or {},
        )

    def prune_subgraph(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        seed_names: list[str],
        keyword_scores: dict[str, float],
    ) -> SubgraphLayerOutput:
        """Step 28: Prune edges and nodes based on hop distance and relation relevance."""
        initial_edge_count = len(edges)

        # エッジスコアの計算:
        # score = (hop_weight) * (relation_type_weight) * (seed_match_factor)
        scored_edges = []
        for edge in edges:
            hop = edge.get("hop", 1)
            hop_decay = 1.0 if hop == 1 else 0.5

            rel_type = edge.get("type", "related")
            rel_weight = 1.0
            for r_key, r_w in RELATION_WEIGHTS.items():
                if r_key in rel_type:
                    rel_weight = max(rel_weight, r_w)

            src = str(edge.get("source", ""))
            tgt = str(edge.get("target", ""))

            # シード関連加点
            seed_boost = 1.0
            if any(s.lower() in src.lower() or s.lower() in tgt.lower() for s in seed_names):
                seed_boost = 1.3

            score = hop_decay * rel_weight * seed_boost
            edge_copy = dict(edge)
            edge_copy["relevance_score"] = round(score, 3)
            scored_edges.append(edge_copy)

        # 閾値以上を保持
        pruned_edges = [e for e in scored_edges if e["relevance_score"] >= self.relevance_threshold]
        if len(pruned_edges) > self.max_edges:
            pruned_edges.sort(key=lambda x: x["relevance_score"], reverse=True)
            pruned_edges = pruned_edges[:self.max_edges]

        # 残ったエッジに接続しているノードを収集
        active_node_ids = set()
        for e in pruned_edges:
            active_node_ids.add(e["source"])
            active_node_ids.add(e["target"])

        # シードノードは必ず残す
        for n in nodes:
            n_name = n.get("name", "")
            if any(s.lower() in n_name.lower() for s in seed_names):
                active_node_ids.add(n.get("id", n_name))

        filtered_nodes = [n for n in nodes if n.get("id", n.get("name")) in active_node_ids]
        if len(filtered_nodes) > self.max_nodes:
            filtered_nodes.sort(key=lambda x: x.get("hop", 2))
            filtered_nodes = filtered_nodes[:self.max_nodes]

        removed_edges = initial_edge_count - len(pruned_edges)

        return SubgraphLayerOutput(
            nodes=filtered_nodes,
            edges=pruned_edges,
            seed_entity_names=seed_names,
            pruned_edge_count=max(0, removed_edges),
            stats={
                "initial_nodes": len(nodes),
                "retained_nodes": len(filtered_nodes),
                "initial_edges": initial_edge_count,
                "retained_edges": len(pruned_edges),
                "pruned_edge_count": max(0, removed_edges),
            },
        )


__all__ = ["Layer2SubgraphExtractor", "RELATION_WEIGHTS"]
