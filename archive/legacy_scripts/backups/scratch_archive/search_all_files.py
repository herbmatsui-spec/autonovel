import os
import zipfile

keyword = "class WritingAgent"
for root, dirs, files in os.walk("."):
    for file in files:
        path = os.path.join(root, file)
        if "node_modules" in path or ".git" in path or "kaku_hegemony" in path:
            continue
        try:
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path, 'r') as z:
                    for name in z.namelist():
                        try:
                            with z.open(name) as f:
                                content = f.read().decode('utf-8', errors='ignore')
                                if keyword in content:
                                    print(f"Found in zip: {path} -> {name} (size: {len(content)})")
                        except Exception:
                            pass
            else:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if keyword in content:
                        print(f"Found in file: {path} (size: {len(content)})")
        except Exception:
            pass

