"""Layer 3 Dynamic Taxonomy & Concept Abstraction Engines (Steps 37-41).

Replaces hardcoded static dictionaries with dynamic rule-based, semantic anchor,
and LLM-driven concept generalization for open-world creative entities.
"""

from __future__ import annotations

import abc
import logging
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Standard conceptual anchor categories for semantic classification
STANDARD_CONCEPT_ANCHORS: dict[str, list[str]] = {
    "武術・戦闘スキル": [
        "剣術", "槍術", "弓術", "格闘術", "暗殺術", "奥義", "必殺技", "魔術詠唱",
        "斬撃", "打撃", "防御壁", "回避法", "呪詛", "術式",
    ],
    "伝説級武装・遺物": [
        "聖剣", "魔剣", "神槍", "宝具", "古代遺物", "魔導書", "秘宝", "アーティファクト",
        "護符", "霊薬", "魔石",
    ],
    "国家・統治機構": [
        "帝国", "王国", "公国", "連邦", "騎士団", "評議会", "ギルド", "教会", "貴族院",
        "関税局", "防衛軍", "同盟",
    ],
    "地理・特殊領域": [
        "霊峰", "迷宮", "ダンジョン", "神殿", "大森林", "魔の海", "地下都市", "要塞",
        "結界領域", "境界",
    ],
    "政治・謀略・伏線": [
        "密定", "諜報網", "裏切り", "政変", "密約", "追放令", "暗殺計画", "後継者争い",
        "宣戦布告", "経済制裁",
    ],
}

# Extensive Japanese suffix patterns for novel entities (50+ rules)
SUFFIX_TAXONOMY_RULES: list[tuple[re.Pattern, str]] = [
    # 武術・スキル・魔法
    (re.compile(r".*(?:剣|刀|刃|槍|斧|弓|弾|撃|斬|破|突|拳|掌|蹴)$"), "近接・物理攻撃スキル"),
    (re.compile(r".*(?:術|法|式|流|技|波|陣|界|円|閃|舞)$"), "武術・魔導術式"),
    (re.compile(r".*(?:炎|火|熱|獄)$"), "火炎系スキル"),
    (re.compile(r".*(?:氷|雪|凍|零)$"), "氷結系スキル"),
    (re.compile(r".*(?:雷|電|迅|轟)$"), "雷撃系スキル"),
    (re.compile(r".*(?:風|嵐|旋|疾)$"), "疾風系スキル"),
    (re.compile(r".*(?:光|聖|神|輝)$"), "聖光・神聖術式"),
    (re.compile(r".*(?:闇|影|黒|冥|凶)$"), "暗黒・冥府術式"),
    (re.compile(r".*(?:治癒|回復|再生|蘇生)$"), "治癒・回復術式"),
    (re.compile(r".*(?:障壁|盾|殻|装甲|防壁)$"), "防御・防壁術式"),
    (re.compile(r".*(?:束縛|封印|枷|網|檻)$"), "拘束・封印術式"),
    # アイテム・装備・アーティファクト
    (re.compile(r".*(?:聖剣|魔剣|宝剣|妖刀|神剣)$"), "伝説級刀剣"),
    (re.compile(r".*(?:鎧|兜|籠手|具足|ローブ|マント)$"), "防具・装具"),
    (re.compile(r".*(?:指輪|首飾り|腕輪|耳飾り|ペンダント|アミュレット)$"), "魔力装飾具"),
    (re.compile(r".*(?:書|典|録|符|巻物|グリモワール)$"), "魔導記録・遺物"),
    (re.compile(r".*(?:薬|水|油|膏|ポーション|エリクサー)$"), "霊薬・消耗品"),
    (re.compile(r".*(?:石|晶|玉|核|結晶)$"), "魔導触媒・宝石"),
    # 国家・勢力・統治
    (re.compile(r".*(?:帝国|王国|公国|皇国|合衆国|連邦)$"), "国家・領邦"),
    (re.compile(r".*(?:団|隊|軍|党|派|同盟|組合|ギルド)$"), "組織・軍事勢力"),
    (re.compile(r".*(?:教|教会|聖堂|宗派|教団)$"), "宗教・信仰勢力"),
    (re.compile(r".*(?:院|府|庁|省|局|所|座)$"), "統治機関・行政組織"),
    # 地理・施設
    (re.compile(r".*(?:城|宮|館|要塞|砦|城塞)$"), "軍事・統治拠点"),
    (re.compile(r".*(?:森|林|海|湖|川|谷|山|峰|窟|洞)$"), "自然地形・秘境"),
    (re.compile(r".*(?:迷宮|遺跡|墳墓|塔|祭壇)$"), "古代遺構・ダンジョン"),
    (re.compile(r".*(?:街|都|村|港|宿)$"), "集落・都市拠点"),
    # 政治・社会・陰謀
    (re.compile(r".*(?:令|法|法規|条約|協定|盟約)$"), "法令・外交協定"),
    (re.compile(r".*(?:計画|謀略|陰謀|工作|変)$"), "政治的策動・事変"),
    (re.compile(r".*(?:制裁|封鎖|追放|粛清|排斥)$"), "制裁・排斥政策"),
]


class TaxonomyEngine(abc.ABC):
    """Abstract base class for entity generalization and concept mapping (Step 37)."""

    @abc.abstractmethod
    def generalize(self, entity_name: str, context: str = "") -> str | None:
        """Generalize a specific entity name to an abstract novel concept."""
        pass


