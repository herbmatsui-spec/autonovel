import os
import re

TARGET_MODULES = [
    "agents",
    "backend",
    "core",
    "models",
    "services",
    "shared"
]

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Skipping {filepath}: {e}")
        return

    original = content
    for mod in TARGET_MODULES:
        # from {mod}.xxx -> from src.{mod}.xxx
        pattern_from = rf'^(\s*)from\s+{mod}(\.|\s+import)'
        content = re.sub(pattern_from, rf'\1from src.{mod}\2', content, flags=re.MULTILINE)

        # import {mod}.xxx -> import src.{mod}.xxx
        # ただし、単純な 'import mod' は除外する（ディレクトリ名と衝突するため）
        pattern_import = rf'^(\s*)import\s+{mod}\.'
        content = re.sub(pattern_import, rf'\1import src.{mod}.', content, flags=re.MULTILINE)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed imports in: {filepath}")

def main():
    root = os.path.abspath('src')
    for dirpath, dirnames, filenames in os.walk(root):
        for file in filenames:
            if file.endswith('.py'):
                fix_file(os.path.join(dirpath, file))

if __name__ == '__main__':
    main()

