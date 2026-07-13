
path = r"i:\claude2\frontend\src\App.tsx"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if "getTaskStatus" in line or "setInterval" in line or "poll" in line or "status" in line.lower():
        if "getTaskStatus" in line or "setInterval" in line or "clearInterval" in line or "startTaskPolling" in line or "task_status" in line:
            print(f"Line {i}: {line.strip()}")

