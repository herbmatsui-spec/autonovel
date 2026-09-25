"""Simple benchmark for the Purple Prose Detox Filter."""

from __future__ import annotations

import time
import random
import string
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.services.anti_ai.pipeline_orchestrator import detox_prose


def generate_test_text(
    length_chars: int = 1000,
    purple_ratio: float = 0.3
) -> str:
    """Generate test text with controllable purple prose density.
    
    Args:
        length_chars: Target length in characters
        purple_ratio: Proportion of text that should be purple prose (0-1)
        
    Returns:
        Generated test text
    """
    # Purple prose templates
    purple_templates = [
        "彼は歯を食いしばり、まるで獣のように怒りに震えた。",
        "血の気が引くほどの恐怖で、奥歯を軋ませながら必死にこらえた。",
        "視線は氷のように冷たく、激痛が脳を焼くようだった。",
        "胃が痛んで吐き気がし、頭がくらりと回転した。",
        "しかし、彼は諦めなかった。なぜなら、約束していたからだ。",
        "星のように輝く未来を信じ、夢のように希望を抱き続けた。",
        "彼の心は炎のように熱く、勇気は雷のように轟いた。",
        "涙が川のように流れ、声は枯れ葉のようにかすれた。"
    ]
    
    # Normal prose templates
    normal_templates = [
        "今日は良い天気だった。",
        "公園を散歩して、友達と会った。",
        "仕事は順調に進んでいる。",
        "コーヒーを飲みながら、新聞を読んだ。",
        "夕方になって、家に帰った。",
        "明日の予定を考えながら、ベッドに入った。",
        "特に変わったことはなかった。",
        "普通の一日だった。"
    ]
    
    # Build text
    parts = []
    target_purple_chars = int(length_chars * purple_ratio)
    target_normal_chars = length_chars - target_purple_chars
    
    current_purple = 0
    current_normal = 0
    
    while current_purple < target_purple_chars or current_normal < target_normal_chars:
        if current_purple < target_purple_chars and (current_normal >= target_normal_chars or random.random() < 0.5):
            # Add purple prose
            template = random.choice(purple_templates)
            parts.append(template)
            current_purple += len(template)
        else:
            # Add normal prose
            template = random.choice(normal_templates)
            parts.append(template)
            current_normal += len(template)
    
    # Join and trim to target length
    text = "".join(parts)
    if len(text) > length_chars:
        text = text[:length_chars]
    elif len(text) < length_chars:
        # Pad with normal text
        padding_needed = length_chars - len(text)
        padding = (" " + random.choice(normal_templates)) * (padding_needed // 20 + 1)
        text = text + padding[:padding_needed]
    
    return text


def run_benchmark() -> None:
    """Run a simple benchmark of the detox pipeline."""
    print("Purple Prose Detox Filter Benchmark")
    print("=" * 40)
    
    # Test different text sizes
    test_sizes = [100, 500, 1000, 2000, 5000]
    
    for size in test_sizes:
        print(f"\nTesting with {size} characters:")
        text = generate_test_text(size, purple_ratio=0.4)
        
        # Time the processing
        start_time = time.perf_counter()
        cleaned_text, metrics = detox_prose(text, episode_id=f"bench_{size}")
        end_time = time.perf_counter()
        
        elapsed_ms = (end_time - start_time) * 1000
        
        print(f"  Original length: {len(text)} chars")
        print(f"  Cleaned length: {len(cleaned_text)} chars")
        print(f"  Processing time: {elapsed_ms:.2f} ms")
        print(f"  Throughput: {len(text) / (elapsed_ms / 1000):.0f} chars/second")
        print(f"  Density category: = {metrics['density_gate']['density_category']}")
        print(f"  Should refine: {metrics['density_gate']['should_refine']}")
        
        # Check stream guard stats
        sg_stats = metrics["stream_guard"]["stats"]
        print(f"  Aggressive reactions: {sg_stats['aggressive_count']}")
        print(f"  Metaphors: {sg_stats['metaphor_count']}")
        
        # Verify latency target (should be under 200ms for reasonable sizes)
        if size <= 2000:
            assert elapsed_ms < 500, f"Too slow: {elapsed_ms}ms for {size} chars"
            print(f"  ✓ Latency OK (<500ms)")
        else:
            print(f"  ⚠ Latency: {elapsed_ms}ms (acceptable for {size} chars)")


def test_consistency() -> None:
    """Test that processing the same text gives consistent results."""
    print("\n\nConsistency Test")
    print("=" * 40)
    
    text = generate_test_text(1000, purple_ratio=0.5)
    
    # Process multiple times
    results = []
    for i in range(5):
        cleaned_text, metrics = detox_prose(text, episode_id=f"consistency_{i}")
        results.append((cleaned_text, metrics))
    
    # Check that all results are identical
    first_result = results[0][0]
    for i, (result, _) in enumerate(results[1:], 1):
        assert result == first_result, f"Inconsistent result at iteration {i}"
    
    print(f"✓ All 5 iterations produced identical results")
    
    # Check that metrics are reasonable (processing time may vary slightly)
    times = [m[1]["pipeline"]["total_time_ms"] for m in results]
    avg_time = sum(times) / len(times)
    print(f"  Average processing time: {avg_time:.2f}ms")
    print(f"  Time range: {min(times):.2f}-{max(times):.2f}ms")


if __name__ == "__main__":
    try:
        run_benchmark()
        test_consistency()
        print("\n🎉 All benchmarks completed successfully!")
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        raise