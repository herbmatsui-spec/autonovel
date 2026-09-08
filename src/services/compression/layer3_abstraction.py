"""Layer 3: Conceptual Abstraction & Categorization Mapper (Steps 43-47).

Refactored to replace static dictionary lookup with multi-tiered DynamicTaxonomyEngine:
- Dynamic suffix & morphological rule matching
- Subgraph node category auto-detection
- Hierarchical edge relation generalization
- Metadata tracking & LRU caching
"""

from __future__ import annotations

import logging
from typing import Any

from src.services.compression.layer3_taxonomy import DynamicTaxonomyEngine, SUFFIX_TAXONOMY_RULES
from src.services.compression.models import AbstractionLayerOutput, SubgraphLayerOutput

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    "主要キャラ",
    "核心設定",
    "伏線",
    "武術・スキル",
    "地理・勢力",
    "アイテム・装備",
]

# Backward compatibility dictionary
CONCEPT_TAXONOMY = {
    # 戦闘・武術
    "抜刀": "近接剣術スキル",
    "居合": "近接剣術スキル",
    "迅雷": "雷属性攻撃",
    "火球": "火炎魔術",
    "爆縮": "高密度破壊魔術",
    "治癒": "回復術式",
    # 政治・社会
    "関税": "経済統制政策",
    "同盟": "国家間外交協定",
    "宣戦": "軍事侵攻決定",
    "密定": "情報諜報網",
    "追放": "勢力追放・排斥",
    # アイテム・装備
    "聖剣": "伝説級武装",
    "魔導書": "古代遺物",
    "ポーション": "回復消耗品",
    "指輪": "魔力補助装飾品",
}


