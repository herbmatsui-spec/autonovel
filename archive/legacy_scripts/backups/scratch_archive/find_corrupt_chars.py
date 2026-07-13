with open('agents/writing.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()
with open('scratch/corrupt_lines.txt', 'w', encoding='utf-8') as out:
    for idx, line in enumerate(lines):
        if '\ufffd' in line:
            safe_line = line.replace('\ufffd', '?')
            out.write(f"Line {idx+1}: {safe_line}\n")

