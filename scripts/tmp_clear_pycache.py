import shutil
import os

removed = 0
for root, dirs, files in os.walk("tests"):
    for d in list(dirs):
        if d == "__pycache__":
            path = os.path.join(root, d)
            shutil.rmtree(path, ignore_errors=True)
            removed += 1
print(f"removed {removed} __pycache__ dirs")
