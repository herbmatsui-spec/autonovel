import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\96401c88-aaff-41af-9694-5d7e6bcb52bd\.system_generated\logs\transcript.jsonl"

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for i, line in enumerate(f, 1):
        if "def build_beat_mapping_prompt" in line:
            # Let's parse this JSON line
            try:
                obj = json.loads(line)
                content = obj.get("content", "")
                if not content and "tool_calls" in obj:
                    content = str(obj["tool_calls"])

                # Check if it has the actual python definition
                if "def build_beat_mapping_prompt" in content:
                    print(f"Line {i} content contains method definition:")
                    # Find start of def build_beat_mapping_prompt
                    idx = content.find("def build_beat_mapping_prompt")
                    print(content[idx:idx+2500])
                    print("=" * 80)
            except Exception as e:
                print(f"Error parsing line {i}: {e}")

