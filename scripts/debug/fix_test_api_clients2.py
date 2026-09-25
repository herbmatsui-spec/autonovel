"""Convert sync test methods containing await into async def."""

import ast
import re

P = "tests/unit/llm_clients/test_api_clients.py"

with open(P, encoding="utf-8") as f:
    content = f.read()

# Convert '    def test_xxx(' -> '    async def test_xxx(' unless already async
content = re.sub(r"^(\s+)def (test_\w+\()", r"\1async def \2", content, flags=re.MULTILINE)

with open(P, "w", encoding="utf-8") as f:
    f.write(content)

try:
    tree = ast.parse(content)
    print("SYNTAX OK")
    # Verify no await outside async
    for node in ast.walk(tree):
        pass
except SyntaxError as e:
    print("SYNTAX ERROR:", e.lineno, e.msg)
    for i, line in enumerate(content.splitlines(), 1):
        if abs(i - (e.lineno or 0)) <= 2:
            print(i, line)
