import os
import sys
from pathlib import Path

root_dir = Path(r"i:\claude2")
sys.path.insert(0, str(root_dir))

print(f"PYTHONPATH: {sys.path[:3]}")
print(f"Current Dir: {os.getcwd()}")

try:
    print("Successfully imported config")
    print("Successfully imported config.narrative")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

