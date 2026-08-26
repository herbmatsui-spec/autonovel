import ast
import os
import sys
import importlib
import re
from pathlib import Path
from collections import defaultdict

def run_deep_inspection(root_dir):
    print("=== Deep Codebase Quality & Architecture Inspection ===")
    
    root_path = Path(root_dir)
    src_path = root_path / "src"
    
    # 1. Detect duplicate modules between root and src
    print("\n--- 1. Root vs src/ duplicates ---")
    root_dirs = ["services", "schemas", "database", "config", "prompts", "models"]
    for d in root_dirs:
        r_d = root_path / d
        s_d = src_path / d
        if r_d.exists() and s_d.exists():
            print(f"[DUPLICATION WARNING] Both '{d}/' and 'src/{d}/' exist in the project!")
            r_files = {p.relative_to(r_d): p for p in r_d.glob("**/*.py")}
            s_files = {p.relative_to(s_d): p for p in s_d.glob("**/*.py")}
            common = set(r_files.keys()) & set(s_files.keys())
            if common:
                print(f"   Common files ({len(common)}):")
                for cf in list(common)[:10]:
                    print(f"     - {d}/{cf} vs src/{d}/{cf}")

    # 2. Check all imports in Python files
    print("\n--- 2. Import Resolution & Obsolete References ---")
    import_errors = []
    deprecated_imports = []
    
    for py_file in root_path.glob("**/*.py"):
        if any(p in str(py_file) for p in [".git", ".venv", "venv", "__pycache__", "archive", "test_chroma_db", "chroma_db"]):
            continue
        rel = py_file.relative_to(root_path)
        try:
            with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read(), filename=str(rel))
        except Exception:
            continue
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("streamlit_app"):
                        deprecated_imports.append((str(rel), node.lineno, alias.name))
                    if alias.name.startswith("src.services.repo_") or alias.name.startswith("services.repo_"):
                        deprecated_imports.append((str(rel), node.lineno, f"Deleted repo mixin: {alias.name}"))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if node.module.startswith("streamlit_app"):
                        deprecated_imports.append((str(rel), node.lineno, node.module))
                    if "repo_" in node.module:
                        deprecated_imports.append((str(rel), node.lineno, f"Deleted repo mixin: {node.module}"))
                    if node.module == "llm_client" or node.module == "src.core.llm_client":
                        deprecated_imports.append((str(rel), node.lineno, f"Deleted llm_client: {node.module}"))

    if deprecated_imports:
        print(f"Found {len(deprecated_imports)} obsolete / broken import references:")
        for file, line, mod in deprecated_imports[:20]:
            print(f"  - {file}:{line} -> {mod}")
    else:
        print("No obsolete module references (streamlit_app, repo_*, llm_client) found.")

    # 3. Check Database & Transaction management
    print("\n--- 3. Database & Transaction Handling ---")
    db_issues = []
    for py_file in root_path.glob("src/**/*.py"):
        rel = py_file.relative_to(root_path)
        try:
            with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            continue
        
        # Check for uncommitted sessions or raw sql without params
        if "session.add(" in content and "session.commit(" not in content and "async with" not in content and "uow" not in content and "repository" not in str(py_file).lower():
            db_issues.append(f"{rel}: session.add() used without commit or uow context")
        
        # Raw sqlite connections
        if "sqlite3.connect" in content and "test" not in str(py_file):
            db_issues.append(f"{rel}: Direct sqlite3.connect used (bypassing DB layer/pool)")

    if db_issues:
        print(f"Found {len(db_issues)} potential DB issues:")
        for item in db_issues:
            print(f"  - {item}")
    else:
        print("No direct sqlite3.connect or obvious transaction leaks detected.")

    # 4. Check FastAPI routes security and auth
    print("\n--- 4. API Endpoints & Security Checks ---")
    api_routes = []
    unprotected_routes = []
    
    for py_file in root_path.glob("src/backend/routers/*.py"):
        rel = py_file.relative_to(root_path)
        try:
            with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(rel))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    dec_name = ""
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        dec_name = dec.func.attr
                        # router.get, router.post, etc.
                        if dec_name in ["get", "post", "put", "delete", "patch"]:
                            route_path = ""
                            if dec.args and isinstance(dec.args[0], ast.Constant):
                                route_path = dec.args[0].value
                            # Check if dependencies / security is present in decorator or func args
                            has_auth = "verify_api_key" in content or "Depends(" in ast.unparse(dec) or any("api_key" in arg.arg or "auth" in arg.arg or "user" in arg.arg for arg in node.args.args)
                            api_routes.append((str(rel), node.name, dec_name.upper(), route_path, has_auth))

    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    for r in api_routes:
        auth_status = "[AUTH]" if r[4] else "[NO-AUTH]"
        print(f"  [{r[2]}] {r[3]:<35} ({r[1]}) -> {auth_status} in {r[0]}")

    # 5. Check Concurrency & Thread safety
    print("\n--- 5. Concurrency / Global State Checks ---")
    global_mutable_vars = []
    for py_file in root_path.glob("src/**/*.py"):
        rel = py_file.relative_to(root_path)
        if "test" in str(rel):
            continue
        try:
            with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read(), filename=str(rel))
        except Exception:
            continue
            
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Detect global dict/list caches
                        if isinstance(node.value, (ast.Dict, ast.List, ast.Set)):
                            if not target.id.isupper(): # Not a constant
                                global_mutable_vars.append((str(rel), node.lineno, target.id, type(node.value).__name__))

    print(f"Found {len(global_mutable_vars)} module-level mutable variables (potential race condition in multi-worker/async):")
    for file, line, var, typ in global_mutable_vars[:15]:
        print(f"  - {file}:{line} -> {var} ({typ})")
    if len(global_mutable_vars) > 15:
        print(f"  ... and {len(global_mutable_vars) - 15} more")

if __name__ == "__main__":
    run_deep_inspection("e:/sda")
