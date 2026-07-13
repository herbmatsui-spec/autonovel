import sys
from pathlib import Path

# Add root dir to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

print("Attempting to import ui_components...")
try:
    print("Successfully imported ui_components!")
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)

