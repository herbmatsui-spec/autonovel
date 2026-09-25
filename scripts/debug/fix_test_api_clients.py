"""Fix broken asyncio.run -> await replacements in test_api_clients.py."""

import ast

P = "tests/unit/llm_clients/test_api_clients.py"

with open(P, encoding="utf-8") as f:
    content = f.read()

import re

# Remove any standalone ')' line that immediately follows an 'await client.' line
# (leftovers from the asyncio.run(...) -> await rewrite).
lines = content.splitlines()
cleaned = []
for i, line in enumerate(lines):
    if line.strip() == ")" and cleaned and cleaned[-1].strip().startswith("await client."):
        continue
    cleaned.append(line)
content = "\n".join(cleaned) + "\n"

with open(P, "w", encoding="utf-8") as f:
    f.write(content)

try:
    ast.parse(content)
    print("SYNTAX OK")
except SyntaxError as e:
    print("SYNTAX ERROR:", e.lineno, e.msg)
    for i, line in enumerate(content.splitlines(), 1):
        if abs(i - (e.lineno or 0)) <= 3:
            print(i, line)
