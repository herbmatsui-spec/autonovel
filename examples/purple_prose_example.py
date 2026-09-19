"""
Example usage of the Purple Prose Detox Filter.

This example demonstrates how to use the detox filter to clean up
excessive purple prose in generated text.
"""

import sys
import os
# Add the src directory to the Python path
# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to get to the project root, then to src
project_root = os.path.dirname(script_dir)
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

from src.services.anti_ai.pipeline_orchestrator import detox_prose

# Example 1: Basic usage
if __name__ == "__main__":
    # Text with excessive purple prose (as described in the issue)
    purple_text = """
    彼は歯を食いしばり、舌打ちし、拳を握りしめた。
    血の気が引くほどの恐怖で、奥歯を軋ませながら必死にこらえた。
    視線は氷のように冷たく、まるで北風のように鋭い。
    激痛が脳を焼くようで、胃が痛んで吐き気がした。
    しかし、彼は諦めなかった。なぜなら、約束していたからだ。
    星のように輝く未来を信じ、夢のように希望を抱き続けた。
    彼の心は炎のように熱く、勇気は雷のように轟いた。
    涙が川のように流れ、声は枯れ葉のようにかすれた。
    """
    
    print("=== Original Text (with purple prose) ===")
    print(purple_text.strip())
    print("\n" + "="*50 + "\n")
    
    # Process the text
    cleaned_text, metrics = detox_prose(
        purple_text,
        episode_id="example_001"
    )
    
    print("=== Cleaned Text (after detox) ===")
    print(cleaned_text.strip())
    print("\n" + "="*50 + "\n")
    
    print("=== Processing Metrics ===")
    print(f"Episode ID: {metrics['episode_id']}")
    print(f"Input length: {metrics['input_length']} characters")
    print(f"Output length: {metrics['output_length']} characters")
    print(f"Processing time: {metrics['pipeline']['total_time_ms']:.2f} ms")
    print(f"Latency target met: {metrics['pipeline']['meets_latency_target']}")
    print(f"Density category: {metrics['density_gate']['density_category']}")
    print(f"Should refine: = {metrics['density_gate']['should_refine']}")
    
    # Show stream guard statistics
    sg_stats = metrics['stream_guard']['stats']
    print(f"\nStream Guard Statistics:")
    print(f"  Aggressive reactions detected: {sg_stats['aggressive_count']}")
    print(f"  Metaphors detected: {sg_stats['metaphor_count']}")
    print(f"  Characters processed: {sg_stats['character_count']}")
    
    # Show density gate details
    dg_score = metrics['density_gate']['score']
    print(f"\nDensity Gate Scores:")
    print(f"  Aggressive density: {dg_score.aggressive_density:.2f} per 1000 chars")
    print(f"  Metaphor density: {dg_score.metaphor_density:.2f} per 1000 chars")
    print(f"  Sensory overload: {dg_score.sensory_overload:.2f}")
    print(f"  Verb strength: {dg_score.verb_strength:.2f}")
    
    print("\n" + "="*50)
    print("Example completed successfully!")


# Example 2: Using the pipeline directly for more control
def example_advanced_usage():
    """Example showing advanced usage with the pipeline directly."""
    # Add src to path for this function too
    sys.path.insert(0, src_path)
    from src.services.anti_ai.pipeline_orchestrator import ProseDetoxPipeline
    from src.services.anti_ai.purple_prose_filter import PurpleProseFilter
    
    # Create a pipeline with custom limits
    custom_pipeline = ProseDetoxPipeline(
        stream_guard=PurpleProseFilter(
            max_aggressive_per_episode=1,  # Very strict: only 1 aggressive reaction per episode
            max_metaphor_per_1k_chars=2    # Only 2 metaphors per 1000 chars
        )
    )
    
    text = """
    主人公は困難に直面した。彼は歯を食いしばり、舌打ちし、
    まるで獣のように怒りに震えた。血の気が引くほどの恐怖に
    さいなまれながら、しかし前に進むことを決意した。
    """
    
    # Process first chunk (episode 1)
    cleaned1, metrics1 = custom_pipeline.process(
        text, 
        episode_id="adv_example_001"
    )
    
    print("\n=== Advanced Example ===")
    print(f"Episode 1 - Aggressive count: {metrics1['stream_guard']['stats']['aggressive_count']}")
    
    # Process second chunk (episode 2) - should allow aggressive again
    text2 = "しかし新たな試練が待ち受けていた。さらに奥歯を軋ませた。"
    cleaned2, metrics2 = custom_pipeline.process(
        text2,
        episode_id="adv_example_002"
    )
    
    print(f"Episode 2 - Aggressive count: {metrics2['stream_guard']['stats']['aggressive_count']}")
    print("(Shows that limits reset between episodes)")


if __name__ == "__main__":
    example_advanced_usage()