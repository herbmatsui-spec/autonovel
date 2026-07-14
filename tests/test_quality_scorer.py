"""tests/test_quality_scorer.py - QualityScorer のテスト"""
import pytest

from src.services.quality_scorer import QualityScorer


class TestQualityScorer:
    """QualityScorer のテスト"""

    @pytest.fixture
    def scorer(self):
        """QualityScorerインスタンス"""
        return QualityScorer()

    @pytest.mark.asyncio
    async def test_score_coherence_good_text(self, scorer):
        """整合性スコア: 良いテキスト"""
        text = "しかし、状況は変わっていた。そのため、主人公は決意を固めた。こうして、物語は動き出す。"
        score = await scorer.score_coherence(text)
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_score_coherence_short_text(self, scorer):
        """整合性スコア: 短いテキスト"""
        text = "短いテキスト"
        score = await scorer.score_coherence(text)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_score_coherence_empty_text(self, scorer):
        """整合性スコア: 空テキスト"""
        score = await scorer.score_coherence("")
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_score_character_consistency(self, scorer):
        """キャラクター一貫性スコア"""
        text = "太郎は走った。花子は笑った。次郎は驚いた。すべての人が集まった。"
        score = await scorer.score_character_consistency(text)
        assert score >= 0.75

    @pytest.mark.asyncio
    async def test_score_character_consistency_single(self, scorer):
        """キャラクター一貫性スコア: 単一キャラクター"""
        text = "主人公は走った。主人公は笑った。"
        score = await scorer.score_character_consistency(text)
        assert score < 0.8

    @pytest.mark.asyncio
    async def test_score_pacing(self, scorer):
        """ペーシングスコア"""
        text = "しかし突然、魔王が姿を現した。猛然と攻撃を開始したが、まだ決意は変わっていない。"
        score = await scorer.score_pacing(text)
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_score_hook_retention(self, scorer):
        """フック保持率スコア"""
        text = "一体どうなるのだろうか。主人公は気づく。すべてはこれから始まる。"
        score = await scorer.score_hook_retention(text)
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_score_emotional_resonance(self, scorer):
        """感情共鳴度スコア"""
        text = "しかし胸が痛む。喜びと悲しみがないまぜになる。 лицо に表情が浮かぶ。"
        score = await scorer.score_emotional_resonance(text)
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_score_commercial_viability(self, scorer):
        """商業的ポテンシャルスコア"""
        text = "最強の覇者が覚醒する。伝説の戦士が運命に立ち向かう。"
        score = await scorer.score_commercial_viability(text)
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_score_all(self, scorer):
        """全スコア一括算出"""
        text = "しかし、最強の戦士が姿を現した。太郎は驚きを隠せなかった。こうして、運命が始まる。"
        metrics = await scorer.score_all(text)
        
        assert metrics.coherence_score == await scorer.score_coherence(text)
        assert metrics.character_consistency == await scorer.score_character_consistency(text)
        assert metrics.pacing_score == await scorer.score_pacing(text)
        assert metrics.hook_retention == await scorer.score_hook_retention(text)
        assert metrics.emotional_resonance == await scorer.score_emotional_resonance(text)
        assert metrics.commercial_viability == await scorer.score_commercial_viability(text)