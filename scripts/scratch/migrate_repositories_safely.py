import os
import shutil
from pathlib import Path

src_repo_dir = Path("src/backend/database/repositories")
dst_repo_dir = Path("src/infrastructure/repositories")

dst_repo_dir.mkdir(parents=True, exist_ok=True)

files = [f for f in src_repo_dir.glob("*.py") if f.name != "__pycache__"]

print(f"Found {len(files)} files in {src_repo_dir}")

for f in files:
    stem = f.stem
    dst_file = dst_repo_dir / f.name
    
    # 1. dst にコピー（存在しない場合、または既存の hook/foreshadowing 以外）
    if f.name != "__init__.py":
        # 実装ファイルを dst へコピー
        shutil.copy2(f, dst_file)
        print(f"Copied {f.name} -> {dst_file}")
        
        # 2. src 側に安全な透過エイリアスを作成
        alias_content = f'''"""下位互換性維持のためのエイリアス。実体は src.infrastructure.repositories.{stem} に移動しました。"""
from src.infrastructure.repositories.{stem} import *  # noqa: F401, F403
'''
        with open(f, "w", encoding="utf-8") as out:
            out.write(alias_content)
        print(f"Created alias at {f}")

# 3. dst_repo_dir/__init__.py の更新
# 元の src_repo_dir/__init__.py の内容をベースに作成
orig_init = src_repo_dir / "__init__.py"
if orig_init.exists():
    init_content = open(orig_init, encoding="utf-8").read()
    dst_init = dst_repo_dir / "__init__.py"
    with open(dst_init, "w", encoding="utf-8") as out:
        out.write(init_content)
    print(f"Updated {dst_init}")

    # src_repo_dir/__init__.py を下位互換エイリアスに更新
    src_init_alias = '''"""下位互換性維持のためのエイリアス。実体は src.infrastructure.repositories に移動しました。"""
from src.infrastructure.repositories import *  # noqa: F401, F403
from src.infrastructure.repositories import __all__ as _all_exports
__all__ = _all_exports
'''
    with open(orig_init, "w", encoding="utf-8") as out:
        out.write(src_init_alias)
    print(f"Updated alias for {orig_init}")

print("Repository migration and aliasing completed successfully.")
