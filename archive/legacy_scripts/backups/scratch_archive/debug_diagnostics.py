import asyncio
import os
import sqlite3
import sys
from pathlib import Path

# Add workspace to path
workspace = Path(os.getcwd())
if str(workspace) not in sys.path:
    sys.path.insert(0, str(workspace))

def check_imports():
    print("--- 🔍 Checking Imports ---")
    modules = [
        "config", "database", "models", "engine", "agents.planning", "agents.writing",
        "kernels.conflict", "kernels.comfort", "kernels.connection", "kernels.enigma"
    ]
    for mod in modules:
        try:
            __import__(mod)
            print(f"✅ {mod}: OK")
        except Exception as e:
            print(f"❌ {mod}: FAILED ({e})")

def check_db_schema():
    print("\n--- 🗄️ Checking DB Schema ---")
    db_path = workspace / "kaku_hegemony_v2.db"
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    tables = ["books", "bible", "plot", "chapters", "branches", "characters"]
    for table in tables:
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cursor.fetchall()]
            if cols:
                print(f"✅ Table '{table}': OK (Columns: {len(cols)})")
                # Specific column checks
                if table == "plot":
                    for c in ["branch_id", "current_chain_phase", "state_integrity_score"]:
                        if c in cols:
                            print(f"   - Column '{c}': OK")
                        else:
                            print(f"   - ❌ Column '{c}': MISSING")
            else:
                print(f"❌ Table '{table}': EMPTY OR MISSING")
        except Exception as e:
            print(f"❌ Table '{table}': ERROR ({e})")
    conn.close()

async def check_engine_init():
    print("\n--- ⚙️ Checking Engine Initialization ---")
    try:
        from backend.engine import UltimateHegemonyEngine
        # Mock API Key
        engine = UltimateHegemonyEngine(api_key="mock_key")
        print("✅ Engine Instance: OK")

        # Check Agent methods
        if hasattr(engine.planner, "audit_bible_completeness"):
            print("✅ PlanningAgent.audit_bible_completeness: EXISTS")
        else:
            print("❌ PlanningAgent.audit_bible_completeness: MISSING")

        # Check Kernel resolution
        try:
            kernel = engine.narrative._get_kernel("追放ざまぁ")
            print(f"✅ Kernel Resolution (Conflict): OK ({type(kernel).__name__})")
        except Exception as e:
            print(f"❌ Kernel Resolution: FAILED ({e})")

    except Exception as e:
        print(f"❌ Engine Init: FAILED ({e})")

if __name__ == "__main__":
    check_imports()
    check_db_schema()
    asyncio.run(check_engine_init())

