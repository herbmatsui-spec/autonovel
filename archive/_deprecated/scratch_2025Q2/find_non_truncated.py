import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\96401c88-aaff-41af-9694-5d7e6bcb52bd\.system_generated\logs\transcript.jsonl"

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for i, line in enumerate(f, 1):
        if "build_beat_mapping_prompt" in line:
            obj = json.loads(line)
            tool_calls = obj.get("tool_calls", [])
            for tc in tool_calls:
                args = tc.get("arguments", {}) if isinstance(tc, dict) else {}
                content = args.get("CodeContent", "") if isinstance(args, dict) else ""
                if "build_beat_mapping_prompt" in content:
                    print(f"Found non-truncated in line {i} tool_call CodeContent:")
                    print(content)
                    print("=" * 80)

            # Check step content
            content = obj.get("content", "")
            if "build_beat_mapping_prompt" in content and "truncated" not in content:
                print(f"Found non-truncated in line {i} step content:")
                print(content)
                print("=" * 80)

