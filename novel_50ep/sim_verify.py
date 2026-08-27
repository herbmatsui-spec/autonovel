
import sys
from pathlib import Path

# Add the project root to sys.path to allow imports from novel_50ep
sys.path.append('.')

from novel_50ep.generator import NovelGenerator, MockLLMGenerator
from novel_50ep.foreshadow_manager import ForeshadowManager
from novel_50ep.config import WORLD_FILE

def run_simulation():
    print("--- Starting Simulation for Episode 51 ---")
    
    # Initialize components
    # We use MockLLMGenerator to avoid API costs and for deterministic verification
    import yaml
    # Corrected: Using NovelGenerator as intended, and passing WORLD_FILE as the first arg
    # The generator internally handles MockLLMGenerator if llm_fn is None
    fm = ForeshadowManager(WORLD_FILE)
    gen = NovelGenerator(world_path=WORLD_FILE)
    # Override the internal generator to use MockLLM for the simulation
    gen.llm_fn = MockLLMGenerator(gen.world_data).generate
    
    # Target episode
    ep = 51
    
    # Generate episode
    # Note: generate_episode handles the 7-part flow and cliffhanger injection
    print(f"Generating episode {ep}...")
    result = gen.generate_episode(ep)
    
    if result:
        # 1. Part Targets (Approximate check via length of parts)
        print("\n[1] Checking Part Lengths:")
        # generate_episode returns (full_text, val_result, part_texts)
        full_text, val_result, part_texts = result
        for part_id, text in part_texts.items():
            print(f"Part {part_id}: {len(text)} chars")
            
        # 2. Verify Cliffhanger Injection for Ep 51
        print("\n[2] Checking Cliffhanger for Episode 51:")
        part7 = part_texts.get(7, "")
        # Expected cliff for ep 51: 【心理的断絶】信じていた言葉が、最悪の意味に変わった瞬間だった。
        if "信じていた言葉が、最悪の意味に変わった瞬間だった" in part7:
            print("✅ Success: Correct cliffhanger injected.")
        else:
            print("❌ Failure: Cliffhanger missing or incorrect.")
            print(f"Actual Part 7 content: {part7[-100:]}")
            
        # 3. Verify Arc Context (MockLLM uses world.yaml)
        print("\n[3] Checking Arc Context:")
        if "浸食と予兆" in full_text or "Rinの能力の真の目的" in full_text:
            print("✅ Success: Arc context found in text.")
        else:
            print("⚠️ Warning: Arc context not explicitly found in Mock text (MockLLM may be generic).")
            
    else:
        print("❌ Failure: Episode generation failed.")

if __name__ == "__main__":
    run_simulation()
