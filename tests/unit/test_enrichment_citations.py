# tests/unit/test_enrichment_citations.py
"""EnrichmentAgent 引用付与の単体テスト"""
import pytest
from src.agents.enrichment_agent import EnrichmentAgent


class TestCitationAttachment:
    """引用付与機能のテスト"""

    @pytest.fixture
    def agent(self):
        agent = EnrichmentAgent()
        # モック Bible 索引
        agent._bible_index = {
            "魔法システム": [{"source": "世界観設定書・巻I", "page": "p.23", "category": "magic"}],
            "MP": [{"source": "世界観設定書・巻I", "page": "p.24", "category": "magic"}],
            "剣": [{"source": "世界観設定書・巻II", "page": "p.45", "category": "item"}],
            "聖剣エクスカリバー": [{"source": "世界観設定書・巻III", "page": "p.100", "category": "item"}],
        }
        return agent

    def test_extract_factual_claims_basic(self, agent):
        """基本的な事実記述抽出"""
        text = "主人公は魔法システムAを使って戦った。MPを10消費した。"
        claims = agent._extract_factual_claims(text)
        assert len(claims) >= 1
        # 位置情報がある
        for claim in claims:
            assert "position" in claim
            assert "end_position" in claim
            assert "text" in claim

    def test_extract_factual_claims_multiple(self, agent):
        """複数の事実記述"""
        text = "魔法システムAはMPを消費する。聖剣エクスカリバーは光る。剣で敵を倒した。"
        claims = agent._extract_factual_claims(text)
        assert len(claims) >= 2

    def test_match_claims_to_sources_exact(self, agent):
        """完全一致マッチング"""
        claims = [
            {"text": "魔法システムAはMPを10消費する", "position": 0, "end_position": 19},
            {"text": "主人公の剣が光った", "position": 20, "end_position": 30},
        ]
        pairs = agent._match_claims_to_sources(claims)
        assert len(pairs) >= 1
        for pair in pairs:
            assert "source" in pair
            assert "score" in pair
            assert pair["score"] >= 0.5

    def test_match_claims_to_sources_no_match(self, agent):
        """マッチしない場合"""
        claims = [
            {"text": "全く関係ない事実", "position": 0, "end_position": 10},
        ]
        pairs = agent._match_claims_to_sources(claims)
        assert len(pairs) == 0

    def test_insert_footnote_markers(self, agent):
        """脚注マーカー挿入"""
        text = "魔法システムAを使った。MPを消費した。"
        pairs = [
            {"claim": "魔法システムAを使った", "position": 0, "end_position": 10, 
             "source": {"source": "世界観設定書・巻I", "page": "p.23"}, "score": 0.8},
            {"claim": "MPを消費した", "position": 11, "end_position": 18,
             "source": {"source": "世界観設定書・巻I", "page": "p.24"}, "score": 0.7},
        ]
        enriched, meta = agent._insert_footnote_markers(text, pairs)
        assert "[^1]" in enriched
        assert "[^2]" in enriched
        assert len(meta) == 2
        assert meta[0]["marker"] == 1
        assert meta[1]["marker"] == 2

    def test_insert_footnote_markers_dedupe_same_source(self, agent):
        """同一ソースは同一番号"""
        text = "魔法システムAを使った。魔法システムAは強力だ。"
        pairs = [
            {"claim": "魔法システムAを使った", "position": 0, "end_position": 10,
             "source": {"source": "世界観設定書・巻I", "page": "p.23"}, "score": 0.8},
            {"claim": "魔法システムAは強力だ", "position": 11, "end_position": 21,
             "source": {"source": "世界観設定書・巻I", "page": "p.23"}, "score": 0.7},
        ]
        enriched, meta = agent._insert_footnote_markers(text, pairs)
        assert enriched.count("[^1]") == 2
        assert "[^2]" not in enriched
        assert len(meta) == 2
        assert meta[0]["marker"] == 1
        assert meta[1]["marker"] == 1

    def test_format_citations_footnote(self, agent):
        """脚注スタイルフォーマット"""
        text = "魔法システムAを使った[^1]。"
        meta = [
            {"marker": 1, "claim": "魔法システムAを使った", 
             "source": {"source": "世界観設定書・巻I", "page": "p.23"}, "score": 0.8},
        ]
        formatted = agent._format_citations(text, meta, "footnote")
        assert "【参考文献】" in formatted
        assert "[^1] 世界観設定書・巻I p.23" in formatted

    def test_format_citations_bracket(self, agent):
        """括弧スタイル（マーカーのみ）"""
        text = "魔法システムAを使った[^1]。"
        meta = [{"marker": 1, "claim": "テスト", "source": {"source": "テスト"}, "score": 0.8}]
        formatted = agent._format_citations(text, meta, "bracket")
        assert formatted == text  # 変更なし

    def test_format_citations_endnote(self, agent):
        """後注スタイル（脚注と同じ）"""
        text = "テスト[^1]。"
        meta = [{"marker": 1, "claim": "テスト", "source": {"source": "テスト"}, "score": 0.8}]
        formatted = agent._format_citations(text, meta, "endnote")
        assert "【参考文献】" in formatted