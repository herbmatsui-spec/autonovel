import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\96401c88-aaff-41af-9694-5d7e6bcb52bd\.system_generated\logs\transcript.jsonl"
output_path = r"i:\claude2\scratch\draft_polish_extracted.py"

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for i, line in enumerate(f, 1):
        if "def build_drafting_prompt" in line:
            try:
                obj = json.loads(line)
                # Let's inspect the step type
                # Look for tool calls or content
                content = ""
                if "tool_calls" in obj:
                    for tc in obj["tool_calls"]:
                        args = tc.get("arguments", {})
                        if args and "CodeContent" in args:
                            if "def build_drafting_prompt" in args["CodeContent"]:
                                content = args["CodeContent"]
                                break
                if not content:
                    content = obj.get("content", "")

                if "def build_drafting_prompt" in content:
                    # Let's write this to file
                    with open(output_path, "w", encoding="utf-8") as out:
                        out.write(content)
                    print(f"Found on line {i} and saved to {output_path}")
                    break
            except Exception:
                pass

