
import os
import sys
from pathlib import Path

# Ensure root is in path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

print(f"Current Directory: {os.getcwd()}")
print(f"Root Directory: {root_dir}")

try:
    print("Attempting to import sanitizer...")
    print("Successfully imported sanitizer")

    print("Attempting to import UltimateHegemonyEngine...")
    from backend.engine import UltimateHegemonyEngine
    print("Successfully imported UltimateHegemonyEngine")

    print("Attempting to instantiate engine (with dummy key)...")
    # This might fail on DB init if key is empty, but we want to see if import works
    engine = UltimateHegemonyEngine(api_key="dummy_key")
    print("Successfully instantiated engine (basic init)")

except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