class RuleBasedMorphologicalMapper(TaxonomyEngine):
    """Generalizes unknown entities using suffix patterns and morphology (Step 38)."""

    def __init__(self, custom_rules: list[tuple[re.Pattern, str]] | None = None) -> None:
        self.rules = list(custom_rules or SUFFIX_TAXONOMY_RULES)

    def generalize(self, entity_name: str, context: str = "") -> str | None:
        if not entity_name or not isinstance(entity_name, str):
            return None
        cleaned = entity_name.strip()
        for pattern, concept in self.rules:
            if pattern.match(cleaned):
                return concept
        return None


class SemanticAnchorTaxonomy(TaxonomyEngine):
    """Maps entities to conceptual classes using embedding cosine similarity (Step 39)."""

    def __init__(
        self,
        embedding_fn: Callable[[str], list[float]] | None = None,
        anchor_categories: dict[str, list[str]] | None = None,
        threshold: float = 0.65,
    ) -> None:
        self.embedding_fn = embedding_fn
        self.anchors = anchor_categories or STANDARD_CONCEPT_ANCHORS
        self.threshold = threshold
        self._anchor_embeddings: dict[str, list[float]] = {}

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def generalize(self, entity_name: str, context: str = "") -> str | None:
        if not self.embedding_fn or not entity_name:
            return None

        try:
            entity_vec = self.embedding_fn(entity_name)
            best_cat = None
            best_sim = 0.0

            for cat, examples in self.anchors.items():
                cat_desc = f"{cat}: {', '.join(examples[:5])}"
                if cat not in self._anchor_embeddings:
                    self._anchor_embeddings[cat] = self.embedding_fn(cat_desc)
                sim = self._cosine_similarity(entity_vec, self._anchor_embeddings[cat])
                if sim > best_sim:
                    best_sim = sim
                    best_cat = cat

            if best_sim >= self.threshold and best_cat:
                return best_cat
        except Exception as e:
            logger.debug(f"SemanticAnchorTaxonomy error: {e}")
        return None


class LLMDynamicTaxonomy(TaxonomyEngine):
    """Infers abstract categories for novel creative terms via lightweight LLM (Step 40)."""

    def __init__(self, llm_adapter: Any = None) -> None:
        self.llm_adapter = llm_adapter

    def generalize(self, entity_name: str, context: str = "") -> str | None:
        if not self.llm_adapter or not entity_name:
            return None

        # Synchronous fallback or mock check
        if hasattr(self.llm_adapter, "generate_sync"):
            try:
                prompt = (
                    f"作中用語: {entity_name}\n文脈: {context}\n"
                    "この用語の小説・創作上の一般的な抽象概念（例:『回復術式』『伝説級武装』『国家間協定』など）を1単語で返してください。"
                )
                res = self.llm_adapter.generate_sync(prompt)
                if isinstance(res, str) and res.strip():
                    return res.strip()
            except Exception as e:
                logger.debug(f"LLMDynamicTaxonomy sync error: {e}")
        return None

    async def generalize_async(self, entity_name: str, context: str = "") -> str | None:
        """Asynchronous LLM concept inference."""
        if not self.llm_adapter or not hasattr(self.llm_adapter, "generate"):
            return self.generalize(entity_name, context)

        try:
            prompt = (
                f"作中用語: {entity_name}\n文脈: {context}\n"
                "この用語の小説・創作上の一般的な抽象概念を1単語で返してください。"
            )
            res = await self.llm_adapter.generate(prompt)
            if isinstance(res, str) and res.strip():
                return res.strip()
        except Exception as e:
            logger.debug(f"LLMDynamicTaxonomy async error: {e}")
        return None


class DynamicTaxonomyEngine(TaxonomyEngine):
    """Multi-stage hybrid taxonomy engine combining cache, rules, embeddings, and LLM (Step 41)."""

    def __init__(
        self,
        rule_mapper: RuleBasedMorphologicalMapper | None = None,
        semantic_anchor: SemanticAnchorTaxonomy | None = None,
        llm_taxonomy: LLMDynamicTaxonomy | None = None,
        static_overrides: dict[str, str] | None = None,
        cache_size: int = 500,
    ) -> None:
        self.rule_mapper = rule_mapper or RuleBasedMorphologicalMapper()
        self.semantic_anchor = semantic_anchor
        self.llm_taxonomy = llm_taxonomy
        self.static_overrides = dict(static_overrides or {})
        self._cache: dict[str, str] = {}
        self.cache_size = cache_size

    def generalize(self, entity_name: str, context: str = "") -> str:
        """Generalize entity using tiered fallback: static -> cache -> rules -> semantic -> LLM."""
        if not entity_name or not isinstance(entity_name, str):
            return ""

        key = entity_name.strip()
        if not key:
            return ""

        # 1. Static override
        if key in self.static_overrides:
            return self.static_overrides[key]

        # 2. Memory cache
        if key in self._cache:
            return self._cache[key]

        # 3. Rule-based suffix and morphological inference (Fastest & deterministic)
        rule_res = self.rule_mapper.generalize(key, context)
        if rule_res:
            self._set_cache(key, rule_res)
            return rule_res

        # 4. Semantic Anchor cosine similarity
        if self.semantic_anchor:
            sem_res = self.semantic_anchor.generalize(key, context)
            if sem_res:
                self._set_cache(key, sem_res)
                return sem_res

        # 5. LLM fallback (if configured)
        if self.llm_taxonomy:
            llm_res = self.llm_taxonomy.generalize(key, context)
            if llm_res:
                self._set_cache(key, llm_res)
                return llm_res

        # 6. Default to original key
        return key

    def _set_cache(self, key: str, value: str) -> None:
        if len(self._cache) >= self.cache_size:
            # Simple eviction
            first_key = next(iter(self._cache))
            del self._cache[first_key]
        self._cache[key] = value
