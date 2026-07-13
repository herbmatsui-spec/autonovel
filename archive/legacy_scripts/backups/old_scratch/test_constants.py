import sys
from pathlib import Path

root_dir = Path(r"i:\claude2")
sys.path.insert(0, str(root_dir))

try:
    from config import (
        AI_CONTAMINATION_WORDS,
        STRESS_CATHARSIS_THRESHOLD,
    )
    print("Successfully imported constants from config")
    print(f"AI_CONTAMINATION_WORDS: {AI_CONTAMINATION_WORDS[:2]}...")
    print(f"STRESS_CATHARSIS_THRESHOLD: {STRESS_CATHARSIS_THRESHOLD}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

