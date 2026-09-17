"""不要な一時ファイルやキャッシュをクリーンアップするスクリプト。"""
import shutil
from pathlib import Path

def cleanup():
    # pycache のクリーンアップ
    pycache_dirs = list(Path(".").rglob("__pycache__"))
    for p in pycache_dirs:
        if ".git" not in str(p) and "node_modules" not in str(p):
            shutil.rmtree(p, ignore_errors=True)
    print(f"Cleaned {len(pycache_dirs)} __pycache__ directories.")

    # pytest_cache のクリーンアップ
    if Path(".pytest_cache").exists():
        shutil.rmtree(".pytest_cache", ignore_errors=True)
        print("Cleaned .pytest_cache")

if __name__ == "__main__":
    cleanup()