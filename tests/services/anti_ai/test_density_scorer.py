"""Unit tests for the Density Scorer."""

from __future__ import annotations

import pytest

from src.services.anti_ai.density_scorer import DensityScorer, DensityScore


class TestDensityScorer:
    """Test the DensityScorer class."""
    
    def test_score_empty_text(self) -> None:
        """Test scoring empty text."""
        score = DensityScorer.score_paragraph("")
        assert score.aggressive_density == 0.0
        assert score.metaphor_density == 0.0
        assert score.sensory_overload == 0.0
        assert score.verb_strength == 0.0
        
        score = DensityScorer.score_paragraph(None)  # type: ignore
        assert score.aggressive_density == 0.0
    
    def test_score_no_matches(self) -> None:
        """Test scoring text with no special patterns."""
        text = "これは普通の文章です。今日はいい天気ですね。"
        score = DensityScorer.score_paragraph(text)
        
        assert score.aggressive_density == 0.0
        assert score.metaphor_density == 0.0
        assert score.sensory_overload >= 0.0
        assert score.verb_strength >= 0.0
    
    def test_score_aggressive_density(self) -> None:
        """Test scoring aggressive reaction density."""
        # Text with 2 aggressive reactions in 100 chars
        text = "彼は歯を食いしばり、舌打ちした。" + "あ" * 80  # ~100 chars total
        
        score = DensityScorer.score_paragraph(text)
        # 2 aggressive reactions in ~100 chars = 20 per 1000 chars
        assert score.aggressive_density > 10.0  # Allow some variance
        assert score.aggressive_density < 40.0
    
    def test_score_metaphor_density(self) -> None:
        """Test scoring metaphor density."""
        # Text with metaphor markers
        text = "彼はまるで獣のように叫び、星のように輝き、夢のように願った。" + "あ" * 100
        
        score = DensityScorer.score_paragraph(text)
        # Should detect some metaphor density
        assert score.metaphor_density > 10.0
        assert score.metaphor_density < 50.0
    
    def test_score_sensory_overload(self) -> None:
        """Test scoring sensory overload."""
        # Test that the score is in valid range [0, 1]
        text = "彼は視線を輝かせ、光を見つめ、色を眺め、影を追いかけた。" + "あ" * 50
        score = DensityScorer.score_paragraph(text)
        # Should have some sensory overload for visual-heavy text
        assert 0.0 <= score.sensory_overload <= 1.0
        
        # Text with mixed senses
        mixed = "彼は音を聞き、匂いをかぎ、触れて、味わった。" + "あ" * 50
        score2 = DensityScorer.score_paragraph(mixed)
        # Should have valid sensory overload
        assert 0.0 <= score2.sensory_overload <= 1.0
    
    def test_score_verb_strength(self) -> None:
        """Test scoring verb strength/diversity."""
        # Text with varied verbs
        varied_verbs = "彼は走った。跳んだ。叫んだ。笑った。泣いた。"
        score = DensityScorer.score_paragraph(varied_verbs)
        
        # Text with repeated same verb
        repeated_verb = "彼は走った。走った。走った。走った。走った。"
        score2 = DensityScorer.score_paragraph(repeated_verb)
        
        # Varied verbs should have higher verb strength
        assert score.verb_strength >= score2.verb_strength
        assert 0.0 <= score.verb_strength <= 1.0
        assert 0.0 <= score2.verb_strength <= 1.0
    
    def test_should_simplify(self) -> None:
        """Test the should_simplify decision function."""
        # Score well under thresholds
        low_score = DensityScore(aggressive_density=0.5, metaphor_density=0.5, 
                                sensory_overload=0.1, verb_strength=0.8)
        assert not DensityScorer.should_simplify(low_score)
        
        # Score over aggressive threshold
        high_aggressive = DensityScore(aggressive_density=3.0, metaphor_density=1.0, 
                                      sensory_overload=0.1, verb_strength=0.8)
        assert DensityScorer.should_simplify(high_aggressive)
        
        # Score over metaphor threshold
        high_metaphor = DensityScore(aggressive_density=1.0, metaphor_density=4.0, 
                                    sensory_overload=0.1, verb_strength=0.8)
        assert DensityScorer.should_simplify(high_metaphor)
        
        # Score over sensory threshold
        high_sensory = DensityScore(aggressive_density=1.0, metaphor_density=1.0, 
                                   sensory_overload=0.6, verb_strength=0.8)
        assert DensityScorer.should_simplify(high_sensory)
        
        # Score under verb strength threshold
        low_verb = DensityScore(aggressive_density=1.0, metaphor_density=1.0, 
                               sensory_overload=0.1, verb_strength=0.2)
        assert DensityScorer.should_simplify(low_verb)
    
    def test_get_density_category(self) -> None:
        """Test density categorization."""
        # Clean text
        clean_score = DensityScore(aggressive_density=0.5, metaphor_density=0.5, 
                                  sensory_overload=0.1, verb_strength=0.8)
        assert DensityScorer.get_density_category(clean_score) == "clean"
        
        # Moderate (1 risk factor)
        mod_score = DensityScore(aggressive_density=1.5, metaphor_density=0.5, 
                                sensory_overload=0.1, verb_strength=0.8)
        assert DensityScorer.get_density_category(mod_score) == "moderate"
        
        # Elevated (2 risk factors)
        elev_score = DensityScore(aggressive_density=1.5, metaphor_density=2.0, 
                                 sensory_overload=0.1, verb_strength=0.8)
        assert DensityScorer.get_density_category(elev_score) == "elevated"
        
        # High (3+ risk factors)
        high_score = DensityScore(aggressive_density=1.5, metaphor_density=2.0, 
                                 sensory_overload=0.4, verb_strength=0.2)
        assert DensityScorer.get_density_category(high_score) == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])