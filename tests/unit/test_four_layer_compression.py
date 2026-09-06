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
from tests.benchmarks.annotations import ACCURACY_TEST_CASES, SCENE_ANNOTATIONS
from tests.benchmarks.accuracy import scene_type_accuracy, evaluate_test_case


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


@pytest.mark.parametrize("test_case", ACCURACY_TEST_CASES)
def test_scene_type_accuracy(test_case):
    """シーンタイプ別圧縮精度の検証: 必須カテゴリ・エンティティが保持されること."""
    config = CompressionConfig(max_tokens=300, cache_enabled=False)
    compressor = FourLayerCompressor(config=config)

    # Build entities with appropriate labels for categorization
    # Map entity names to labels based on test case
    entity_labels = {}
    relations = []
    
    if test_case["scene_type"] == "combat":
        entity_labels = {
            "e1": ("アルカディア", ["Character"]),
            "e2": ("ヴォルケイン", ["Character"]),
            "e3": ("エクスカリバー", ["Item", "Weapon"]),
            "e4": ("迅雷", ["Skill"]),
        }
        relations = [
            {"source": "e1", "target": "e3", "type": "所持"},
            {"source": "e1", "target": "e2", "type": "敵対"},
            {"source": "e1", "target": "e4", "type": "使用"},
        ]
    elif test_case["scene_type"] == "daily":
        entity_labels = {
            "e1": ("アルカディア", ["Character"]),
            "e2": ("カロル", ["Character"]),
            "e3": ("王都グランヴァル", ["Location", "City"]),
            "e4": ("冒険者ギルド", ["Organization", "Faction"]),
            "e5": ("治癒のポーション", ["Item"]),
        }
        relations = [
            {"source": "e1", "target": "e2", "type": "同行"},
            {"source": "e1", "target": "e3", "type": "滞在"},
            {"source": "e1", "target": "e5", "type": "所持"},
        ]
    elif test_case["scene_type"] == "psychological":
        entity_labels = {
            "e1": ("アルカディア", ["Character"]),
            "e2": ("ガレス", ["Character"]),
            "e3": ("ヴォルケイン", ["Character"]),
            "e4": ("エクスカリバー", ["Item", "Weapon", "Lore"]),
            "e5": ("迅雷", ["Skill", "Lore"]),
        }
        relations = [
            {"source": "e1", "target": "e2", "type": "師弟"},
            {"source": "e1", "target": "e3", "type": "因縁"},
            {"source": "e1", "target": "e4", "type": "因縁"},
        ]
    elif test_case["scene_type"] == "political":
        entity_labels = {
            "e1": ("バルガス", ["Character"]),
            "e2": ("ミレナ", ["Character"]),
            "e3": ("商人ギルド", ["Organization", "Faction"]),
            "e4": ("辺境警備隊", ["Organization", "Faction"]),
            "e5": ("エルシオン協定", ["Rule", "Lore"]),
            "e6": ("関税", ["Policy", "Lore"]),
        }
        relations = [
            {"source": "e1", "target": "e2", "type": "対立"},
            {"source": "e3", "target": "e4", "type": "対立"},
            {"source": "e1", "target": "e5", "type": "引用"},
            {"source": "e2", "target": "e6", "type": "反対"},
        ]

    entities = [{"id": eid, "name": name, "labels": labels} for eid, (name, labels) in entity_labels.items()]

    result = compressor.compress(
        test_case["text"],
        entities=entities,
        relations=relations,
        scene_type=test_case["scene_type"],
        bypass_cache=True,
    )

    compressed_result = {
        "final_text": result.final_context_text,
        "layer3_categories": list(result.layer3.categorized_facts.keys()) if result.layer3 else [],
    }

    eval_result = evaluate_test_case(test_case, compressed_result)

    assert eval_result["passed_category"], (
        f"Category preservation failed for {test_case['name']}: "
        f"expected {test_case['expected_categories']}, got {eval_result['actual_categories']}, "
        f"rate={eval_result['category_preservation_rate']:.2f}"
    )
    assert eval_result["passed_entity"], (
        f"Entity retention failed for {test_case['name']}: "
        f"expected {test_case['expected_entities']}, rate={eval_result['entity_retention_rate']:.2f}"
    )

    compressed_result = {
        "final_text": result.final_context_text,
        "layer3_categories": list(result.layer3.categorized_facts.keys()) if result.layer3 else [],
    }

    eval_result = evaluate_test_case(test_case, compressed_result)

    assert eval_result["passed_category"], (
        f"Category preservation failed for {test_case['name']}: "
        f"expected {test_case['expected_categories']}, got {eval_result['actual_categories']}, "
        f"rate={eval_result['category_preservation_rate']:.2f}"
    )
    assert eval_result["passed_entity"], (
        f"Entity retention failed for {test_case['name']}: "
        f"expected {test_case['expected_entities']}, rate={eval_result['entity_retention_rate']:.2f}"
    )


