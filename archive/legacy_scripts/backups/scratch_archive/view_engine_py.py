with open("engine.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "WritingAgent" in line or "content_processor" in line:
            print(f"Line {i}: {line.strip()}")

