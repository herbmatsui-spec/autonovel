
path = r'i:\claude2\sanitizer.py'
with open(path, 'rb') as f:
    lines = f.readlines()

# Line 409 is index 408 (0-indexed)
# Wait, view_file says 409 is MEMORY_KEYWORDS list
target_lines = lines[407:415]
for i, line in enumerate(target_lines):
    print(f"Line {408+i}: {line}")
    print(f"Hex: {line.hex()}")

