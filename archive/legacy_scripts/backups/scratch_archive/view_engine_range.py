with open("engine.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
    for i in range(1, min(41, len(lines))):
        print(f"{i}: {lines[i-1].rstrip()}")