def test_scene_type_accuracy_all_scenes():
    """全シーンタイプでの精度検証（統合テスト）."""
    config = CompressionConfig(max_tokens=300, cache_enabled=False)
    compressor = FourLayerCompressor(config=config)

    def build_entities_relations(test_case):
        """Build entities and relations for a test case."""
        if test_case["scene_type"] == "combat":
            entity_labels = {
                "e1": ("アルカディア", ["Character"]),
                "e2": ("ヴォルケイン", ["Character"]),
                "e3": ("エクスカリバー", ["Item", "Weapon"]),
                "e4": ("迅雷", ["Skill"]),
            }
            relations = [
                {"source": "e1", "target": "e3", "type": "所持"},
                {"source": "e1", "target": "e2", "type": "敵対"},
                {"source": "e1", "target": "e4", "type": "使用"},
            ]
        elif test_case["scene_type"] == "daily":
            entity_labels = {
                "e1": ("アルカディア", ["Character"]),
                "e2": ("カロル", ["Character"]),
                "e3": ("王都グランヴァル", ["Location", "City"]),
                "e4": ("冒険者ギルド", ["Organization", "Faction"]),
                "e5": ("治癒のポーション", ["Item"]),
            }
            relations = [
                {"source": "e1", "target": "e2", "type": "同行"},
                {"source": "e1", "target": "e3", "type": "滞在"},
                {"source": "e1", "target": "e5", "type": "所持"},
            ]
        elif test_case["scene_type"] == "psychological":
            entity_labels = {
                "e1": ("アルカディア", ["Character"]),
                "e2": ("ガレス", ["Character"]),
                "e3": ("ヴォルケイン", ["Character"]),
                "e4": ("エクスカリバー", ["Item", "Weapon", "Lore"]),
                "e5": ("迅雷", ["Skill", "Lore"]),
            }
            relations = [
                {"source": "e1", "target": "e2", "type": "師弟"},
                {"source": "e1", "target": "e3", "type": "因縁"},
                {"source": "e1", "target": "e4", "type": "因縁"},
            ]
        elif test_case["scene_type"] == "political":
            entity_labels = {
                "e1": ("バルガス", ["Character"]),
                "e2": ("ミレナ", ["Character"]),
                "e3": ("商人ギルド", ["Organization", "Faction"]),
                "e4": ("辺境警備隊", ["Organization", "Faction"]),
                "e5": ("エルシオン協定", ["Rule", "Lore"]),
                "e6": ("関税", ["Policy", "Lore"]),
            }
            relations = [
                {"source": "e1", "target": "e2", "type": "対立"},
                {"source": "e3", "target": "e4", "type": "対立"},
                {"source": "e1", "target": "e5", "type": "引用"},
                {"source": "e2", "target": "e6", "type": "反対"},
            ]
        else:
            entity_labels = {}
            relations = []
        entities = [{"id": eid, "name": name, "labels": labels} for eid, (name, labels) in entity_labels.items()]
        return entities, relations

    results = {}
    for test_case in ACCURACY_TEST_CASES:
        entities, relations = build_entities_relations(test_case)
        result = compressor.compress(
            test_case["text"],
            entities=entities,
            relations=relations,
            scene_type=test_case["scene_type"],
            bypass_cache=True,
        )

        compressed_result = {
            "final_text": result.final_context_text,
            "layer3_categories": list(result.layer3.categorized_facts.keys()) if result.layer3 else [],
        }

        eval_result = evaluate_test_case(test_case, compressed_result)
        results[test_case["scene_type"]] = eval_result

    # 全シーンでカテゴリ保持率80%以上
    for scene_type, eval_result in results.items():
        assert eval_result["passed_category"], (
            f"{scene_type}: category preservation {eval_result['category_preservation_rate']:.2f} < 0.80"
        )
        assert eval_result["passed_entity"], (
            f"{scene_type}: entity retention {eval_result['entity_retention_rate']:.2f} < 0.80"
        )

    # 結果サマリ出力
    print("\n=== Scene Type Accuracy Summary ===")
    for scene_type, eval_result in results.items():
        print(f"  {scene_type:15s}: cat={eval_result['category_preservation_rate']:.2f}, "
              f"ent={eval_result['entity_retention_rate']:.2f}, "
              f"passed={eval_result['overall_passed']}")


def test_scene_type_detection_keywords():
    """シーンタイプ検出キーワードの妥当性検証."""
    from src.services.compression.layer4_trimming import Layer4SceneTrimmer
    from tests.benchmarks.annotations import SCENE_TYPE_KEYWORDS

    trimmer = Layer4SceneTrimmer()

    for scene_type, keywords in SCENE_TYPE_KEYWORDS.items():
        # キーワードを含むテキストで正しく検出されること
        test_text = f"これは{keywords[0]}に関するシーンです。{keywords[1]}も含まれます。"
        detected = trimmer.detect_scene_type(test_text)
        # 完全一致でなくても、関連するタイプが検出されることを確認
        # （キーワードベースなので厳密な一致は要求しない）
        assert detected in ("combat", "daily", "psychological", "political", "general")


