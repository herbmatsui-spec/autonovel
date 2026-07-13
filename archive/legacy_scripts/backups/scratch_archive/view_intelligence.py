with open("engine.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
    for idx in range(217, min(251, len(lines))):
        print(f"{idx}: {lines[idx-1].rstrip()}")

