"""Unit tests for Layer 3 Dynamic Concept Abstraction & Hierarchy Integration (Part 4 / Steps 43-48)."""

import pytest

from src.services.compression.layer3_abstraction import Layer3ConceptAbstractor
from src.services.compression.models import SubgraphLayerOutput, AbstractionLayerOutput


def test_layer3_dynamic_concept_abstraction():
    """Test dynamic concept generalization without relying solely on static dictionary (Step 43)."""
    abstractor = Layer3ConceptAbstractor()

    subgraph = SubgraphLayerOutput(
        nodes=[
            # Node with unlisted custom skill name
            {"name": "星砕破", "labels": [], "properties": {"description": "星をも砕く渾身の打撃技"}},
            # Node with unlisted nation name
            {"name": "バルフィア帝国", "labels": [], "properties": {"description": "北方の覇権軍事国家"}},
        ],
        edges=[],
    )

    output = abstractor.abstract(subgraph)
    assert isinstance(output, AbstractionLayerOutput)

    # Concepts should be inferred dynamically from morphological suffix rules
    assert any("攻撃スキル" in c for c in output.abstract_concepts)
    assert any("国家・領邦" in c for c in output.abstract_concepts)


def test_subgraph_node_category_auto_detection():
    """Test dynamic detection of category for unlabelled nodes (Step 44)."""
    abstractor = Layer3ConceptAbstractor()

    subgraph = SubgraphLayerOutput(
        nodes=[
            # No explicit label, but name suggests skill
            {"name": "烈火魔導式", "labels": []},
            # No explicit label, but name suggests artifact
            {"name": "幻影の指輪", "labels": []},
        ],
        edges=[],
    )

    output = abstractor.abstract(subgraph)

    # 烈火魔導式 should be auto-assigned to 武術・スキル
    assert "武術・スキル" in output.categorized_facts
    skill_facts = [f["entity"] for f in output.categorized_facts["武術・スキル"]]
    assert "烈火魔導式" in skill_facts

    # 幻影の指輪 should be auto-assigned to アイテム・装備
    assert "アイテム・装備" in output.categorized_facts
    item_facts = [f["entity"] for f in output.categorized_facts["アイテム・装備"]]
    assert "幻影の指輪" in item_facts


def test_hierarchical_edge_generalization():
    """Test hierarchical edge relation abstraction (Step 45)."""
    abstractor = Layer3ConceptAbstractor()

    subgraph = SubgraphLayerOutput(
        nodes=[
            {"name": "勇者", "labels": ["Character"]},
            {"name": "魔王", "labels": ["Character"]},
            {"name": "聖剣", "labels": ["Item"]},
        ],
        edges=[
            {"source": "勇者", "target": "魔王", "type": "因縁と裏切り"},
            {"source": "勇者", "target": "聖剣", "type": "継承し装備"},
        ],
    )

    output = abstractor.abstract(subgraph)

    # "因縁と裏切り" must be generalized to 対立・因縁関係 under 伏線
    assert "伏線" in output.categorized_facts
    foreshadow_facts = output.categorized_facts["伏線"]
    assert any("対立・因縁関係" in f["concept"] for f in foreshadow_facts)

    # "継承し装備" must be generalized to 装備・使役関係 under アイテム・装備
    assert "アイテム・装備" in output.categorized_facts
    equip_facts = output.categorized_facts["アイテム・装備"]
    assert any("装備・使役関係" in f["concept"] for f in equip_facts)


def test_abstraction_layer_output_metadata_and_backward_compat():
    """Test metadata presence and backward compatibility with static taxonomy (Steps 46-47)."""
    abstractor = Layer3ConceptAbstractor()

    # Test backward-compatible terms (from static CONCEPT_TAXONOMY)
    subgraph = SubgraphLayerOutput(
        nodes=[
            {"name": "抜刀", "labels": ["Skill"]},
            {"name": "聖剣", "labels": ["Weapon"]},
        ],
        edges=[],
    )

    output = abstractor.abstract(subgraph, raw_text="聖剣と抜刀術")

    # Output metadata check
    assert "engine" in output.metadata
    assert output.metadata["engine"] == "DynamicTaxonomyEngine"
    assert output.metadata["total_concepts"] >= 2
    assert output.metadata["cache_size"] >= 0

    # Ensure classic concepts are still mapped correctly
    assert "近接剣術スキル" in output.abstract_concepts
    assert "伝説級武装" in output.abstract_concepts
