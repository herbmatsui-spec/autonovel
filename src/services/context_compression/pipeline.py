# src/services/context_compression/pipeline.py
"""4層コンテキスト圧縮パイプライン統合クラス"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging
import re
from collections import Counter

from src.utils.context_compression_config import (
    CompressionConfig,
    Layer1Config,
    Layer2Config,
    Layer3Config,
    Layer4Config,
    get_compression_config,
)
from src.services.context_compression.keyphrase_extractors import (
    KeyphraseExtractor,
    create_extractor,
)

logger = logging.getLogger(__name__)


@dataclass
class CompressionResult:
    """圧縮結果"""
    layer1_keyphrases: List[Tuple[str, float]] = field(default_factory=list)
    layer2_subgraph: Dict[str, Any] = field(default_factory=dict)
    layer3_abstracted: Dict[str, List[Dict]] = field(default_factory=dict)
    layer4_trimmed: str = ""
    stats: Dict[str, Any] = field(default_factory=dict)


class SubgraphExtractor:
    """第2層: サブグラフ抽出・プリューニング"""

    def __init__(self, config: Layer2Config):
        self.config = config

    def extract_subgraph(
        self,
        entities: List[Dict],
        relations: List[Dict],
        keyphrases: List[Tuple[str, float]],
    ) -> Dict[str, Any]:
        """サブグラフ抽出・プリューニング"""
        if not entities or not relations:
            return {"nodes": [], "edges": [], "stats": {"pruned_nodes": 0}}

        # 1. キーフレーズに関連するシードノード特定
        seed_node_ids = self._find_seed_nodes(entities, keyphrases)

        if not seed_node_ids:
            return {"nodes": [], "edges": [], "stats": {"pruned_nodes": 0}}

        # 2. 隣接リスト構築
        adj = self._build_adjacency(relations)

        # 3. BFSで max_hops 以内のノード抽出
        visited = set()
        current_layer = set(seed_node_ids)
        all_visited = set(seed_node_ids)
        node_distances = {nid: 0 for nid in seed_node_ids}

        for hop in range(1, self.config.max_hops + 1):
            next_layer = set()
            for nid in current_layer:
                for neighbor in adj.get(nid, []):
                    if neighbor not in all_visited:
                        all_visited.add(neighbor)
                        next_layer.add(neighbor)
                        node_distances[neighbor] = hop
            current_layer = next_layer
            if not current_layer:
                break

        # 4. 抽出されたノード・エッジ収集
        subgraph_nodes = [e for e in entities if e.get("id") in all_visited]
        subgraph_edges = [r for r in relations
                         if r.get("source") in all_visited and r.get("target") in all_visited]

        # 5. 関連性スコア計算・プリューニング
        scored_nodes = list(self._score_relevance(subgraph_nodes, keyphrases, node_distances))
        pruned_nodes = [
            n for n in scored_nodes
            if n["relevance_score"] >= self.config.relevance_threshold
        ]

        # 最大ノード数制限
        if len(pruned_nodes) > self.config.max_nodes:
            pruned_nodes = sorted(pruned_nodes, key=lambda x: x["relevance_score"], reverse=True)[:self.config.max_nodes]

        pruned_node_ids = {n["id"] for n in pruned_nodes}
        pruned_edges = [e for e in subgraph_edges
                       if e.get("source") in pruned_node_ids and e.get("target") in pruned_node_ids]

        return {
            "nodes": pruned_nodes,
            "edges": pruned_edges,
            "stats": {
                "original_nodes": len(entities),
                "extracted_nodes": len(subgraph_nodes),
                "pruned_nodes": len(pruned_nodes),
                "edges": len(pruned_edges),
            }
        }

    def _find_seed_nodes(self, entities: List[Dict], keyphrases: List[Tuple[str, float]]) -> set:
        """キーフレーズに関連するエンティティIDをシードとして特定"""
        seed_ids = set()
        # キーフレーズを単語レベルで分割してマッチング
        kp_words = set()
        for kp, _ in keyphrases:
            # キーフレーズを単語レベルで分割してマッチング
            for word in kp:
                if len(word) >= 2:
                    kp_words.add(word)
            kp_words.add(kp)

        for entity in entities:
            name = entity.get("name", "").lower()
            aliases = [a.lower() for a in entity.get("aliases", [])]
            all_names = [name] + aliases

            for kp in kp_words:
                for ename in all_names:
                    if kp in ename or ename in kp:
                        eid = entity.get("id")
                        if eid:
                            seed_ids.add(eid)
                            break

        return seed_ids

    def _build_adjacency(self, relations: List[Dict]) -> Dict[str, set]:
        """隣接リスト構築"""
        adj = {}
        for rel in relations:
            src = rel.get("source")
            tgt = rel.get("target")
            if src and tgt:
                if src not in adj:
                    adj[src] = set()
                if tgt not in adj:
                    adj[tgt] = set()
                adj[src].add(tgt)
                adj[tgt].add(src)  # 無向グラフとして扱う
        return adj

    def _score_relevance(
        self,
        nodes: List[Dict],
        keyphrases: List[Tuple[str, float]],
        distances: Dict[str, int]
    ) -> List[Dict]:
        """関連性スコア計算"""
        for node in nodes:
            score = 0.0
            name = node.get("name", "").lower()
            aliases = [a.lower() for a in node.get("aliases", [])]
            all_names = [node.get("name", "").lower()] + [a.lower() for a in node.get("aliases", [])]

            # キーフレーズとのマッチング
            for kp, kp_score in keyphrases:
                kp_lower = kp.lower()
                for ename in all_names:
                    if kp_lower in ename or ename in kp_lower:
                        score += kp_score * 2.0  # 直接マッチは高スコア
                        break

            # 距離による減衰
            dist = distances.get(node.get("id"), 3)
            if dist == 1:
                score *= 1.0
            elif dist == 2:
                score *= 0.5
            else:
                score *= 0.25

            # エンティティタイプによる重み付け
            entity_type = node.get("type", "").lower()
            type_weights = {
                "character": 1.5,
                "location": 1.2,
                "item": 1.0,
                "organization": 1.2,
                "event": 1.3,
            }
            score *= type_weights.get(entity_type, 1.0)

            node_copy = node.copy()
            node_copy["relevance_score"] = score
            yield node_copy


class AbstractionLayer:
    """第3層: 抽象化・カテゴリ化"""

    def __init__(self, config: Layer3Config):
        self.config = config
        self._summarizer = None
        self._load_model()

    def _load_model(self):
        """要約モデル遅延読み込み"""
        try:
            from transformers import pipeline
            self._summarizer = pipeline(
                "summarization",
                model=self.config.model,
                device=-1  # CPU
            )
        except Exception as e:
            logger.warning(f"Failed to load summarization model: {e}")
            self._summarizer = None

    def abstract_facts(
        self,
        subgraph: Dict[str, Any],
        raw_text: str,
    ) -> Dict[str, List[Dict]]:
        """サブグラフの事実を抽象化・カテゴリ化"""
        # まず要約モデルを試す
        if self._summarizer:
            try:
                return self._abstract_with_model(subgraph)
            except Exception as e:
                logger.warning(f"Model-based abstraction failed, using fallback: {e}")

        # フォールバック: ルールベースの抽象化
        return self._abstract_with_rules(subgraph)

    def _abstract_with_model(self, subgraph: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """要約モデルを使用した抽象化（将来の拡張用）"""
        # 将来的にモデルが利用可能になった時用
        return self._abstract_with_rules(subgraph)

    def _abstract_with_rules(self, subgraph: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """ルールベースの抽象化（モデル不要）"""
        categorized = {cat: [] for cat in self.config.abstraction_categories}

        # ノードから事実抽出
        for node in subgraph.get("nodes", []):
            name = node.get("name", "")
            node_type = node.get("type", "")

            if node.get("type") == "character":
                self._add_fact(categorized, "主要キャラ", f"{node.get('name', '')}が登場")
            elif node.get("type") == "location":
                self._add_fact(categorized, "地理・地形", f"{node.get('name', '')}が舞台")
            elif node.get("type") == "item":
                self._add_fact(categorized, "アイテム・装備", f"{node.get('name', '')}が登場")
            elif node.get("type") == "organization":
                self._add_fact(categorized, "組織・派閥", f"{node.get('name', '')}が関与")

        # エッジから関係事実抽出
        for edge in subgraph.get("edges", []):
            rel_type = edge.get("type", "related")
            src = edge.get("source_name", edge.get("source", ""))
            tgt = edge.get("target_name", edge.get("target", ""))

            if "敵" in rel_type or "対立" in rel_type:
                self._add_fact(categorized, "伏線", f"{edge.get('source_name', edge.get('source', ''))}と{edge.get('target_name', edge.get('target', ''))}は{rel_type}関係")
            elif "同行" in rel_type or "協力" in rel_type:
                self._add_fact(categorized, "組織・派閥", f"{edge.get('source_name', edge.get('source', ''))}と{edge.get('target_name', edge.get('target', ''))}は{rel_type}")
            elif "所持" in rel_type or "使用" in rel_type:
                self._add_fact(categorized, "アイテム・装備", f"{edge.get('source_name', edge.get('source', ''))}が{edge.get('target_name', edge.get('target', ''))}を{rel_type}")

        return {cat: facts for cat, facts in categorized.items() if facts}

    def _build_categorized_dict(self, subgraph: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """カテゴリ辞書を構築"""
        categorized = {cat: [] for cat in self.config.abstraction_categories}

        # ノードから事実抽出
        for node in subgraph.get("nodes", []):
            name = node.get("name", "")
            node_type = node.get("type", "")

            if node.get("type") == "character":
                self._add_fact(categorized, "主要キャラ", f"{node.get('name', '')}が登場")
            elif node.get("type") == "location":
                self._add_fact(categorized, "地理・地形", f"{node.get('name', '')}が舞台")
            elif node.get("type") == "item":
                self._add_fact(categorized, "アイテム・装備", f"{node.get('name', '')}が登場")
            elif node.get("type") == "organization":
                self._add_fact(categorized, "組織・派閥", f"{node.get('name', '')}が関与")

        # エッジから関係事実抽出
        for edge in subgraph.get("edges", []):
            rel_type = edge.get("type", "related")
            src = edge.get("source_name", edge.get("source", ""))
            tgt = edge.get("target_name", edge.get("target", ""))

            if "敵" in rel_type or "対立" in rel_type:
                self._add_fact(categorized, "伏線", f"{edge.get('source_name', edge.get('source', ''))}と{edge.get('target_name', edge.get('target', ''))}は{rel_type}関係")
            elif "同行" in rel_type or "協力" in rel_type:
                self._add_fact(categorized, "組織・派閥", f"{edge.get('source_name', edge.get('source', ''))}と{edge.get('target_name', edge.get('target', ''))}は{rel_type}")
            elif "所持" in rel_type or "使用" in rel_type:
                self._add_fact(categorized, "アイテム・装備", f"{edge.get('source_name', edge.get('source', ''))}が{edge.get('target_name', edge.get('target', ''))}を{rel_type}")

        return {cat: facts for cat, facts in categorized.items() if facts}

    def _add_fact(self, categorized: Dict[str, List[Dict]], category: str, content: str):
        """事実をカテゴリに追加"""
        if category in self.config.abstraction_categories:
            categorized[category].append({"content": content, "category": category})


class TrimmingLayer:
    """第4層: 重要度ベース動的トリミング"""

    def __init__(self, config: Layer4Config):
        self.config = config
        try:
            import tiktoken
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._tokenizer = None
            logger.warning("tiktoken not available, using character count approximation")

    def count_tokens(self, text: str) -> int:
        """トークン数カウント"""
        if self._tokenizer:
            return len(self._tokenizer.encode(text))
        # 概算: 日本語は1文字≒1.5トークン、英語は1単語≒1.3トークン
        return int(len(text) * 1.5)

    def trim(
        self,
        abstracted: Dict[str, List[Dict]],
        raw_text: str,
        keyphrases: List[Tuple[str, float]],
    ) -> str:
        """重要度ベース動的トリミング"""
        # 1. 各カテゴリの事実に重要度スコア付与
        all_facts = []
        for cat, facts in abstracted.items():
            for fact in facts:
                score = self._calculate_importance(fact, keyphrases)
                all_facts.append({
                    "category": cat,
                    "content": fact["content"],
                    "score": score,
                })

        # 2. 必須保持カテゴリの事実を最優先
        preserved = []
        optional = []
        for fact in all_facts:
            if fact["category"] in self.config.preserve_categories:
                fact["mandatory"] = True
                preserved.append(fact)
            else:
                fact["mandatory"] = False
                optional.append(fact)

        # 3. 任意事実はスコア順ソート
        optional.sort(key=lambda x: x["score"], reverse=True)

        # 4. トークン予算内に収まるよう選択
        selected = list(preserved)  # 必須は全採用
        current_tokens = sum(self.count_tokens(f["content"]) for f in preserved)
        token_budget = self.config.max_tokens - current_tokens

        for fact in optional:
            fact_tokens = self.count_tokens(fact["content"])
            if fact_tokens <= token_budget:
                selected.append(fact)
                token_budget -= fact_tokens
            else:
                break

        # 4. 閾値未満も除外（任意事実のみ）
        selected = [f for f in selected if f["mandatory"] or f["score"] >= self.config.importance_threshold]

        # 5. 自然な文章として結合
        return self._format_output(selected)

    def _calculate_importance(self, fact: Dict, keyphrases: List[Tuple[str, float]]) -> float:
        """事実の重要度計算"""
        content = fact.get("content", "").lower()
        cat = fact.get("category", "")

        base_score = 0.5

        # カテゴリによる基本スコア
        cat_weights = {
            "主要キャラ": 1.5,
            "核心設定": 1.5,
            "伏線": 1.3,
            "武術スキル": 1.2,
            "魔法システム": 1.1,
            "統治システム": 1.1,
            "組織・派閥": 1.0,
            "地理・地形": 0.9,
            "歴史・年表": 0.9,
            "アイテム・装備": 0.8,
            "種族・血統": 0.8,
        }
        base_score *= cat_weights.get(fact.get("category", ""), 1.0)

        # キーフレーズとのマッチング
        content_lower = fact.get("content", "").lower()
        for kp, kp_score in keyphrases:
            if kp.lower() in content_lower:
                base_score += kp_score * 0.5

        return min(base_score, 2.0)

    def _format_output(self, selected: List[Dict]) -> str:
        """選択された事実を自然な文章として結合"""
        if not selected:
            return ""

        # カテゴリごとにグループ化
        by_cat = {}
        for f in selected:
            cat = f["category"]
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(f["content"])

        # 重要カテゴリ順で出力
        cat_order = [
            "主要キャラ", "核心設定", "伏線",
            "武術スキル", "魔法システム", "統治システム",
            "組織・派閥", "地理・地形", "歴史・年表",
            "アイテム・装備", "種族・血統",
        ]

        parts = []
        for cat in cat_order:
            if cat in by_cat:
                parts.append(f"【{cat}】")
                for content in by_cat[cat]:
                    parts.append(f"  - {content}")
                parts.append("")

        return "\n".join(parts).strip()


class ContextCompressionPipeline:
    """4層コンテキスト圧縮パイプライン統合クラス"""

    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or get_compression_config()

        if not self.config.enabled:
            logger.info("Context compression is disabled")
            self._enabled = False
            return

        self._enabled = True

        # 各層の初期化
        self.layer1_extractor = create_extractor(self.config.layer1.method)
        self.layer2_extractor = SubgraphExtractor(self.config.layer2)
        self.layer3_abstractor = AbstractionLayer(self.config.layer3)
        self.layer4_trimmer = TrimmingLayer(self.config.layer4)

        logger.info("ContextCompressionPipeline initialized")

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def compress(
        self,
        raw_text: str,
        entities: List[Dict],
        relations: List[Dict],
        scene_context: Optional[Dict] = None,
    ) -> CompressionResult:
        """4層圧縮実行"""
        if not self._enabled:
            return CompressionResult(
                layer4_trimmed=raw_text,
                stats={"enabled": False, "compression_ratio": 1.0}
            )

        start_time = __import__('time').time()

        # Layer 1: キーフレーズ抽出
        keyphrases = self.layer1_extractor.extract(
            raw_text,
            self.config.layer1.top_k,
            self.config.layer1.min_score
        )

        # Layer 2: サブグラフ抽出
        keyphrases_list = list(keyphrases) if not isinstance(keyphrases, list) else keyphrases
        subgraph = self.layer2_extractor.extract_subgraph(
            entities,
            relations,
            keyphrases_list
        )

        # Layer 3: 抽象化
        abstracted = self.layer3_abstractor.abstract_facts(subgraph, raw_text)

        # Layer 4: トリミング
        trimmed = self.layer4_trimmer.trim(abstracted, raw_text, keyphrases_list)

        elapsed = __import__('time').time() - start_time

        # 統計計算
        original_tokens = self._count_tokens(raw_text)
        compressed_tokens = self._count_tokens(trimmed)
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0

        stats = {
            "enabled": True,
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "compression_ratio": compression_ratio,
            "layer1_keyphrases": len(keyphrases) if isinstance(keyphrases, list) else len(keyphrases_list),
            "layer2_nodes": subgraph.get("stats", {}).get("pruned_nodes", 0),
            "layer3_categories": len([k for k, v in abstracted.items() if v]),
            "elapsed_sec": elapsed,
        }

        return CompressionResult(
            layer1_keyphrases=keyphrases_list,
            layer2_subgraph=subgraph,
            layer3_abstracted=abstracted,
            layer4_trimmed=trimmed,
            stats=stats,
        )

    def _count_tokens(self, text: str) -> int:
        """トークン数概算"""
        try:
            import tiktoken
            tokenizer = tiktoken.get_encoding("cl100k_base")
            return len(tokenizer.encode(text))
        except Exception:
            return int(len(text) * 1.5)