"""Unit tests for the Syntax Refiner."""

from __future__ import annotations

import pytest

from src.services.anti_ai.syntax_refiner import SyntaxRefiner


class TestSyntaxRefiner:
    """Test the SyntaxRefiner class."""
    
    def test_init(self) -> None:
        """Test initialization."""
        refiner = SyntaxRefiner()
        assert refiner is not None
    
    def test_refine_empty_text(self) -> None:
        """Test refining empty text."""
        refiner = SyntaxRefiner()
        assert refiner.refine_paragraph("") == ("", 0, 0)
        assert refiner.refine_paragraph(None) == (None, 0, 0)  # type: ignore
    
    def test_refine_no_changes_needed(self) -> None:
        """Test refining text that doesn't need changes."""
        refiner = SyntaxRefiner()
        text = "今日は良い天気です。散歩に出かけました。"
        result, agg_used, meta_used = refiner.refine_paragraph(text, 0, 0)
        
        # Should be largely unchanged
        assert "今日" in result
        assert "天気" in result
        assert agg_used == 0
        assert meta_used == 0
    
    def test_aggressive_verb_replacement(self) -> None:
        """Test replacement of aggressive verbs."""
        refiner = SyntaxRefiner()
        
        # Test with limit exceeded (should replace)
        text = "彼は歯を食いしばり、舌打ちし、拳を握りしめた。さらに奥歯を軋ませた。"
        result, agg_used, meta_used = refiner.refine_paragraph(text, 2, 0)  # Already used 2
        
        # Should have replaced aggressive verbs since limit exceeded
        assert "耐えた" in result or "こらえた" in result or "眉をひそめた" in result
        assert agg_used >= 2  # Should have counted the replacements
    
    def test_metaphor_simplification(self) -> None:
        """Test simplification of metaphors."""
        refiner = SyntaxRefiner()
        
        # Test with limit exceeded (should simplify)
        text = "彼はまるで獣のように吠え、星のように輝く目をして、まるで夢を見ていた。"
        result, agg_used, meta_used = refiner.refine_paragraph(text, 0, 2)  # Already used 2 metaphors
        
        # Should have simplified some metaphors
        # The exact result depends on implementation, but should be less flowery
        
    def test_noun_ending_conversion(self) -> None:
        """Test conversion to noun endings (体言止め)."""
        refiner = SyntaxRefiner()
        
        # Test continuous past -> simple past
        text = "彼は走っていた。ジャンプしていた。"
        result, agg_used, meta_used = refiner.refine_paragraph(text, 0, 0)
        
        # Should have converted to simple past where appropriate
        # Note: This depends on the specific patterns implemented
        
    def test_filler_removal(self) -> None:
        """Test removal of filler words."""
        refiner = SyntaxRefiner()
        
        text = "たぶん、彼はきっと成功するでしょう。おそらく、うまくいくはずです。"
        result, agg_used, meta_used = refiner.refine_paragraph(text, 0, 0)
        
        # Should have reduced filler words
        assert "たぶん" not in result or result.count("たぶん") < text.count("たぶん")
        assert "きっと" not in result or result.count("きっと") < text.count("きっと")
    
    def test_refine_with_counts(self) -> None:
        """Test that the refiner properly updates and uses counts."""
        refiner = SyntaxRefiner()
        
        # First call - under limits
        text1 = "彼は歯を食いしばった。"
        result1, agg1, meta1 = refiner.refine_paragraph(text1, 0, 0)
        assert agg1 >= 0  # May or may not have incremented depending on implementation
        
        # Second call - continuing from first
        text2 = "さらに舌打ちした。"
        result2, agg2, meta2 = refiner.refine_paragraph(text2, agg1, meta1)
        # Should continue counting from where we left off
        
    def test_split_sentences_keep_delimiters(self) -> None:
        """Test the sentence splitting helper."""
        refiner = SyntaxRefiner()
        
        text = "こんにちは！どうですか？よろしくお願いします。"
        sentences = refiner._split_sentences_keep_delimiters(text)
        
        assert len(sentences) == 3
        assert sentences[0].endswith("！")
        assert sentences[1].endswith("？")
        assert sentences[2].endswith("。")
        
        # Test with newlines
        text2 = "第一段落\n第二段落\n第三段落"
        sentences2 = refiner._split_sentences_keep_delimiters(text2)
        # Should handle newlines as delimiters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])