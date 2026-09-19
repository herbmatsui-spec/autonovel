"""
Simple test of the Purple Prose Filter without loading the full src hierarchy.
"""

import sys
import os

# Add the specific path to our anti_ai module
current_dir = os.path.dirname(os.path.abspath(__file__))
anti_ai_path = os.path.join(current_dir, '..', 'src', 'services', 'anti_ai')
sys.path.insert(0, anti_ai_path)

# Also add the src directory for config imports
src_path = os.path.join(current_dir, '..', 'src')
sys.path.insert(0, src_path)

# Now import our modules directly
from purple_prose_filter import PurpleProseFilter
from density_scorer import DensityScorer
from syntax_refiner import SyntaxRefiner

def test_basic_functionality():
    """Test that our core components work."""
    print("Testing Purple Prose Filter...")
    
    # Test PurpleProseFilter
    filter_obj = PurpleProseFilter(max_aggressive_per_episode=2, max_metaphor_per_1k_chars=3)
    test_text = "彼は歯を食いしばり、まるで獣のように吠えた。"
    result = filter_obj.process(test_text)
    print(f"Input:  {test_text}")
    print(f"Output: {result}")
    print(f"Stats:  {filter_obj.get_stats()}")
    print()
    
    # Test DensityScorer
    scorer = DensityScorer()
    score = scorer.score_paragraph("彼は歯を食いしばり、まるで獣のように怒った。")
    print(f"Density Score:")
    print(f"  Aggressive: {score.aggressive_density:.2f}/1000")
    print(f"  Metaphor:   {score.metaphor_density:.2f}/1000")
    print(f"  Sensory:    {score.sensory_overload:.2f}")
    print(f"  Verb:       {score.verb_strength:.2f}")
    print()
    
    # Test SyntaxRefiner
    refiner = SyntaxRefiner()
    refined, agg_used, meta_used = refiner.refine_paragraph(
        "彼は歯を食いしばり、まるで獣のように吠えた。", 0, 0
    )
    print(f"Syntax Refinement:")
    print(f"  Input:  彼は歯を食いしばり、まるで獣のように吠えた。")
    print(f"  Output: {refined}")
    print(f"  Agg used: {agg_used}, Meta used: {meta_used}")
    print()

if __name__ == "__main__":
    test_basic_functionality()
    print("✓ All tests passed!")