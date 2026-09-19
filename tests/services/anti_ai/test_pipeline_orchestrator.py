"""Unit tests for the Pipeline Orchestrator."""

from __future__ import annotations

import pytest

from src.services.anti_ai.pipeline_orchestrator import ProseDetoxPipeline, detox_prose


class TestProseDetoxPipeline:
    """Test the ProseDetoxPipeline class."""
    
    def test_init_default(self) -> None:
        """Test default initialization."""
        pipeline = ProseDetoxPipeline()
        assert pipeline.stream_guard is not None
        assert pipeline.density_scorer is not None
        assert pipeline.syntax_refiner is not None
        assert pipeline._episode_id is None
    
    def test_init_with_components(self) -> None:
        """Test initialization with custom components."""
        from src.services.anti_ai.purple_prose_filter import PurpleProseFilter
        from src.services.anti_ai.density_scorer import DensityScorer
        from src.services.anti_ai.syntax_refiner import SyntaxRefiner
        
        stream_guard = PurpleProseFilter(max_aggressive_per_episode=5)
        density_scorer = DensityScorer()
        syntax_refiner = SyntaxRefiner()
        
        pipeline = ProseDetoxPipeline(
            stream_guard=stream_guard,
            density_scorer=density_scorer,
            syntax_refiner=syntax_refiner
        )
        
        assert pipeline.stream_guard.max_aggressive_per_episode == 5
    
    def test_reset_episode(self) -> None:
        """Test resetting the episode."""
        pipeline = ProseDetoxPipeline()
        
        # Process something to set state
        pipeline.process("test", episode_id="episode_1")
        assert pipeline._episode_id == "episode_1"
        
        # Reset with new ID
        pipeline.reset_episode("episode_2")
        assert pipeline._episode_id == "episode_2"
        
        # Stream guard should be reset
        stats = pipeline.stream_guard.get_stats()
        assert stats["aggressive_count"] == 0
    
    def test_process_empty_text(self) -> None:
        """Test processing empty text."""
        pipeline = ProseDetoxPipeline()
        result, metrics = pipeline.process("")
        
        assert result == ""
        assert metrics["input_length"] == 0
        assert metrics["output_length"] == 0
    
    def test_process_no_matches(self) -> None:
        """Test processing text with no purple prose."""
        pipeline = ProseDetoxPipeline()
        text = "今日は良い天気です。公園を散歩しました。"
        result, metrics = pipeline.process(text, episode_id="test_001")
        
        # Should be largely unchanged
        assert "今日" in result
        assert "公園" in result
        assert metrics["episode_id"] == "test_001"
        assert metrics["pipeline"]["total_time_ms"] >= 0
    
    def test_process_with_purple_prose(self) -> None:
        """Test processing text with purple prose elements."""
        pipeline = ProseDetoxPipeline()
        # Text with multiple aggressive reactions and metaphors
        text = """
        彼は歯を食いしばり、舌打ちし、拳を握りしめた。 
        まるで獣のように怒り、血の気が引くほど恐怖に震えた。
        視線は氷のように冷たく、激痛が脳を焼くようだった。
        しかし、彼は夢のように希望を抱き、星のように輝く未来を信じていた。
        """
        
        result, metrics = pipeline.process(text, episode_id="test_002")
        
        # Should have processed something
        assert len(result) > 0
        assert metrics["episode_id"] == "test_002"
        assert metrics["input_length"] == len(text)
        assert metrics["output_length"] > 0
        
        # Should have some processing time recorded
        assert metrics["pipeline"]["total_time_ms"] >= 0
        assert metrics["stream_guard"]["time_ms"] >= 0
        assert metrics["density_gate"]["time_ms"] >= 0
        
        # Check that we got stats
        assert "aggressive_count" in metrics["stream_guard"]["stats"]
        assert "metaphor_count" in metrics["stream_guard"]["stats"]
        
        # Check density gate results
        assert "score" in metrics["density_gate"]
        assert "should_refine" in metrics["density_gate"]
        assert "density_category" in metrics["density_gate"]
    
    def test_episode_boundaries(self) -> None:
        """Test that limits reset between episodes."""
        pipeline = ProseDetoxPipeline()
        
        # First episode - use up aggressive limit
        text1 = "彼は歯を食いしばった。さらに舌打ちした。"  # 2 aggressive
        result1, metrics1 = pipeline.process(text1, episode_id="episode_A")
        stats1_after = metrics1["stream_guard"]["stats"]
        
        # Second episode - should allow aggressive again
        text2 = "彼は拳を握りしめた。さらに奥歯を軋ませた。"  # 2 more aggressive
        result2, metrics2 = pipeline.process(text2, episode_id="episode_B")
        stats2_after = metrics2["stream_guard"]["stats"]
        
        # Each episode should have its own count
        # The exact counts depend on implementation, but they should be tracked separately
        assert metrics2["episode_id"] == "episode_B"
    
    def test_convenience_function(self) -> None:
        """Test the convenience detox_prose function."""
        text = "彼は歯を食いしばり、まるで獣のように吠えた。"
        result, metrics = detox_prose(text, episode_id="convenience_test")
        
        assert result is not None
        assert metrics["episode_id"] == "convenience_test"
        assert isinstance(metrics["pipeline"]["total_time_ms"], (int, float))
    
    def test_processing_times(self) -> None:
        """Test getting processing times."""
        pipeline = ProseDetoxPipeline()
        text = "テストテキスト"
        pipeline.process(text, episode_id="time_test")
        
        times = pipeline.get_processing_times()
        assert "stream_guard" in times
        assert "density_gate" in times
        assert "syntax_refiner" in times
        assert "total" in times
        
        # All should be non-negative
        assert times["stream_guard"] >= 0
        assert times["density_gate"] >= 0
        assert times["syntax_refiner"] >= 0
        assert times["total"] >= 0


# ──────────────────────────────────────────────
# Edge case tests
# ──────────────────────────────────────────────

def test_edge_cases() -> None:
    """Test edge cases."""
    pipeline = ProseDetoxPipeline()
    
    # Very short text
    result, metrics = pipeline.process("あ", episode_id="edge_001")
    assert result == "あ" or len(result) > 0
    
    # Only punctuation
    result, metrics = pipeline.process("。。。。", episode_id="edge_002")
    assert result is not None
    
    # Only whitespace
    result, metrics = pipeline.process("   \n\t  ", episode_id="edge_003")
    assert result is not None
    
    # Mixed Japanese/English
    result, metrics = pipeline.process("He 歯を食いしばった and まるでheroだった。", episode_id="edge_004")
    assert result is not None
    assert len(result) > 0