import ast
import sys
from pathlib import Path

root = Path(r"i:\claude2")
sys.path.insert(0, str(root))

def check_call():
    file_path = root / "agents" / "writing.py"
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "get_optimal_context_split":
                print(f"Call found: {ast.dump(node)}")
                print(f"Number of args: {len(node.args)}")
                for i, arg in enumerate(node.args):
                    print(f"  Arg {i}: {ast.dump(arg)}")

if __name__ == "__main__":
    check_call()

