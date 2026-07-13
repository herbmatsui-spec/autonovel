import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\c7365df4-738d-4991-a317-74d243bcbfce\.system_generated\logs\transcript.jsonl"

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            idx = data.get("step_index")
            if idx < 198 and "writing.py" in line:
                snippet = str(data.get("tool_calls"))[:200] if data.get("tool_calls") else str(data.get("content"))[:200]
                print(f"Step {idx}: {data.get('source')} | {data.get('type')} | Snippet: {snippet}")
        except Exception:
            pass

