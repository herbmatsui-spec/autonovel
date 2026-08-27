"""
scripts/verify_app_health.py - アプリケーション総合ヘルスチェック
"""

import sys
import os
import ast
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def test_codebase_integrity():
    print("=== 1. Checking Python Codebase Integrity ===")
    root = Path(".")
    py_files = list(root.glob("src/**/*.py")) + list(root.glob("config/**/*.py"))
    
    syntax_errors = []
    for p in py_files:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                ast.parse(f.read(), filename=str(p))
        except SyntaxError as e:
            syntax_errors.append((str(p), e.lineno, e.msg))
            
    if syntax_errors:
        print(f"❌ Syntax Errors found ({len(syntax_errors)}):")
        for f, l, m in syntax_errors:
            print(f"   {f}:{l} - {m}")
        return False
    else:
        print(f"✅ All {len(py_files)} Python source files parsed successfully (0 Syntax Errors)!")
        return True

def test_api_client_contract():
    print("\n=== 2. Checking Frontend API Client Contract ===")
    api_client_path = Path("frontend/src/lib/apiClient.ts")
    if not api_client_path.exists():
        print("❌ frontend/src/lib/apiClient.ts missing!")
        return False
        
    with open(api_client_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    required_tokens = ["X-API-Key", "API_BASE_URL", "request<T>", "ApiError"]
    missing = [t for t in required_tokens if t not in content]
    if missing:
        print(f"❌ Missing tokens in apiClient.ts: {missing}")
        return False
        
    print("✅ Frontend apiClient contract verified (X-API-Key, request, error handling present).")
    return True

def test_router_registrations():
    print("\n=== 3. Checking Router Registrations in server.py ===")
    server_path = Path("src/backend/server.py")
    with open(server_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    required_routers = [
        "src.backend.routers.health",
        "src.backend.routers.books",
        "src.backend.routers.plots",
        "src.backend.routers.episodes",
        "src.backend.routers.tasks",
        "src.backend.routers.patches",
        "src.backend.routers.issues",
        "src.backend.routers.marketing",
        "src.backend.routers.prompt_versions",
        "src.backend.routers.metrics",
        "src.backend.routers.misc",
        "src.backend.routers.novel",
        "src.backend.routers.commercial",
        "src.backend.routers.easy_mode",
        "src.backend.routers.illustrations",
        "src.backend.routers.events",
        "src.api.routes.ux_routes",
    ]

    
    for r in required_routers:
        if r not in content:
            print(f"❌ Router not registered: {r}")
            return False
            
    print(f"✅ All {len(required_routers)} routers registered in server.py.")
    return True

def main():
    print("🚀 Starting Autonovel Application Comprehensive Verification...\n")
    ok1 = test_codebase_integrity()
    ok2 = test_api_client_contract()
    ok3 = test_router_registrations()
    
    if ok1 and ok2 and ok3:
        print("\n🎉 ALL APPLICATION INTEGRITY CHECKS PASSED!")
        return 0
    else:
        print("\n❌ SOME CHECKS FAILED.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
