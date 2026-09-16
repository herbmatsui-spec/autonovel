#!/usr/bin/env python3
"""
Benchmark script to measure correlation between token budget and retention rates.
Outputs a table showing token budget, reduction ratio, character retention, and foreshadowing retention.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.compression import FourLayerCompressor, ProtectedContext

def run_benchmark():
    """Run benchmark varying token budgets and measuring retention rates."""
    compressor = FourLayerCompressor()
    
    # Test text with known characters and foreshadowing
    text = """
    勇者アレンは聖剣バルムンクを構えた。背後には魔法使いエレナが控えている。
    古の予言『月が紅く染まる時』の謎が迫る。王国の宰相は暗黙のうちに反逆を企てていた。
    アレンとエレナは王都を脱出し、森の奥深くで隠れ家を見つけた。
    二人はそこで古い魔導書を見つけ、『月が紅く染まる時』の真の意味を解き明かそうとした。
    """
    
    protected = ProtectedContext(
        active_characters=["アレン", "エレナ", "宰相"],
        pending_foreshadowing_ids=["月が紅く染まる時", "古い魔導書"],
    )
    
    # Test various token budgets from 500 to 3000 in steps of 500
    token_budgets = list(range(500, 3500, 500))
    
    print("Token Budget | Reduction Ratio | Char Retention | Foreshadow Retention | Overall Consistency")
    print("-" * 80)
    
    for budget in token_budgets:
        try:
            result = compressor.compress(
                raw_text=text,
                protected_context=protected,
                max_tokens=budget,
                bypass_cache=True
            )
            
            if result.metrics:
                print(f"{budget:11} | {result.overall_reduction_ratio:15.3f} | {result.metrics.character_retention_score:14.3f} | {result.metrics.foreshadowing_retention_score:20.3f} | {result.metrics.overall_consistency_score:20.3f}")
            else:
                print(f"{budget:11} | {result.overall_reduction_ratio:15.3f} | {'N/A':14} | {'N/A':20} | {'N/A':20}")
        except Exception as e:
            print(f"{budget:11} | ERROR: {e}")
    
    print("\nBenchmark completed.")

if __name__ == "__main__":
    run_benchmark()