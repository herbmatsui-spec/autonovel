import sys
from pathlib import Path

root_dir = Path(r"i:\claude2")
sys.path.insert(0, str(root_dir))

try:
    import config.word_lists
    print("Successfully imported config.word_lists")
    print(f"File: {config.word_lists.__file__}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

