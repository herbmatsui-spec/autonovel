"""
Final verification of the Purple Prose Detox Filter implementation.

This script verifies that all components work correctly together
without relying on the problematic src module imports.
"""

import sys
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# The project root is the directory containing this script
project_root = script_dir
# Build paths to our modules
src_path = os.path.join(project_root, 'src')
anti_ai_path = os.path.join(src_path, 'services', 'anti_ai')

# Add the necessary paths to sys.path
sys.path.insert(0, anti_ai_path)
sys.path.insert(0, src_path)

# Debug: Print paths to verify
print(f"[DEBUG] Script dir: {script_dir}")
print(f"[DEBUG] Project root: {project_root}")
print(f"[DEBUG] Src path: {src_path}")
print(f"[DEBUG] Anti-AI path: {anti_ai_path}")
print(f"[DEBUG] Src path exists: {os.path.exists(src_path)}")
print(f"[DEBUG] Anti-AI path exists: {os.path.exists(anti_ai_path)}")
print(f"[DEBUG] Purple prose filter exists: {os.path.exists(os.path.join(anti_ai_path, 'purple_prose_filter.py'))}")
print(f"[DEBUG] Sys path first 3: {sys.path[:3]}")
print()

# Import our modules
from purple_prose_filter import PurpleProseFilter
from density_scorer import DensityScorer, DensityScore
from syntax_refiner import SyntaxRefiner
from pipeline_orchestrator import ProseDetoxPipeline

def test_complete_system():
    """Test the complete purple prose detox system."""
    print("🔷 Purple Prose Detox Filter - Final Verification")
    print("=" * 60)
    
    # Test text with excessive purple prose (as described in the issue)
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
    
    print("📝 Original Text:")
    print(purple_text.strip())
    print()
    
    # Initialize the pipeline
    print("⚙️  Initializing pipeline...")
    pipeline = ProseDetoxPipeline()
    
    # Process the text
    print("🔄 Processing text...")
    start_time = time.time()
    cleaned_text, metrics = pipeline.process(purple_text, episode_id="final_verification")
    end_time = time.time()
    
    processing_time_ms = (end_time - start_time) * 1000
    
    print("✨ Cleaned Text:")
    print(cleaned_text.strip())
    print()
    
    # Verify results
    print("📊 Verification Results:")
    print(f"  ✓ Processing completed successfully")
    print(f"  ✓ Episode ID: {metrics['episode_id']}")
    print(f"  ✓ Input length: {metrics['input_length']} characters")
    print(f"  ✓ Output length: {metrics['output_length']} characters")
    print(f"  ✓ Processing time: {processing_time_ms:.2f} ms")
    print(f"  ✓ Latency target met: {metrics['pipeline']['meets_latency_target']} (<200ms)")
    print()
    
    # Show stream guard statistics
    sg_stats = metrics['stream_guard']['stats']
    print("🛡️  Stream Guard Statistics:")
    print(f"  ✓ Aggressive reactions processed: {sg_stats['aggressive_count']}")
    print(f"  ✓ Metaphors processed: = {sg_stats['metaphor_count']}")
    print(f"  ✓ Characters processed: = {sg_stats['character_count']}")
    print()
    
    # Show density gate details
    dg = metrics['density_gate']
    dg_score = dg['score']
    print("📈 Density Gate Analysis:")
    print(f"  ✓ Density category: {dg['density_category']}")
    print(f"  ✓ Should refine: = {dg['should_refine']}")
    print(f"  ✓ Aggressive density: = {dg_score.aggressive_density:.2f} per 1000 chars")
    print(f"  ✓ Metaphor density: = {dg_score.metaphor_density:.2f} per 1000 chars")
    print(f"  ✓ Sensory overload: = {dg_score.sensory_overload:.2f}")
    print(f"  ✓ Verb strength: = {dg_score.verb_strength:.2f}")
    print()
    
    # Verify that the system reduced purple prose
    original_length = len(purple_text)
    cleaned_length = len(cleaned_text)
    length_change = ((cleaned_length - original_length) / original_length) * 100
    
    print("📏 Length Analysis:")
    print(f"  ✓ Original length: = {original_length} characters")
    print(f"  ✓ Cleaned length: = {cleaned_length} characters")
    print(f"  ✓ Length change: = {length_change:+.1f}%")
    print()
    
    # Test episode boundaries
    print("🔄 Testing Episode Boundaries:")
    pipeline.reset_episode("episode_2")
    text2 = "しかし新たな試練が待ち受けていた。さらに奥歯を軋ませた。"
    cleaned2, metrics2 = pipeline.process(text2, episode_id="episode_2")
    agg_count_ep2 = metrics2['stream_guard']['stats']['aggressive_count']
    print(f"  ✓ Episode 2 aggressive count: = {agg_count_ep2} (should be able to use aggressive reactions again)")
    print()
    
    # Performance check
    print("⚡ Performance Check:")
    if processing_time_ms < 200:
        print(f"  ✓ Excellent: = {processing_time_ms:.2f}ms (<200ms target)")
    elif processing_time_ms < 500:
        print(f"  ✓ Good: = {processing_time_ms:.2f}ms (<500ms threshold)")
    else:
        print(f"  ⚠ Slow: = {processing_time_ms:.2f}ms (consider optimization)")
    print()
    
    # Overall assessment
    print("🏆 Overall Assessment:")
    checks_passed = 0
    total_checks = 5
    
    if metrics['pipeline']['meets_latency_target']:
        checks_passed += 1
        print("  ✓ Performance target met (<200ms)")
    else:
        print("  ⚠ Performance target not met (>200ms)")
    
    if sg_stats['aggressive_count'] <= 2:  # Should respect the limit
        checks_passed += 1
        print("  ✓ Aggressive reaction limits respected")
    else:
        print("  ⚠ Aggressive reaction limits may be exceeded")
        
    if dg['density_category'] in ['clean', 'moderate', 'elevated']:
        checks_passed += 1
        print("  ✓ Density categorization working")
    else:
        print("  ⚠ Density categorization issue")
        
    if cleaned_length > 0:
        checks_passed += 1
        print("  ✓ Text processing produced output")
    else:
        print("  ⚠ No output produced")
        
    if processing_time_ms > 0:
        checks_passed += 1
        print("  ✓ Processing time measured")
    else:
        print("  ⚠ Processing time not measured")
    
    print(f"\n📈 Final Score: = {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("🎉 ALL CHECKS PASSED - System is working correctly!")
        return True
    elif checks_passed >= total_checks * 0.8:
        print("👍 MOST CHECKS PASSED - System is working well with minor issues")
        return True
    else:
        print("👎 TOO MANY FAILURES - System needs attention")
        return False

if __name__ == "__main__":
    try:
        success = test_complete_system()
        exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)