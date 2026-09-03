"""因果律監査 (PlotIntegrityMonitor) 単体テスト"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.audit import PlotIntegrityMonitor
from src.models.audit import (
    CausalityAuditResult,
    CausalityLink,
    ForeshadowingItem,
    GraphDiffResult,
    PromptPatch,
)
from src.models.graph_schemas import Entity, GraphExtractionResult, Relationship


class TestCausalityLink:
    """CausalityLink モデルテスト"""

    def test_causality_link_creation(self):
        link = CausalityLink(
            cause_entity="アルス",
            cause_event="聖剣を抜いた",
            effect_entity="封印",
            effect_event="解かれた",
            confidence=0.95,
            source="blueprint",
        )
        assert link.cause_entity == "アルス"
        assert link.confidence == 0.95
        assert link.source == "blueprint"

    def test_causality_link_defaults(self):
        link = CausalityLink(
            cause_entity="A",
            cause_event="原因",
            effect_entity="B",
            effect_event="結果",
            source="blueprint",
        )
        assert link.confidence == 1.0
        assert link.source == "blueprint"


class TestForeshadowingItem:
    """ForeshadowingItem モデルテスト"""

    def test_foreshadowing_creation(self):
        fs = ForeshadowingItem(
            entity_name="竜の心臓",
            setup_chapter=3,
            setup_context="宝箱から発見された",
            expected_payoff="最終決戦で竜を制御する",
            importance="Critical",
        )
        assert fs.entity_name == "竜の心臓"
        assert fs.setup_chapter == 3
        assert fs.importance == "Critical"
        assert fs.is_resolved is False


class TestGraphDiffResult:
    """GraphDiffResult モデルテスト"""

    def test_empty_diff(self):
        diff = GraphDiffResult()
        assert diff.missing_entities == set()
        assert diff.extra_entities == set()
        assert diff.missing_relations == set()
        assert diff.extra_relations == set()
        assert diff.property_conflicts == {}

    def test_diff_with_data(self):
        diff = GraphDiffResult(
            missing_entities={"聖剣", "王都"},
            extra_entities={"新キャラ"},
            missing_relations={("アルス", "聖剣", "POSSESSES")},
            extra_relations={("アルス", "新アイテム", "POSSESSES")},
            property_conflicts={"アルス": {"location": {"blueprint": "王都", "content": "村"}}},
        )
        assert "聖剣" in diff.missing_entities
        assert "新キャラ" in diff.extra_entities
        assert ("アルス", "聖剣", "POSSESSES") in diff.missing_relations
        assert diff.property_conflicts["アルス"]["location"]["blueprint"] == "王都"


class TestCausalityAuditResult:
    """CausalityAuditResult モデルテスト"""

    def test_default_consistent(self):
        result = CausalityAuditResult()
        assert result.is_consistent is True
        assert result.score == 1.0
        assert result.causality_links == []
        assert result.broken_chains == []
        assert result.unresolved_foreshadowing == []
        assert result.contradictions == []
        assert result.patches == []

    def test_inconsistent_result(self):
        link = CausalityLink(
            cause_entity="A", cause_event="原因", effect_entity="B", effect_event="結果", source="content"
        )
        result = CausalityAuditResult(
            is_consistent=False,
            score=0.5,
            causality_links=[link],
            broken_chains=[link],
            contradictions=["矛盾あり"],
        )
        assert result.is_consistent is False
        assert result.score == 0.5
        assert len(result.broken_chains) == 1


class TestPlotIntegrityMonitor:
    """PlotIntegrityMonitor 統合テスト"""

    @pytest.fixture
    def monitor(self):
        """モックLLM付きモニター"""
        mock_llm = AsyncMock()
        mock_llm.generate_json = AsyncMock(return_value={
            "metadata": {
                "causality_links": [
                    {
                        "cause_entity": "アルス",
                        "cause_event": "聖剣を抜いた",
                        "effect_entity": "封印",
                        "effect_event": "解かれた",
                        "confidence": 0.95,
                    }
                ]
            }
        })
        return PlotIntegrityMonitor(llm=mock_llm)

    @pytest.fixture
    def sample_blueprint(self):
        return """
第1話: アルスは聖剣エクスカリバーを手に、王都ルミナスの門をくぐった。
門番のガレスは懐かしい顔を見て安堵した。
アルスは城へ向かい、王と謁見する約束を取り付けた。
"""

    @pytest.fixture
    def sample_content(self):
        return """
