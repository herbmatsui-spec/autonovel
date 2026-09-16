import io
from collections import Counter

with io.open("fail_list.txt", encoding="utf-8", errors="replace") as f:
    lines = [l for l in f if l.strip()]

print("total failed:", len(lines))
files = Counter()
for line in lines:
    parts = line.split("::")
    if len(parts) >= 2:
        files[parts[0]] += 1

for f, c in sorted(files.items(), key=lambda x: -x[1])[:30]:
    print(c, f)
