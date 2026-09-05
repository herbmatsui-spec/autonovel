# tests/unit/test_enrichment_trivia.py
"""EnrichmentAgent トリビア挿入の単体テスト"""
import pytest
from src.agents.enrichment_agent import EnrichmentAgent


class TestTriviaInsertion:
    """トリビア挿入機能のテスト"""

    @pytest.fixture
    def agent(self):
        return EnrichmentAgent()

    def test_find_insertion_points_paragraph_breaks(self, agent):
        """段落区切りでの挿入ポイント検出"""
        text = "第一段落です。\n\n第二段落です。\n\n第三段落です。"
        points = agent._find_insertion_points(text, 3)
        assert len(points) == 3
        # 先頭(0)と各段落区切り付近
        assert 0 in points
        assert points[1] > 0
        assert points[2] > points[1]

    def test_find_insertion_points_sentence_ends(self, agent):
        """文末での挿入ポイント検出（段落区切りがない場合）"""
        text = "第一文です。第二文です。第三文です。"
        points = agent._find_insertion_points(text, 3)
        assert len(points) <= 3
        # 先頭(0)を含む
        assert 0 in points
        # 残りは文末付近
        for p in points[1:]:
            assert text[max(0, p-5):p] in ["。", "！", "？"] or p == len(text)

    def test_find_insertion_points_evenly_spaced(self, agent):
        """等間隔フォールバック"""
        text = "あ" * 1000  # 句読点なし
        points = agent._find_insertion_points(text, 5)
        assert len(points) == 5
        # 概ね等間隔
        for i in range(1, len(points)):
            diff = points[i] - points[i-1]
            assert 150 < diff < 250  # 1000/5=200 前後

    def test_score_trivia_relevance_exact_match(self, agent):
        """完全一致で高スコア"""
        trivia = {"fact": "魔法システムAはMPを10消費する", "source_type": "world_bible", "entity": "魔法システムA"}
        context = "主人公は魔法システムAを使って戦った。MPが減った。"
        score = agent._score_trivia_relevance(trivia, context)
        assert score > 0.5  # エンティティマッチでボーナス

    def test_score_trivia_relevance_no_match(self, agent):
        """無関連で低スコア"""
        trivia = {"fact": "遠い国の歴史", "source_type": "historical_facts", "entity": "遠い国"}
        context = "主人公は魔法システムAを使って戦った。"
        score = agent._score_trivia_relevance(trivia, context)
        assert score < 0.3

    def test_score_trivia_relevance_source_weight(self, agent):
        """ソースタイプによる重み付け"""
        trivia_wb = {"fact": "テスト事実", "source_type": "world_bible", "entity": ""}
        trivia_hist = {"fact": "テスト事実", "source_type": "historical_facts", "entity": ""}
        trivia_cult = {"fact": "テスト事実", "source_type": "cultural_trivia", "entity": ""}
        context = "テスト事実について"
        
        score_wb = agent._score_trivia_relevance(trivia_wb, context)
        score_hist = agent._score_trivia_relevance(trivia_hist, context)
        score_cult = agent._score_trivia_relevance(trivia_cult, context)
        
        assert score_wb >= score_hist >= score_cult

    def test_extract_scene_context(self, agent):
        """シーン文脈抽出"""
        text = "主人公は剣を構えた。敵が迫る。"
        writing_context = {"location": "決戦の野", "characters": ["主人公", "敵将軍"]}
        context = agent._extract_scene_context(text, writing_context)
        assert "決戦の野" in context
        assert "主人公" in context
        assert "敵将軍" in context

    def test_extract_entities(self, agent):
        """エンティティ抽出"""
        writing_context = {
            "characters": ["主人公", "ヒロイン"],
            "location": "王都",
            "key_items": ["聖剣", "魔導書"]
        }
        entities = agent._extract_entities(writing_context)
        assert "主人公" in entities
        assert "ヒロイン" in entities
        assert "王都" in entities
        assert "聖剣" in entities
        assert "魔導書" in entities
        # 重複なし
        assert len(entities) == len(set(entities))