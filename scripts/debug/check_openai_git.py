"""Compare generate_json signature in git HEAD vs working tree."""

import subprocess
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

head = subprocess.run(
    ["git", "show", "HEAD:src/core/llm_clients/openai.py"],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
).stdout.splitlines()

# print lines 28-50 of HEAD (generate_json signature)
for i, line in enumerate(head[27:50], 28):
    print(i, line)
