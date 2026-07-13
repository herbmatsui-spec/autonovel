with open("agents/writing.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
    for idx in range(480, 486):
        print(f"{idx}: {lines[idx-1].rstrip()}")

