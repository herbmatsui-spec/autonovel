import os
import re


def fix_test_imports(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Skipping {filepath}: {e}")
        return

    original = content
    # インポートパスの修正
    # from core. -> from src.core.
    content = re.sub(r'from\s+core\.', r'from src.core.', content)
    content = re.sub(r'import\s+core\.', r'import src.core.', content)
    # from models. -> from src.models.
    content = re.sub(r'from\s+models\.', r'from src.models.', content)
    content = re.sub(r'import\s+models\.', r'import src.models.', content)
    # from agents. -> from src.agents.
    content = re.sub(r'from\s+agents\.', r'from src.agents.', content)
    # from backend. -> from src.backend.
    content = re.sub(r'from\s+backend\.', r'from src.backend.', content)
    # from services. -> from src.services.
    content = re.sub(r'from\s+services\.', r'from src.services.', content)
    # from shared. -> from src.shared.
    content = re.sub(r'from\s+shared\.', r'from src.shared.', content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed imports in: {filepath}")

def main():
    root = os.path.abspath('tests')
    for dirpath, dirnames, filenames in os.walk(root):
        for file in filenames:
            if file.endswith('.py'):
                fix_test_imports(os.path.join(dirpath, file))

if __name__ == '__main__':
    main()

