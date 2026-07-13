import os

path = "scratch/engine_agents_utf8.py"
print("Exists:", os.path.exists(path))
if os.path.exists(path):
    print("Size:", os.path.getsize(path))
    with open(path, "r", encoding="utf-8") as f:
        print("First 10 lines:")
        for i in range(10):
            line = f.readline()
            if not line:
                break
            print(repr(line))

