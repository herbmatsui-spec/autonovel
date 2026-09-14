import os

# 全テキストを結合して参照検索に使う
all_text_parts = []
for root, dirs, files in os.walk("."):
    if ".git" in root or "node_modules" in root or "__pycache__" in root:
        continue
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(root, f)
            try:
                all_text_parts.append(open(p, encoding="utf-8", errors="ignore").read())
            except Exception:
                pass
all_text = "\n".join(all_text_parts)

targets = []
for root, dirs, files in os.walk("src"):
    for f in files:
        if f.endswith(".py"):
            p = os.path.join(root, f)
            mod = p[:-3].replace(os.sep, ".")
            name = f[:-3]
            parent_pkg = os.path.dirname(p).replace(os.sep, ".")
            referenced = (
                (f"from {mod} " in all_text)
                or (f"from {mod}." in all_text)
                or (f"from {mod} import" in all_text)
                or (f"import {mod}" in all_text)
                or (f"from {parent_pkg} import" in all_text and name in all_text)
            )
            if not referenced:
                targets.append(p)

targets.sort()
out = "never_referenced_modules.txt"
with open(out, "w", encoding="utf-8") as fh:
    fh.write("\n".join(targets))
print("never-referenced modules:", len(targets))
for t in targets[:150]:
    print(t)
