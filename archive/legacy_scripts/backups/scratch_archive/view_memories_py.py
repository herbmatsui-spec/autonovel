import os

keyword = ".memory"
for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if keyword in content:
                        for line in content.split("\n"):
                            if "memory" in line and ("save" in line or "create" in line or "add" in line or "update" in line):
                                print(f"{path}: {line.strip()}")
            except Exception:
                pass

