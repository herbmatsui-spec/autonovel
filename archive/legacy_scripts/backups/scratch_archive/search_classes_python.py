with open("scratch/engine_agents_utf8.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "AtmosphereGenerator" in line:
            print(f"Line {i}: {line}")

