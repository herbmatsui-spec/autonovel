"""古い計画書を docs/archive/ に退避するスクリプト。"""
import os
import shutil
from pathlib import Path

ARCHIVE_DIR = Path("docs/archive/plans_v4")
PLANS_DIR = Path("plans")

# 退避対象とする古い計画書接頭辞やファイル名
STALE_PATTERNS = [
    "PLAN_",
    "plan1",
    "p0_implementation",
    "marketing_and_graphrag",
    "frontend_testing",
    "frontend_e2e",
    "implementation_plan_72steps",
]

def archive_plans():
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    if not PLANS_DIR.exists():
        print("plans directory does not exist.")
        return

    archived_count = 0
    for file in PLANS_DIR.glob("*.md"):
        # PROPOSAL_01〜09 および README.md は保護して残す
        if file.name.startswith("PROPOSAL_") or file.name in ("README.md", "P1_COVERAGE_DATABASE_12STEPS.md", "P4_COVERAGE_WORKFLOWS_12STEPS.md", "P5_COVERAGE_EASYMODE_12STEPS.md"):
            continue

        for pat in STALE_PATTERNS:
            if pat in file.name:
                dst = ARCHIVE_DIR / file.name
                shutil.move(str(file), str(dst))
                print(f"Archived: {file.name} -> {dst}")
                archived_count += 1
                break

    print(f"Total archived files: {archived_count}")

if __name__ == "__main__":
    archive_plans()