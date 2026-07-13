with open('agents/writing.py', 'rb') as f:
    lines = f.readlines()
# Line 206 (0-indexed is 205)
line_bytes = lines[205]
print("Raw bytes of line 206:", line_bytes)
with open('scratch/line206_bytes.txt', 'wb') as out:
    out.write(line_bytes)

