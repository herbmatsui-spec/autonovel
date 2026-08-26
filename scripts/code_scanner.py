import ast
import os
import sys
import glob
import re
from pathlib import Path
from collections import defaultdict

def scan_python_codebase(root_dir):
    print("=== Scanning Python Codebase ===")
    issues = defaultdict(list)
    file_count = 0
    line_count = 0

    py_files = []
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        if any(p in root for p in [".git", ".venv", "venv", "__pycache__", "archive"]):
            continue
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))

    print(f"Found {len(py_files)} Python files to analyze.")

    for filepath in py_files:
        rel_path = os.path.relpath(filepath, root_dir)
        file_count += 1
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()
                line_count += len(lines)
        except UnicodeDecodeError:
            try:
                with open(filepath, "r", encoding="cp932") as f:
                    content = f.read()
                    lines = content.splitlines()
                    line_count += len(lines)
            except Exception as e:
                issues["Encoding Error"].append(f"{rel_path}: {e}")
                continue

        # 1. Syntax / AST check
        try:
            tree = ast.parse(content, filename=rel_path)
        except SyntaxError as e:
            issues["Syntax Error"].append(f"{rel_path}:{e.lineno} - {e.msg}")
            continue

        # 2. AST-based analysis
        for node in ast.walk(tree):
            # Broad exception check
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues["Bare Except"].append(f"{rel_path}:{node.lineno} - bare except clause")
                elif isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"):
                    # Check if body is just pass
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        issues["Silent Exception Suppression (except Exception: pass)"].append(f"{rel_path}:{node.lineno}")

            # Hardcoded secrets/passwords/API keys pattern
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name_lower = target.id.lower()
                        if any(k in name_lower for k in ["api_key", "secret_key", "password", "token"]) and not name_lower.startswith("test_"):
                            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                val = node.value.value
                                if val and len(val) > 8 and not any(dummy in val.lower() for dummy in ["dummy", "test", "mock", "env", "your-", "xxx", "placeholder", "default", "none"]):
                                    issues["Potential Hardcoded Secret"].append(f"{rel_path}:{node.lineno} - Variable {target.id} might contain a real secret")

            # SQL Injection risks
            if isinstance(node, ast.Call):
                # execute(f"...") or execute("..." % ...) or execute("...".format(...))
                func_name = ""
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id
                if func_name in ("execute", "executemany", "raw_sql"):
                    if node.args:
                        arg0 = node.args[0]
                        if isinstance(arg0, ast.JoinedStr): # f-string
                            issues["SQL Injection Risk (f-string in execute)"].append(f"{rel_path}:{node.lineno}")
                        elif isinstance(arg0, ast.BinOp) and isinstance(arg0.op, ast.Mod): # % format
                            issues["SQL Injection Risk (% formatting in execute)"].append(f"{rel_path}:{node.lineno}")

            # Dangerous functions
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                if func_name in ("eval", "exec"):
                    issues["Dangerous Function (eval/exec)"].append(f"{rel_path}:{node.lineno} - {func_name}() used")

            # Async issues (e.g. time.sleep inside async def)
            if isinstance(node, ast.AsyncFunctionDef):
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Call):
                        if isinstance(inner.func, ast.Attribute):
                            if isinstance(inner.func.value, ast.Name) and inner.func.value.id == "time" and inner.func.attr == "sleep":
                                issues["Blocking Call in Async Function (time.sleep)"].append(f"{rel_path}:{inner.lineno}")

        # 3. Regex / String checks
        for i, line in enumerate(lines, start=1):
            if "TODO" in line or "FIXME" in line or "XXX" in line:
                # Capture TODO lines
                clean_line = line.strip()
                if len(clean_line) < 120:
                    issues["TODO/FIXME Comments"].append(f"{rel_path}:{i} - {clean_line}")

    print(f"\nTotal Python files analyzed: {file_count}, Total lines: {line_count}")
    print("=" * 60)
    for category, items in issues.items():
        print(f"\n### {category} (Count: {len(items)})")
        for item in items[:15]: # Show top 15
            print(f"  - {item}")
        if len(items) > 15:
            print(f"  ... and {len(items) - 15} more")

if __name__ == "__main__":
    scan_python_codebase("e:/sda")