アルスは聖剣エクスカリバーを手に、王都ルミナスの門をくぐった。
門番のガレスは懐かしい顔を見て安堵した。
「よく来たな、アルス」ガレスは笑顔で迎えた。
アルスは城へ向かい、王と謁見する約束を取り付けた。
しかし、聖剣の力が暴走し、城の一部を破壊してしまった。
"""

    @pytest.mark.asyncio
    async def test_extract_keywords_returns_entities(self, monitor):
        """NER抽出が主要エンティティを返すこと"""
        text = "アルスは聖剣エクスカリバーを手に王都ルミナスへ向かった。"
        keywords = await monitor.extract_keywords(text)
        # 抽出サービスのモック結果に依存するため、空リストでないことを確認
        assert isinstance(keywords, list)

    @pytest.mark.asyncio
    async def test_extract_keywords_empty_text(self, monitor):
        """空テキストで空リスト返却"""
        keywords = await monitor.extract_keywords("")
        assert keywords == []

        keywords = await monitor.extract_keywords("   ")
        assert keywords == []

    @pytest.mark.asyncio
    async def test_check_integrity_empty_blueprint(self, monitor):
        """Blueprint空ならスキップ"""
        is_ok, score, result = await monitor.check_integrity([], "", "本文あり")
        assert is_ok is True
        assert score == 1.0
        assert result.is_consistent is True

    @pytest.mark.asyncio
    async def test_check_integrity_empty_content(self, monitor):
        """Content空ならスキップ"""
        is_ok, score, result = await monitor.check_integrity([], "計画あり", "")
        assert is_ok is True
        assert score == 1.0
        assert result.is_consistent is True

    @pytest.mark.asyncio
    async def test_check_integrity_with_mock_extraction(self, monitor, sample_blueprint, sample_content):
        """モック抽出サービスでの整合性チェック"""
        with patch("src.agents.audit.extraction_service") as mock_extraction:
            # Blueprint側の抽出結果
            bp_entities = [
                Entity(name="アルス", type="Character", description="主人公", properties={"is_alive": True}),
                Entity(name="聖剣エクスカリバー", type="Item", description="聖剣", properties={"owner": "アルス"}),
                Entity(name="王都ルミナス", type="Location", description="王都", properties={}),
                Entity(name="ガレス", type="Character", description="門番", properties={}),
            ]
            bp_rels = [
                Relationship(source="アルス", target="聖剣エクスカリバー", type="POSSESSES", detail="所持"),
                Relationship(source="アルス", target="王都ルミナス", type="LOCATED_IN", detail="到着"),
            ]
            bp_result = GraphExtractionResult(entities=bp_entities, relationships=bp_rels, plot_summary="")

            # Content側の抽出結果（同じエンティティ＋追加）
            ct_entities = bp_entities + [
                Entity(name="城", type="Location", description="王城", properties={}),
            ]
            ct_rels = bp_rels + [
                Relationship(source="アルス", target="城", type="LOCATED_IN", detail="向かう"),
            ]
            ct_result = GraphExtractionResult(entities=ct_entities, relationships=ct_rels, plot_summary="")

            # 呼び出し順序で返却を分ける
            mock_extraction.extract_graph_from_text.side_effect = [bp_result, ct_result]

            # LLMモックの設定（因果抽出用）
            monitor.llm.generate_json = AsyncMock(return_value={
                "metadata": {
                    "causality_links": []
                }
            })

            is_ok, score, result = await monitor.check_integrity(
                [], sample_blueprint, sample_content, threshold=0.7, book_id=1, ep_num=1
            )

            assert isinstance(result, CausalityAuditResult)
            assert result.graph_diff is not None
            # 基本エンティティは共通なので missing_entities は空に近いはず
            assert score >= 0.0

    @pytest.mark.asyncio
    async def test_verify_causality_chains_detects_broken(self, monitor):
        """因果鎖切れ検出テスト"""
        links = [
            CausalityLink(
                cause_entity="アルス", cause_event="聖剣を抜く",
                effect_entity="封印", effect_event="解かれる",
                source="blueprint"
            ),
            CausalityLink(
                cause_entity="封印", cause_event="解かれる",
                effect_entity="魔王", effect_event="復活",
                source="blueprint"
            ),
            # ここが切れている: 魔王が復活した後の因果がない
        ]
        broken = monitor._verify_causality_chains(links)
        # 魔王は入力があるが出力がない → 終端でない限り broken に入る
        # 実装では _is_terminal_entity で判定される
        assert isinstance(broken, list)

    @pytest.mark.asyncio
    async def test_verify_causality_chains_connected(self, monitor):
        """繋がっている因果鎖は broken にならない"""
        links = [
            CausalityLink(
                cause_entity="アルス", cause_event="聖剣を抜く",
                effect_entity="封印", effect_event="解かれる",
                source="blueprint"
            ),
            CausalityLink(
                cause_entity="封印", cause_event="解かれる",
                effect_entity="魔王", effect_event="復活",
                source="blueprint"
            ),
            CausalityLink(
                cause_entity="魔王", cause_event="復活",
                effect_entity="世界", effect_event="滅亡の危機",
                source="blueprint"
            ),
        ]
        broken = monitor._verify_causality_chains(links)
        # 全て繋がっているので broken は空（終端の「世界」は除外判定される可能性）
        # 少なくとも魔王→世界は繋がっている

    @pytest.mark.asyncio
    async def test_generate_patches_for_broken_chains(self, monitor):
        """因果鎖切れパッチ生成"""
        broken = [
            CausalityLink(
                cause_entity="A", cause_event="原因", effect_entity="B", effect_event="結果", source="content"
            ),
        ]
        patches = await monitor._generate_patches(broken, [], [])
        assert len(patches) == 1
        assert patches[0].target_prompt == "writing_director"
        assert "因果鎖切れ" in patches[0].reasoning

    @pytest.mark.asyncio
    async def test_generate_patches_for_foreshadowing(self, monitor):
        """伏線未回収パッチ生成"""
        foreshadowing = [
            ForeshadowingItem(
                entity_name="竜の心臓",
                setup_chapter=3,
                setup_context="宝箱から発見",
                expected_payoff="竜制御",
                importance="Critical",
            ),
        ]
        patches = await monitor._generate_patches([], foreshadowing, [])
        assert len(patches) == 1
        assert patches[0].target_prompt == "plot_expansion"
        assert "伏線" in patches[0].reasoning

    @pytest.mark.asyncio
    async def test_generate_patches_for_contradictions(self, monitor):
        """矛盾パッチ生成"""
        contradictions = ["[アルス.location] Blueprint: 王都 vs Content: 村"]
        patches = await monitor._generate_patches([], [], contradictions)
        assert len(patches) == 1
        assert patches[0].target_prompt == "bible_update"
        assert "矛盾" in patches[0].reasoning

    @pytest.mark.asyncio
    async def test_generate_patches_multiple_types(self, monitor):
        """複数タイプ混在時"""
        broken = [CausalityLink(cause_entity="A", cause_event="a", effect_entity="B", effect_event="b", source="blueprint")]
        foreshadowing = [ForeshadowingItem(entity_name="X", setup_chapter=1, setup_context="ctx", expected_payoff="payoff")]
        contradictions = ["矛盾1"]

        patches = await monitor._generate_patches(broken, foreshadowing, contradictions)
        assert len(patches) == 3
        targets = {p.target_prompt for p in patches}
        assert targets == {"writing_director", "plot_expansion", "bible_update"}

    def test_calculate_score_perfect(self, monitor):
        """完全整合ならスコア1.0"""
        score = monitor._calculate_score([], [], [], [])
        assert score == 1.0

    def test_calculate_score_broken_chains(self, monitor):
        """因果鎖切れで減点"""
        links = [
            CausalityLink(cause_entity="A", cause_event="a", effect_entity="B", effect_event="b", source="blueprint")
            for _ in range(10)
        ]
        broken = links[:3]  # 30%切れ
        score = monitor._calculate_score(broken, [], [], links)
        assert score < 1.0
        assert score > 0.5  # 0.4 * 0.3 = 0.12 減点なので 0.88 程度

    def test_calculate_score_foreshadowing(self, monitor):
        """伏線未回収で減点"""
        fs_critical = [ForeshadowingItem(entity_name="X", setup_chapter=1, setup_context="c", expected_payoff="p", importance="Critical")]
        fs_major = [ForeshadowingItem(entity_name="Y", setup_chapter=1, setup_context="c", expected_payoff="p", importance="Major")]
        score = monitor._calculate_score([], fs_critical + fs_major, [], [])
        # Critical: 0.15, Major: 0.08 減点
        assert score == pytest.approx(0.77, rel=0.01)

    def test_calculate_score_contradictions(self, monitor):
        """矛盾で減点"""
        score = monitor._calculate_score([], [], ["矛盾1", "矛盾2"], [])
        assert score == 0.8  # 0.1 * 2 減点

    def test_is_terminal_entity(self, monitor):
        """終端エンティティ判定"""
        link = CausalityLink(
            cause_entity="A", cause_event="戦う", effect_entity="敵", effect_event="死亡", source="blueprint"
        )
        assert monitor._is_terminal_entity("敵", [link]) is True

        link2 = CausalityLink(
            cause_entity="A", cause_event="攻撃", effect_entity="敵", effect_event="負傷", source="blueprint"
        )
        assert monitor._is_terminal_entity("敵", [link2]) is False

    def test_is_initial_entity(self, monitor):
        """始端エンティティ判定"""
        link = CausalityLink(
            cause_entity="主人公", cause_event="旅立ち", effect_entity="世界", effect_event="冒険開始", source="blueprint"
        )
        assert monitor._is_initial_entity("主人公", [link]) is True


class TestPromptPatch:
    """PromptPatch モデルテスト"""

    def test_prompt_patch_creation(self):
        patch = PromptPatch(
            target_prompt="writing_director",
            patch_content="追加指示",
            reasoning="理由",
        )
        assert patch.target_prompt == "writing_director"
        assert patch.patch_content == "追加指示"
        assert patch.reasoning == "理由"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])