import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\96401c88-aaff-41af-9694-5d7e6bcb52bd\.system_generated\logs\transcript.jsonl"

found_blocks = []

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for idx, line in enumerate(f, 1):
        if "def build_drafting_prompt" in line:
            try:
                obj = json.loads(line)

                # Check tool calls
                tool_calls = obj.get("tool_calls", [])
                for tc in tool_calls:
                    args = tc.get("arguments", {})
                    for key in ["CodeContent", "ReplacementContent"]:
                        if key in args:
                            val = args[key]
                            if "def build_drafting_prompt" in val:
                                found_blocks.append((idx, key, len(val), val))

                # Check if it is a user input or response that has a code block
                content = obj.get("content", "")
                if "def build_drafting_prompt" in content and "def build_drafting_prompt" not in [x[3] for x in found_blocks]:
                    if "UnicodeEncodeError" not in content and "Match on line" not in content:
                        found_blocks.append((idx, "content", len(content), content))
            except Exception:
                pass

# Sort by length descending
found_blocks.sort(key=lambda x: x[2], reverse=True)

for i, (idx, source, size, val) in enumerate(found_blocks[:5]):
    print(f"Block {i}: Line {idx}, source {source}, size {size}")
    # Write to a file
    with open(f"i:\\claude2\\scratch\\drafting_candidate_{idx}_{source}.py", "w", encoding="utf-8") as out:
        out.write(val)

