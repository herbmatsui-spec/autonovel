with open('agents/writing.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(200, 215):
    if i < len(lines):
        print(f"Line {i+1}: {repr(lines[i])}")

