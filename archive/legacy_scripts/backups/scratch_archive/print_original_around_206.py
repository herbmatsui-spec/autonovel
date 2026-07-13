with open('scratch/writing_agent_original.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()
for i in range(195, 230):
    if i < len(lines):
        line = lines[i].replace('\u26a0', '[WARN]')
        safe_line = line.encode('ascii', 'backslashreplace').decode('ascii')
        print(f"Line {i+1}: {safe_line.strip()}")

