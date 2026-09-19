"""Pipeline orchestrator for the Purple Prose Detox Filter.

Coordinates the stream guard, density gate, and syntax refiner
to provide a multi-layered defense against purple prose.
"""

from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

from src.services.anti_ai.density_scorer import DensityScore, DensityScorer
from src.services.anti_ai.purple_prose_filter import PurpleProseFilter
from src.services.anti_ai.syntax_refiner import SyntaxRefiner


class ProseDetoxPipeline:
    """Multi-stage pipeline for purple prose detoxification.
    
    Stages:
    1. Stream Guard: Fast regex-based filtering with episode limits
    2. Density Gate: Paragraph scoring to determine when to refine
    3. Syntax Refiner: Sentence-level refinement for flagged content
    """
    
    def __init__(
        self,
        stream_guard: Optional[PurpleProseFilter] = None,
        density_scorer: Optional[DensityScorer] = None,
        syntax_refiner: Optional[SyntaxRefiner] = None,
        aggressive_threshold: float = 2.0,
        metaphor_threshold: float = 3.0,
        sensory_threshold: float = 0.5,
        verb_strength_threshold: float = 0.3,
    ) -> None:
        """Initialize the pipeline.
        
        Args:
            stream_guard: Stream guard filter (creates default if None)
            density_scorer: Density scorer (creates default if None)
            syntax_refiner: Syntax refiner (creates default if None)
            aggressive_threshold: Aggressive reactions per 1000 chars threshold
            metaphor_threshold: Metaphors per 1000 chars threshold
            sensory_threshold: Sensory overload threshold (0-1)
            verb_strength_threshold: Verb strength threshold (0-1)
        """
        self.stream_guard = stream_guard or PurpleProseFilter()
        self.density_scorer = density_scorer or DensityScorer()
        self.syntax_refiner = syntax_refiner or SyntaxRefiner()
        
        self.aggressive_threshold = aggressive_threshold
        self.metaphor_threshold = metaphor_threshold
        self.sensory_threshold = sensory_threshold
        self.verb_strength_threshold = verb_strength_threshold
        
        # Pipeline state
        self._episode_id: Optional[str] = None
        self._processing_times: Dict[str, float] = {}
    
    def reset_episode(self, episode_id: str) -> None:
        """Reset pipeline for a new episode.
        
        Args:
            episode_id: Unique identifier for the episode
        """
        self._episode_id = episode_id
        self.stream_guard.reset()
        self._processing_times = {}
    
    def process(
        self, 
        text: str, 
        episode_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Tuple[str, Dict]:
        """Process text through the full detox pipeline.
        
        Args:
            text: Input text to process
            episode_id: Episode identifier for limit tracking
            metadata: Optional metadata (user plan, episode tags, etc.)
            
        Returns:
            Tuple of (processed_text, pipeline_metrics)
        """
        if not text:
            return text, self._get_empty_metrics()
        
        # Set episode ID if provided
        if episode_id is not None:
            if self._episode_id != episode_id:
                self.reset_episode(episode_id)
        elif self._episode_id is None:
            # Generate a default episode ID if none provided
            self._episode_id = f"episode_{int(time.time())}"
            self.stream_guard.reset()
        
        metadata = metadata or {}
        start_time = time.time()
        
        # Stage 1: Stream Guard (fast, always-on)
        stage1_start = time.time()
        stream_filtered = self.stream_guard.process(text)
        stage1_time = (time.time() - stage1_start) * 1000  # ms
        
        # Stage 2: Density Gate (check if we need refinement)
        stage2_start = time.time()
        score = self.density_scorer.score_paragraph(stream_filtered)
        should_refine = self.density_scorer.should_simplify(
            score,
            self.aggressive_threshold,
            self.metaphor_threshold,
            self.sensory_threshold,
            self.verb_strength_threshold
        )
        stage2_time = (time.time() - stage2_start) * 1000  # ms
        
        # Stage 3: Syntax Refiner (conditional, slower)
        stage3_time = 0.0
        syntax_refined = stream_filtered
        
        if should_refine:
            stage3_start = time.time()
            # Get current counts from stream guard for context
            stats = self.stream_guard.get_stats()
            syntax_refined, _, _ = self.syntax_refiner.refine_paragraph(
                stream_filtered,
                stats["aggressive_count"],
                stats["metaphor_count"]
            )
            stage3_time = (time.time() - stage3_start) * 1000  # ms
        
        total_time = (time.time() - start_time) * 1000  # ms
        
        # Update processing times
        self._processing_times = {
            "stream_guard": stage1_time,
            "density_gate": stage2_time,
            "syntax_refiner": stage3_time,
            "total": total_time
        }
        
        # Prepare metrics
        metrics = {
            "episode_id": self._episode_id,
            "input_length": len(text),
            "output_length": len(syntax_refined),
            "stream_guard": {
                "time_ms": stage1_time,
                "stats": self.stream_guard.get_stats()
            },
            "density_gate": {
                "time_ms": stage2_time,
                "score": score,
                "should_refine": should_refine,
                "density_category": self.density_scorer.get_density_category(score)
            },
            "syntax_refiner": {
                "time_ms": stage3_time,
                "applied": should_refine
            },
            "pipeline": {
                "total_time_ms": total_time,
                "meets_latency_target": total_time < 200  # 200ms target
            }
        }
        
        if metadata:
            metrics["metadata"] = metadata
            
        return syntax_refined, metrics
    
    def _get_empty_metrics(self) -> Dict:
        """Get empty metrics structure for empty input."""
        return {
            "episode_id": self._episode_id,
            "input_length": 0,
            "output_length": 0,
            "stream_guard": {"time_ms": 0.0, "stats": {}},
            "density_gate": {"time_ms": 0.0, "score": DensityScore(), "should_refine": False},
            "syntax_refiner": {"time_ms": 0.0, "applied": False},
            "pipeline": {"total_time_ms": 0.0, "meets_latency_target": True}
        }
    
    def get_processing_times(self) -> Dict[str, float]:
        """Get the last recorded processing times.
        
        Returns:
            Dictionary with processing times for each stage in milliseconds
        """
        return self._processing_times.copy()


# Convenience function for simple usage
def detox_prose(
    text: str, 
    episode_id: str = "default",
    **kwargs
) -> Tuple[str, Dict]:
    """Convenience function for one-off prose detoxification.
    
    Args:
        text: Input text to process
        episode_id: Episode identifier
        **kwargs: Additional arguments passed to ProseDetoxPipeline
        
    Returns:
        Tuple of (processed_text, metrics)
    """
    pipeline = ProseDetoxPipeline(**kwargs)
    return pipeline.process(text, episode_id)


if __name__ == "__main__":
    # Simple test
    test_text = """
    彼は歯を食いしばり、まるで獣のように怒りに震えた。 
    血の気が引くほどの恐怖で、奥歯を軋ませながら必死にこらえた。
    視線は氷のように冷たく、激痛が脳を焼くようだった。
    しかし、彼は諦めなかった。なぜなら、約束していたからだ。
    """
    
    processed, metrics = detox_prose(test_text, episode_id="test_001")
    print("Original:")
    print(test_text)
    print("\nProcessed:")
    print(processed)
    print("\nMetrics:")
    print(f"Total time: {metrics['pipeline']['total_time_ms']:.2f}ms")
    print(f"Density category: {metrics['density_gate']['density_category']}")