import pytest
from src.services.compression.layer3_abstraction import Layer3ConceptAbstractor
from src.services.compression.models import SubgraphLayerOutput

def test_layer3_preserves_proper_nouns_with_dual_format():
    abstractor = Layer3ConceptAbstractor()
    subgraph = SubgraphLayerOutput(
        nodes=[
            {"name": "抜刀・迅雷", "labels": ["Skill"], "properties": {"description": "神速の雷撃斬撃"}},
            {"name": "魔剣バルムンク", "labels": ["Item"], "properties": {"description": "竜殺しの呪われし古剣"}},
        ],
        edges=[
            {"source": "抜刀・迅雷", "target": "魔剣バルムンク", "type": "併用奥義"},
        ]
    )
    res = abstractor.abstract(subgraph)
    
    # 武術・スキルに「抜刀・迅雷」と「雷撃系」が両立していること
    skills = res.categorized_facts.get("武術・スキル", [])
    assert any("抜刀・迅雷" in f["fact"] and "[" in f["fact"] for f in skills)
    
    # アイテム・装備に「魔剣バルムンク」と「伝説級」が両立していること
    items = res.categorized_facts.get("アイテム・装備", [])
    assert any("魔剣バルムンク" in f["fact"] and "[" in f["fact"] for f in items)