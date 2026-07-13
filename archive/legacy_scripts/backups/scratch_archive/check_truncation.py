import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\c7365df4-738d-4991-a317-74d243bcbfce\.system_generated\logs\transcript.jsonl"

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get("step_index") == 203:
                for k, v in data.items():
                    print(f"Key: {k}, Type: {type(v)}, Length: {len(str(v)) if hasattr(v, '__len__') or isinstance(v, str) else 'N/A'}")
                    if k == "content":
                        print("Content starts with:")
                        print(str(v)[:300])
                        print("Content ends with:")
                        print(str(v)[-300:])
        except Exception:
            pass

