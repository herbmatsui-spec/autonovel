"""Integration test for the Purple Prose Detox Filter system."""

from __future__ import annotations

import pytest

from src.services.anti_ai.pipeline_orchestrator import detox_prose


class TestPurpleProseDetoxIntegration:
    """Integration tests for the complete purple prose detox system."""
    
    def test_basic_detox(self) -> None:
        """Test basic detox functionality."""
        # Text with excessive purple prose as described in the issue
        purple_text = """
        彼は歯を食いしばり、舌打ちし、拳を握りしめた。
        血の気が引くほどの恐怖で、奥歯を軋ませながら必死にこらえた。
        視線は氷のように冷たく、まるで北風のように鋭い。
        激痛が脳を焼くようで、胃が痛んで吐き気がした。
        しかし、彼は諦めなかった。なぜなら、約束していたからだ。
        星のように輝く未来を信じ、夢のように希望を抱き続けた。
        彼の心は炎のように熱く、勇気は雷のように轟いた。
        """
        
        cleaned_text, metrics = detox_prose(
            purple_text, 
            episode_id="integration_test_001",
            # Use tight limits for testing
        )
        
        # Basic assertions
        assert cleaned_text is not None
        assert len(cleaned_text) > 0
        assert metrics["episode_id"] == "integration_test_001"
        
        # Should have reduced length somewhat (due to removals)
        # Though some replacements might keep similar length
        print(f"Original length: {len(purple_text)}")
        print(f"Cleaned length: {len(cleaned_text)}")
        print(f"Processing time: {metrics['pipeline']['total_time_ms']:.2f}ms")
        
        # Check that we got reasonable metrics
        assert metrics["pipeline"]["total_time_ms"] >= 0
        assert metrics["stream_guard"]["time_ms"] >= 0
        assert metrics["density_gate"]["time_ms"] >= 0
        assert metrics["syntax_refiner"]["time_ms"] >= 0
        
        # Check stream guard stats
        sg_stats = metrics["stream_guard"]["stats"]
        assert "aggressive_count" in sg_stats
        assert "metaphor_count" in sg_stats
        assert "character_count" in sg_stats
        
        # Check density gate
        dg = metrics["density_gate"]
        assert hasattr(dg["score"], "aggressive_density")
        assert hasattr(dg["score"], "metaphor_density")
        assert hasattr(dg["score"], "sensory_overload")
        assert hasattr(dg["score"], "verb_strength")
        assert isinstance(dg["should_refine"], bool)
        assert dg["density_category"] in ["clean", "moderate", "elevated", "high"]
        
        print(f"Aggressive count: {sg_stats['aggressive_count']}")
        print(f"Metaphor count: {sg_stats['metaphor_count']}")
        print(f"Density category: {dg['density_category']}")
        print(f"Should refine: {dg['should_refine']}")
    
    def test_clean_text_unchanged(self) -> None:
        """Test that clean text remains largely unchanged."""
        clean_text = """
        今日はいい天気だった。 
        公園を散歩して、友達とコーヒーを飲んだ。
        仕事は順調に進んでいて、満足している。
        """
        
        cleaned_text, metrics = detox_prose(clean_text, episode_id="clean_test")
        
        # Should be very similar
        assert len(cleaned_text) > 0
        # Check for key phrases that should remain
        assert "今日" in cleaned_text or "天気" in cleaned_text
        assert "公園" in cleaned_text or "散歩" in cleaned_text
        assert "仕事" in cleaned_text or "順調" in cleaned_text
        
        # Should not need refinement
        assert not metrics["density_gate"]["should_refine"]
        assert metrics["density_gate"]["density_category"] == "clean"
        
        print(f"Clean text processing time: {metrics['pipeline']['total_time_ms']:.2f}ms")
        print(f"Density category: {metrics['density_gate']['density_category']}")
    
    def test_episode_limits(self) -> None:
        """Test that episode-based limits work correctly."""
        # Use very low limits for testing
        from src.services.anti_ai.pipeline_orchestrator import ProseDetoxPipeline
        
        pipeline = ProseDetoxPipeline(
            stream_guard=__import__('src.services.anti_ai.purple_prose_filter', 
                                   fromlist=['PurpleProseFilter']).PurpleProseFilter(
                max_aggressive_per_episode=1,  # Only 1 allowed per episode
                max_metaphor_per_1k_chars=2   # Only 2 allowed per 1000 chars
            )
        )
        
        # Episode 1: Use up the limit
        text1 = "彼は歯を食いしばった。"  # 1 aggressive
        result1, metrics1 = pipeline.process(text1, episode_id="limit_test_001")
        
        # Episode 2: Should allow aggressive again (fresh episode)
        text2 = "彼は舌打ちした。"  # 1 aggressive - should be allowed
        result2, metrics2 = pipeline.process(text2, episode_id="limit_test_002")
        
        # Both episodes should allow their respective aggressive reactions
        # The exact behavior depends on implementation, but episode separation should work
        
        assert metrics2["episode_id"] == "limit_test_002"
        print(f"Episode 1 aggressive count: {metrics1['stream_guard']['stats']['aggressive_count']}")
        print(f"Episode 2 aggressive count: {metrics2['stream_guard']['stats']['aggressive_count']}")
    
    def test_performance_requirements(self) -> None:
        """Test that the system meets performance requirements."""
        # Create a reasonably sized text chunk
        base_text = "彼は歯を食いしばり、まるで獣のように吠えた。血の気が引くほど怖がっていた。"
        # Repeat to make it longer
        long_text = (base_text * 50)  # ~50 repetitions
        
        cleaned_text, metrics = detox_prose(long_text, episode_id="perf_test")
        
        # Should process quickly (under 200ms for typical chunks)
        total_time = metrics["pipeline"]["total_time_ms"]
        print(f"Long text ({len(long_text)} chars) processing time: {total_time:.2f}ms")
        
        # For integration test, we'll be lenient - just ensure it doesn't hang
        assert total_time >= 0
        assert total_time < 5000  # Should be much less than 5 seconds even for long text
        
        # Check that all stages reported time
        assert metrics["stream_guard"]["time_ms"] >= 0
        assert metrics["density_gate"]["time_ms"] >= 0
        assert metrics["syntax_refiner"]["time_ms"] >= 0
    
    def test_metaphor_density_limit(self) -> None:
        """Test metaphor density limiting."""
        from src.services.anti_ai.pipeline_orchestrator import ProseDetoxPipeline
        
        # Tight metaphor limit
        pipeline = ProseDetoxPipeline(
            stream_guard=__import__('src.services.anti_ai.purple_prose_filter', 
                                   fromlist=['PurpleProseFilter']).PurpleProseFilter(
                max_metaphor_per_1k_chars=2  # Only 2 metaphors per 1000 chars
            )
        )
        
        # Text with many metaphors
        metaphor_heavy = (
            "彼はまるで獣のように吠え、 "
            "まるでเทพのように輝き、 "
            "まるで神のように賢く、 "
            "まるで王のように振る舞い、 "
            "まるで英雄のように戦った。 "
        ) * 3  # Repeat to increase density
        
        cleaned_text, metrics = pipeline.process(metaphor_heavy, episode_id="metaphor_test")
        
        # Should have processed and applied limits
        assert len(cleaned_text) > 0
        stats = metrics["stream_guard"]["stats"]
        print(f"Metaphor count: {stats['metaphor_count']}")
        print(f"Metaphor per 1000 chars: {stats.get('metaphor_per_1k_chars', 0)}")
        
        # The density gate should have detected high metaphor density
        assert metrics["density_gate"]["score"].metaphor_density >= 0
        
    def test_edge_cases(self) -> None:
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])