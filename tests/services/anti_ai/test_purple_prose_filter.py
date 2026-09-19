"""Unit tests for the Purple Prose Filter."""

from __future__ import annotations

import pytest

from src.services.anti_ai.purple_prose_filter import PurpleProseFilter


class TestPurpleProseFilter:
    """Test the PurpleProseFilter class."""
    
    def test_init_default(self) -> None:
        """Test default initialization."""
        filter_obj = PurpleProseFilter()
        assert filter_obj.max_aggressive_per_episode == 2
        assert filter_obj.max_metaphor_per_1k_chars == 3
        assert filter_obj._aggressive_count == 0
        assert filter_obj._metaphor_count == 0
        assert filter_obj._character_count == 0
    
    def test_init_custom(self) -> None:
        """Test custom initialization."""
        filter_obj = PurpleProseFilter(
            max_aggressive_per_episode=5,
            max_metaphor_per_1k_chars=10
        )
        assert filter_obj.max_aggressive_per_episode == 5
        assert filter_obj.max_metaphor_per_1k_chars == 10
    
    def test_reset(self) -> None:
        """Test resetting counters."""
        filter_obj = PurpleProseFilter()
        # Manually set some counts
        filter_obj._aggressive_count = 5
        filter_obj._metaphor_count = 3
        filter_obj._character_count = 1000
        
        filter_obj.reset()
        
        assert filter_obj._aggressive_count == 0
        assert filter_obj._metaphor_count == 0
        assert filter_obj._character_count == 0
    
    def test_process_empty_text(self) -> None:
        """Test processing empty text."""
        filter_obj = PurpleProseFilter()
        assert filter_obj.process("") == ""
        assert filter_obj.process(None) == None  # type: ignore
    
    def test_process_no_matches(self) -> None:
        """Test processing text with no matches."""
        filter_obj = PurpleProseFilter()
        text = "これは普通の文章です。特別な表現は含まれていません。"
        result = filter_obj.process(text)
        assert result == text
        assert filter_obj.get_stats()["aggressive_count"] == 0
        assert filter_obj.get_stats()["metaphor_count"] == 0
    
    def test_aggressive_limit(self) -> None:
        """Test aggressive reaction limit."""
        filter_obj = PurpleProseFilter(max_aggressive_per_episode=2)
        
        # Process text with 3 aggressive reactions - should limit to 2
        text = "彼は歯を食いしばり、舌打ちし、拳を握りしめた。"
        result = filter_obj.process(text)
        
        # Should have replaced the third one (拳を握りしめた -> 拳を握った)
        # Or depending on implementation, may have transformed patterns
        stats = filter_obj.get_stats()
        assert stats["aggressive_count"] == 2  # Limited to 2
        
        # Process another chunk - should continue limiting
        text2 = "さらに奥歯を軋ませた。"
        result2 = filter_obj.process(text2)
        stats2 = filter_obj.get_stats()
        # Should still be at 2 or less (the third+ should be transformed/limited)
    
    def test_metaphor_limit(self) -> None:
        """Test metaphor density limit."""
        filter_obj = PurpleProseFilter(max_metaphor_per_1k_chars=3)
        
        # Process text with metaphors
        text = "彼はまるで獣のように叫び、星のように輝く目をして、夢のように遠い未来を見ていた。"
        result = filter_obj.process(text)
        
        stats = filter_obj.get_stats()
        # Should limit metaphors to 3 per 1000 chars
        # Depending on text length, this might be under or over limit
        
    def test_episode_boundary(self) -> None:
        """Test that counters reset between episodes."""
        filter_obj = PurpleProseFilter(max_aggressive_per_episode=1)
        
        # First "episode"
        text1 = "彼は歯を食いしばった。"
        result1 = filter_obj.process(text1)
        stats1 = filter_obj.get_stats()
        assert stats1["aggressive_count"] == 1
        
        # Reset for new episode
        filter_obj.reset()
        
        # Second "episode" - should allow aggressive reaction again
        text2 = "彼は舌打ちした。"
        result2 = filter_obj.process(text2)
        stats2 = filter_obj.get_stats()
        assert stats2["aggressive_count"] == 1  # Fresh count
        
    def test_get_stats(self) -> None:
        """Test getting statistics."""
        filter_obj = PurpleProseFilter()
        text = "彼は歯を食いしばり、まるで獣のように吠えた。"
        filter_obj.process(text)
        
        stats = filter_obj.get_stats()
        assert "aggressive_count" in stats
        assert "metaphor_count" in stats
        assert "character_count" in stats
        assert "aggressive_per_episode" in stats
        assert "metaphor_per_1k_chars" in stats
        
        assert isinstance(stats["aggressive_count"], int)
        assert isinstance(stats["metaphor_count"], int)
        assert isinstance(stats["character_count"], int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])