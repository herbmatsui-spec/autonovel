import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.getcwd())

try:
    from config import PHYSIOLOGICAL_REPLACEMENTS, STORY_ARCHETYPES, STYLE_DEFINITIONS
    print("✅ Engine and Config imported successfully")
    print(f"STORY_ARCHETYPES count: {len(STORY_ARCHETYPES)}")
    print(f"STYLE_DEFINITIONS count: {len(STYLE_DEFINITIONS)}")
    print(f"PHYSIOLOGICAL_REPLACEMENTS count: {len(PHYSIOLOGICAL_REPLACEMENTS)}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()

