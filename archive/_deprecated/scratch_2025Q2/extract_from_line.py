import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\96401c88-aaff-41af-9694-5d7e6bcb52bd\.system_generated\logs\transcript.jsonl"

for line_num in [94, 136, 396]:
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f, 1):
            if idx == line_num:
                try:
                    obj = json.loads(line)
                    # Let's inspect the keys and content
                    tool_calls = obj.get("tool_calls", [])
                    print(f"Line {line_num}: type={obj.get('type')}")
                    # In transcript.jsonl, the output of the tool call might be in a different field or under tool_calls/output
                    # Let's write the JSON to a file for investigation
                    with open(f"i:\\claude2\\scratch\\line_{line_num}.json", "w", encoding="utf-8") as out:
                        json.dump(obj, out, indent=2, ensure_ascii=False)
                    print(f"Saved line {line_num} to scratch\\line_{line_num}.json")
                except Exception as e:
                    print(f"Error for line {line_num}: {e}")

