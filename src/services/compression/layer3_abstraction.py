"""Layer 3: Conceptual Abstraction & Categorization Mapper (Step 29)."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from src.services.compression.models import SubgraphLayerOutput, AbstractionLayerOutput

DEFAULT_CATEGORIES = [
    "主要キャラ",
    "核心設定",
    "伏線",
    "武術・スキル",
    "地理・勢力",
    "アイテム・装備",
]

# 概念マッピング（具体語 -> 一般化・抽象概念）
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
    """Abstracts specific facts into higher-level conceptual categories."""

    def __init__(self, categories: list[str] | None = None) -> None:
        self.categories = categories or list(DEFAULT_CATEGORIES)

    def abstract(
        self,
        subgraph: SubgraphLayerOutput,
        raw_text: str = "",
    ) -> AbstractionLayerOutput:
        """Abstract and categorize entities, relations, and text facts."""
        categorized_facts: dict[str, list[dict[str, Any]]] = {cat: [] for cat in self.categories}
        abstract_concepts: list[str] = []
        category_mappings: dict[str, list[str]] = {}

        # 1. ノードからの事実・概念抽出
        for node in subgraph.nodes:
            name = node.get("name", "")
            labels = node.get("labels", [])
            props = node.get("properties", {})
            desc = props.get("description") or props.get("role") or ""

            # ラベル/タイプ判定
            target_cat = "主要キャラ"
            if any(l in ["Location", "Place", "City", "Country", "地理", "国家"] for l in labels):
                target_cat = "地理・勢力"
            elif any(l in ["Item", "Weapon", "Artifact", "アイテム", "武器"] for l in labels):
                target_cat = "アイテム・装備"
            elif any(l in ["Skill", "Magic", "Ability", "スキル", "魔法"] for l in labels):
                target_cat = "武術・スキル"
            elif any(l in ["Rule", "Lore", "WorldSetting", "設定"] for l in labels):
                target_cat = "核心設定"

            # 概念の一般化
            generalized = self._generalize_concept(name)
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

        # 2. エッジ（関係性）からの事実・伏線抽出
        for edge in subgraph.edges:
            src = edge.get("source")
            tgt = edge.get("target")
            rel = edge.get("type", "related")

            target_cat = "主要キャラ"
            if any(k in rel for k in ["敵対", "対立", "裏切り", "陰謀", "因縁"]):
                target_cat = "伏線"
            elif any(k in rel for k in ["所属", "統治", "領地"]):
                target_cat = "地理・勢力"
            elif any(k in rel for k in ["所持", "使用", "装備"]):
                target_cat = "アイテム・装備"

            edge_fact = f"{src} と {tgt} は「{rel}」の関係"
            categorized_facts[target_cat].append({
                "entity": f"{src}-{tgt}",
                "concept": rel,
                "fact": edge_fact,
                "category": target_cat,
            })

        # 3. 生テキストからの特定キーワード概念マッピング
        for kw, abstract_term in CONCEPT_TAXONOMY.items():
            if kw in raw_text and abstract_term not in abstract_concepts:
                abstract_concepts.append(abstract_term)

        # 空のカテゴリを除去
        cleaned_facts = {cat: facts for cat, facts in categorized_facts.items() if facts}

        return AbstractionLayerOutput(
            abstract_concepts=list(dict.fromkeys(abstract_concepts)),
            categorized_facts=cleaned_facts,
            category_mappings=category_mappings,
        )

    def _generalize_concept(self, name: str) -> str | None:
        """Map a specific entity/skill/item name to an abstracted category."""
        for pattern, concept in CONCEPT_TAXONOMY.items():
            if pattern in name:
                return concept
        return None


__all__ = ["Layer3ConceptAbstractor", "DEFAULT_CATEGORIES", "CONCEPT_TAXONOMY"]