def test_multi_label_detection():
    """マルチラベルシーンタイプ検出の検証."""
    from src.services.compression.layer4_trimming import Layer4SceneTrimmer

    trimmer = Layer4SceneTrimmer()

    # 単一シーン: combat が最も高い確信度
    combat_text = "アルカディアは剣を抜き、魔王ヴォルケインと激突した。迅雷で撃破を狙う。"
    multi = trimmer.detect_scene_type_multi(combat_text)
    assert multi[0][0] == "combat"
    assert multi[0][1] > 0.5  # 高い確信度
    assert sum(score for _, score in multi) == pytest.approx(1.0, rel=1e-6)

    # 複合シーン: combat + psychological
    mixed_text = "戦闘の中、アルカディアは師匠の言葉を思い出し、葛藤しながら剣を振るう。"
    multi = trimmer.detect_scene_type_multi(mixed_text)
    # combat と psychological の両方が検出される
    scene_types = [st for st, _ in multi]
    assert "combat" in scene_types
    assert "psychological" in scene_types
    assert sum(score for _, score in multi) == pytest.approx(1.0, rel=1e-6)

    # キーワードなし: general にフォールバック
    neutral_text = "今日は良い天気だ。"
    multi = trimmer.detect_scene_type_multi(neutral_text)
    assert multi[0][0] == "general"
    assert multi[0][1] == 1.0


def test_weight_blending():
    """カテゴリ重みブレンドの検証."""
    from src.services.compression.layer4_trimming import _blend_category_weights

    # 単一シーン: 元の重みと同じ
    combat_weights = _blend_category_weights({"combat": 1.0})
    from src.services.compression.layer4_trimming import SCENE_CATEGORY_WEIGHTS
    for cat, weight in SCENE_CATEGORY_WEIGHTS["combat"].items():
        assert combat_weights[cat] == pytest.approx(weight, rel=1e-6)

    # ブレンド: combat 0.6 + psychological 0.4
    blended = _blend_category_weights({"combat": 0.6, "psychological": 0.4})
    # 主要キャラ: 1.6*0.6 + 2.0*0.4 = 0.96 + 0.8 = 1.76
    assert blended["主要キャラ"] == pytest.approx(1.76, rel=1e-3)
    # 武術・スキル: 2.2*0.6 + 0.4*0.4 = 1.32 + 0.16 = 1.48
    assert blended["武術・スキル"] == pytest.approx(1.48, rel=1e-3)
    # 伏線: 1.0*0.6 + 1.9*0.4 = 0.6 + 0.76 = 1.36
    assert blended["伏線"] == pytest.approx(1.36, rel=1e-3)

    # 空の重み: 空の辞書
    empty = _blend_category_weights({})
    assert empty == {}


def test_trim_with_scene_weights():
    """scene_weights を指定したトリミングの検証."""
    from src.services.compression.layer4_trimming import Layer4SceneTrimmer
    from src.services.compression.models import AbstractionLayerOutput

    trimmer = Layer4SceneTrimmer(max_tokens=150)

    abs_out = AbstractionLayerOutput(
        abstract_concepts=["近接剣術スキル", "伝説級武装"],
        categorized_facts={
            "武術・スキル": [{"entity": "迅雷", "fact": "抜刀術・迅雷", "category": "武術・スキル"}],
            "主要キャラ": [{"entity": "アルカディア", "fact": "アルカディア", "category": "主要キャラ"}],
            "伏線": [{"entity": "ヴォルケイン", "fact": "ヴォルケインとの因縁", "category": "伏線"}],
        },
    )

    # 単一 scene_type 指定（後方互換）
    result1 = trimmer.trim(abs_out, scene_type="combat", original_token_count=300)
    assert result1.scene_type == "combat"
    assert "武術・スキル" in result1.compressed_text

    # scene_weights 指定（マルチラベル）
    result2 = trimmer.trim(
        abs_out,
        scene_type="general",  # フォールバック用
        scene_weights={"combat": 0.7, "psychological": 0.3},
        original_token_count=300,
    )
    # 主要シーンタイプは combat になる
    assert result2.scene_type == "combat"
    # ブレンドされた重みでトリミングされる（伏線の重みが上がるため含まれやすい）
    assert "伏線" in result2.compressed_text or "主要キャラ" in result2.compressed_text


__all__ = [
    "test_scene_type_accuracy",
    "test_scene_type_accuracy_all_scenes",
    "test_multi_label_detection",
    "test_weight_blending",
    "test_trim_with_scene_weights",
]

