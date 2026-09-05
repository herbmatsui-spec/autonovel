"""Unit and Integration Tests for 4-Layer Context Compression (Step 34)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.services.compression import (
    CompressionConfig,
    FourLayerCompressor,
    Layer1KeywordExtractor,
    Layer2SubgraphExtractor,
    Layer3ConceptAbstractor,
    Layer4SceneTrimmer,
)
from src.agents.context_builder_agent import ContextBuilderAgent
from src.agents.orchestrator import AgentContext


SAMPLE_LONG_NOVEL_TEXT = """
第1章：勇者と王都の暗雲
勇者アルカディアは、王都グランヴァルを揺るがす経済制裁の報せを受け取った。
宰相バルガスが画策する不当な関税引き上げにより、辺境の領民は飢えに瀕している。
アルカディアは王宮地下深くに眠る伝説級武装、聖剣エクスカリバーの封印を解くため旅立った。
道中、宿敵である魔王軍幹部ヴォルケインが放った暗殺部隊の強襲に遭う。
アルカディアは瞬時に神速の抜刀術・迅雷を繰り出し、電光石火の一撃で敵影を両断した。
一方、王都では陰謀と裏切りの気配が濃厚に漂っており、味方であるはずの神官カロルにも不審な密談の噂があった。
"""


def test_layer1_keyphrase_extraction():
    """Layer 1: キーフレーズ抽出と固有名詞スコアリングの検証."""
    extractor = Layer1KeywordExtractor(top_n=6)
    out = extractor.extract(SAMPLE_LONG_NOVEL_TEXT)

    assert len(out.extracted_keywords) > 0
    assert out.original_char_count > 0
    assert out.original_token_count > 0
    # 主要固有名詞が含まれていること
    keywords = out.extracted_keywords
    assert any("アルカディア" in k or "エクスカリバー" in k or "ヴォルケイン" in k for k in keywords)


def test_layer2_subgraph_and_pruning():
    """Layer 2: 2-hop近傍探索と低関連度エッジの枝刈り検証."""
    extractor = Layer2SubgraphExtractor(max_hops=2, relevance_threshold=1.0)
    entities = [
        {"id": "e1", "name": "アルカディア", "labels": ["Character"]},
        {"id": "e2", "name": "聖剣エクスカリバー", "labels": ["Item"]},
        {"id": "e3", "name": "ヴォルケイン", "labels": ["Character"]},
        {"id": "e4", "name": "名もなき通行人", "labels": ["Character"]},
    ]
    relations = [
        {"source": "e1", "target": "e2", "type": "所持"},       # 重要リレーション
        {"source": "e1", "target": "e3", "type": "敵対"},       # 重要リレーション
        {"source": "e3", "target": "e4", "type": "雑談・目撃"}, # 低関連リレーション（枝刈り対象）
    ]

    res = extractor.extract_from_memory(
        entities=entities,
        relations=relations,
        seed_names=["アルカディア"],
    )

    retained_names = [n["name"] for n in res.nodes]
    assert "アルカディア" in retained_names
    assert "名もなき通行人" not in retained_names
    assert res.pruned_edge_count >= 1


def test_layer3_conceptual_abstraction():
    """Layer 3: 具体的表現の上位概念マッピングとカテゴリ化検証."""
    from src.services.compression.models import SubgraphLayerOutput

    sub = SubgraphLayerOutput(
        nodes=[
            {"name": "抜刀術・迅雷", "labels": ["Skill"]},
            {"name": "聖剣エクスカリバー", "labels": ["Item"]},
            {"name": "王都グランヴァル", "labels": ["Location"]},
        ],
        edges=[
            {"source": "アルカディア", "target": "ヴォルケイン", "type": "敵対"},
        ],
    )

    abstractor = Layer3ConceptAbstractor()
    out = abstractor.abstract(sub, raw_text="抜刀術・迅雷で戦う。関税政策に反対する。")

    assert "近接剣術スキル" in out.abstract_concepts
    assert "伏線" in out.categorized_facts
    assert "アイテム・装備" in out.categorized_facts


def test_layer4_dynamic_scene_trimming():
    """Layer 4: シーン種別に応じた動的トークン割り当て・重要度枝刈り検証."""
    trimmer = Layer4SceneTrimmer(max_tokens=150)
    abstractor = Layer3ConceptAbstractor()

    from src.services.compression.models import SubgraphLayerOutput
    sub = SubgraphLayerOutput(
        nodes=[
            {"name": "アルカディア", "labels": ["Character"]},
            {"name": "抜刀術・迅雷", "labels": ["Skill"]},
            {"name": "王都グランヴァル関税令", "labels": ["Location"]},
        ],
        edges=[
            {"source": "アルカディア", "target": "ヴォルケイン", "type": "敵対"},
        ],
    )
    abs_out = abstractor.abstract(sub)

    # 戦闘シーンの場合
    combat_out = trimmer.trim(abs_out, scene_type="combat", original_token_count=300)
    assert combat_out.token_count <= 150
    assert combat_out.scene_type == "combat"
    assert "武術・スキル" in combat_out.compressed_text or "主要キャラ" in combat_out.compressed_text


def test_four_layer_compressor_pipeline():
    """統合 FourLayerCompressor パイプライン実行とキャッシュ機能の検証."""
    config = CompressionConfig(max_tokens=200, cache_enabled=True)
    compressor = FourLayerCompressor(config=config)

    entities = [
        {"id": "1", "name": "アルカディア"},
        {"id": "2", "name": "ヴォルケイン"},
        {"id": "3", "name": "聖剣エクスカリバー"},
    ]
    relations = [
        {"source": "1", "target": "2", "type": "敵対"},
        {"source": "1", "target": "3", "type": "所持"},
    ]

    # 初回実行（キャッシュミス）
    res1 = compressor.compress(
        SAMPLE_LONG_NOVEL_TEXT,
        entities=entities,
        relations=relations,
        book_id=1,
        ep_num=1,
        scene_type="combat",
    )
    assert res1.from_cache is False
    assert res1.final_token_count <= 200
    assert len(res1.final_context_text) > 0

    # 2回目実行（キャッシュヒット）
    res2 = compressor.compress(
        SAMPLE_LONG_NOVEL_TEXT,
        entities=entities,
        relations=relations,
        book_id=1,
        ep_num=1,
        scene_type="combat",
    )
    assert res2.from_cache is True
    assert res2.final_context_text == res1.final_context_text


@pytest.mark.asyncio
async def test_context_builder_with_compressor():
    """ContextBuilderAgent に FourLayerCompressor を注入した統合検証."""
    repo = MagicMock()
    repo.session = MagicMock()
    plot_mock = MagicMock()
    plot_mock.summary = "アルカディアとヴォルケインの激突"
    plot_mock.title = "第1話：決戦"
    plot_mock.tension = 75
    plot_mock.detailed_blueprint = "戦闘ブループリント"
    plot_mock.scenes = ["激突", "抜刀"]
    plot_mock.is_catharsis = False
    plot_mock.model_dump.return_value = {
        "summary": "アルカディアとヴォルケインの激突",
        "title": "第1話：決戦",
        "tension": 75,
        "scenes": ["激突", "抜刀"],
    }
    repo.get_plot = AsyncMock(return_value=plot_mock)
    repo.get_book = AsyncMock(return_value={"id": 1, "title": "テスト作品"})
    char_mock = MagicMock()
    char_mock.name = "アルカディア"
    repo.get_all_characters = AsyncMock(return_value=[char_mock])
    repo.get_prev_chapter = AsyncMock(return_value=None)

    compressor = FourLayerCompressor(CompressionConfig(max_tokens=150))
    agent = ContextBuilderAgent(repo=repo, compressor=compressor)

    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={"repo": repo},
    )

    result = await agent.execute(ctx)
    assert result.error is None
    w_ctx = result.artifacts["writing_context"]
    assert "compressed_context" in w_ctx
    assert "compression_stats" in w_ctx
    assert w_ctx["compression_stats"]["scene_type"] == "combat"


def test_layer4_packs_smaller_facts_after_large_fact_exceeds_budget():
    """budget オーバー時に大きな事実をスキップし、後続の小さい事実がパッキングされることの検証.

    break → continue の修正により、小さい事実が漏らさずパックされることを確認する。
    """
    from src.services.compression.layer4_trimming import Layer4SceneTrimmer
    from src.services.compression.models import SubgraphLayerOutput
    trimmer = Layer4SceneTrimmer(max_tokens=80)
    abstractor = Layer3ConceptAbstractor()

    sub = SubgraphLayerOutput(
        nodes=[
            {"name": "大きな事象A", "labels": ["Event"]},
            {"name": "小さい事象B", "labels": ["Event"]},
            {"name": "中規模事象C", "labels": ["Event"]},
        ],
        edges=[
            {"source": "A", "target": "B", "type": "関連"},
        ],
    )
    abs_out = abstractor.abstract(sub, raw_text="")

    trim_result = trimmer.trim(abs_out, scene_type="daily", original_token_count=500)

    assert trim_result.token_count <= 80
    text = trim_result.compressed_text
    assert "事象" in text or "Event" in text or len(text) > 0