class Layer3ConceptAbstractor:
    """Abstracts specific facts into higher-level conceptual categories with dynamic taxonomy."""

    def __init__(
        self,
        categories: list[str] | None = None,
        taxonomy_engine: DynamicTaxonomyEngine | None = None,
    ) -> None:
        self.categories = categories or list(DEFAULT_CATEGORIES)
        self.taxonomy_engine = taxonomy_engine or DynamicTaxonomyEngine(
            static_overrides=CONCEPT_TAXONOMY
        )

    def abstract(
        self,
        subgraph: SubgraphLayerOutput,
        raw_text: str = "",
    ) -> AbstractionLayerOutput:
        """Abstract and categorize entities, relations, and text facts (Steps 43-47)."""
        categorized_facts: dict[str, list[dict[str, Any]]] = {cat: [] for cat in self.categories}
        abstract_concepts: list[str] = []
        category_mappings: dict[str, list[str]] = {}

        # 1. ノードからの事実・概念抽出 & 動的カテゴリ自動判定 (Step 44)
        for node in subgraph.nodes:
            name = node.get("name", "")
            labels = node.get("labels", [])
            props = node.get("properties", {})
            desc = props.get("description") or props.get("role") or ""

            # 概念の動的一般化
            generalized = self._generalize_concept(name, context=desc)

            # ラベル/タイプ判定 (ラベルまたは動的タクソノミー結果から判定)
            target_cat = self._detect_category_for_node(labels, generalized, name)

            if generalized:
                abstract_concepts.append(generalized)
                category_mappings.setdefault(target_cat, []).append(f"{name} -> {generalized}")

            fact_text = f"{name}（{desc}）" if desc else name
            categorized_facts[target_cat].append({
                "entity": name,
                "concept": generalized or name,
                "fact": fact_text,
                "category": target_cat,
            })

        # 2. エッジ（関係性）からの事実・階層的関係一般化 (Step 45)
        for edge in subgraph.edges:
            src = edge.get("source")
            tgt = edge.get("target")
            rel = edge.get("type", "related")

            # 階層的関係一般化
            generalized_rel = self._generalize_relation(rel)
            target_cat = "主要キャラ"
            if any(k in generalized_rel for k in ["対立", "因縁", "謀略"]):
                target_cat = "伏線"
            elif any(k in generalized_rel for k in ["統治", "領地", "同盟"]):
                target_cat = "地理・勢力"
            elif any(k in generalized_rel for k in ["装備", "遺物", "使役"]):
                target_cat = "アイテム・装備"

            edge_fact = f"{src} と {tgt} は「{rel}（{generalized_rel}）」の関係"
            categorized_facts[target_cat].append({
                "entity": f"{src}-{tgt}",
                "concept": generalized_rel,
                "fact": edge_fact,
                "category": target_cat,
            })

        # 3. 生テキストからの特定キーワード概念マッピング (動的エンジン併用)
        for kw, abstract_term in self.taxonomy_engine.static_overrides.items():
            if kw in raw_text and abstract_term not in abstract_concepts:
                abstract_concepts.append(abstract_term)

        # 空のカテゴリを除去
        cleaned_facts = {cat: facts for cat, facts in categorized_facts.items() if facts}

        total_mappings = sum(len(m) for m in category_mappings.values())

        return AbstractionLayerOutput(
            abstract_concepts=list(dict.fromkeys(abstract_concepts)),
            categorized_facts=cleaned_facts,
            category_mappings=category_mappings,
            metadata={
                "engine": "DynamicTaxonomyEngine",
                "total_concepts": len(abstract_concepts),
                "total_mappings": total_mappings,
                "cache_size": len(self.taxonomy_engine._cache),
            },
        )

    def _detect_category_for_node(
        self, labels: list[str], generalized: str | None, name: str
    ) -> str:
        """Dynamically detect category using labels and taxonomy concept (Step 44)."""
        # Explicit labels check
        if any(l in ["Location", "Place", "City", "Country", "地理", "国家"] for l in labels):
            return "地理・勢力"
        if any(l in ["Item", "Weapon", "Artifact", "アイテム", "武器"] for l in labels):
            return "アイテム・装備"
        if any(l in ["Skill", "Magic", "Ability", "スキル", "魔法"] for l in labels):
            return "武術・スキル"
        if any(l in ["Rule", "Lore", "WorldSetting", "設定"] for l in labels):
            return "核心設定"

        # Concept-based heuristic inference
        if generalized:
            if any(k in generalized for k in ["スキル", "攻撃", "魔術", "術式", "剣術", "格闘"]):
                return "武術・スキル"
            if any(k in generalized for k in ["国家", "領邦", "組織", "勢力", "都市", "ダンジョン", "拠点"]):
                return "地理・勢力"
            if any(k in generalized for k in ["武装", "刀剣", "防具", "装飾具", "遺物", "触媒", "消耗品"]):
                return "アイテム・装備"
            if any(k in generalized for k in ["法令", "協定", "政策", "策動", "事変"]):
                return "核心設定"

        return "主要キャラ"

    def _generalize_relation(self, rel: str) -> str:
        """Hierarchically generalize relation types into higher-level abstract bonds (Step 45)."""
        if not rel or not isinstance(rel, str):
            return "一般関係"

        if any(k in rel for k in ["敵対", "対立", "裏切り", "陰謀", "因縁", "憎悪", "復讐"]):
            return "対立・因縁関係"
        if any(k in rel for k in ["所属", "統治", "領地", "主従", "配下", "服従"]):
            return "統治・主従関係"
        if any(k in rel for k in ["所持", "使用", "装備", "使役", "継承"]):
            return "装備・使役関係"
        if any(k in rel for k in ["同盟", "協調", "友愛", "共闘", "師弟", "親愛"]):
            return "協力・盟約関係"
        if any(k in rel for k in ["血縁", "親子", "兄弟", "夫婦", "家族"]):
            return "血縁・家系関係"

        return rel

    def _generalize_concept(self, name: str, context: str = "") -> str | None:
        """Map a specific entity/skill/item name to an abstracted category via DynamicTaxonomyEngine."""
        res = self.taxonomy_engine.generalize(name, context)
        # Only return generalized concept if it actually abstracted away from raw name
        if res and res != name:
            return res
        return None


__all__ = ["Layer3ConceptAbstractor", "DEFAULT_CATEGORIES", "CONCEPT_TAXONOMY"]
