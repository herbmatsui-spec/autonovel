"""Unit tests for Layer 3 Dynamic Taxonomy Engines (Part 4 / Steps 37-42)."""

import pytest
from unittest.mock import MagicMock

from src.services.compression.layer3_taxonomy import (
    TaxonomyEngine,
    RuleBasedMorphologicalMapper,
    SemanticAnchorTaxonomy,
    LLMDynamicTaxonomy,
    DynamicTaxonomyEngine,
)


def test_rule_based_morphological_mapper():
    """Test morphological suffix pattern matching for novel entities (Step 38)."""
    mapper = RuleBasedMorphologicalMapper()

    # Weapons & attack skills
    assert mapper.generalize("星砕剣") == "近接・物理攻撃スキル"
    assert mapper.generalize("獄炎破") == "近接・物理攻撃スキル"
    assert mapper.generalize("極光炎") == "火炎系スキル"
    assert mapper.generalize("大治癒") == "治癒・回復術式"
    assert mapper.generalize("天罰の雷") == "雷撃系スキル"

    # Nations & organizations
    assert mapper.generalize("神聖ルキア帝国") == "国家・領邦"
    assert mapper.generalize("自由商人ギルド") == "組織・軍事勢力"
    assert mapper.generalize("影の騎士団") == "組織・軍事勢力"

    # Laws & treaties
    assert mapper.generalize("不可侵条約") == "法令・外交協定"
    assert mapper.generalize("王族追放令") == "法令・外交協定"


def test_semantic_anchor_taxonomy():
    """Test embedding-based semantic anchor concept mapping (Step 39)."""
    # Mock embedding function that returns distinct vector signatures
    def mock_embedding(text: str) -> list[float]:
        if any(w in text for w in ["剣", "武術", "斬", "術", "スキル"]):
            return [1.0, 0.0, 0.0]
        if any(w in text for w in ["国家", "帝国", "組織"]):
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    semantic = SemanticAnchorTaxonomy(
        embedding_fn=mock_embedding,
        threshold=0.5,
    )

    cat = semantic.generalize("疾風の抜刀剣術")
    assert cat == "武術・戦闘スキル"


def test_llm_dynamic_taxonomy():
    """Test LLM-driven abstraction for complex creative concepts (Step 40)."""
    mock_llm = MagicMock()
    mock_llm.generate_sync.return_value = "精神拘束術式"

    llm_tax = LLMDynamicTaxonomy(llm_adapter=mock_llm)
    concept = llm_tax.generalize("魂魄の軛", context="敵の魂を縛る呪具")

    assert concept == "精神拘束術式"
    mock_llm.generate_sync.assert_called_once()


def test_dynamic_taxonomy_engine_tiered_resolution():
    """Test hybrid multi-tiered dynamic taxonomy resolution and caching (Step 41)."""
    engine = DynamicTaxonomyEngine(
        static_overrides={"特例": "固有特異点"},
    )

    # 1. Static override hit
    assert engine.generalize("特例") == "固有特異点"

    # 2. Rule-based hit
    concept1 = engine.generalize("雷帝剣")
    assert concept1 == "近接・物理攻撃スキル"
    assert "雷帝剣" in engine._cache

    # 3. Cache hit (verify rule_mapper is not called for cached key)
    original_generalize = engine.rule_mapper.generalize
    engine.rule_mapper.generalize = MagicMock(side_effect=Exception("Should not be called"))
    concept2 = engine.generalize("雷帝剣")
    assert concept2 == "近接・物理攻撃スキル"

    # Restore rule_mapper
    engine.rule_mapper.generalize = original_generalize

    # 4. Unknown term falls back safely to original key
    assert engine.generalize("アグライア") == "アグライア"
