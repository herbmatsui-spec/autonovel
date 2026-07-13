import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\96401c88-aaff-41af-9694-5d7e6bcb52bd\.system_generated\logs\transcript.jsonl"

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_idx, line in enumerate(f, 1):
        if "def build_drafting_prompt" in line:
            try:
                obj = json.loads(line)
                step_idx = obj.get("step_index")
                if "tool_calls" in obj:
                    for tc_idx, tc in enumerate(obj["tool_calls"]):
                        args = tc.get("args", {})
                        for k, v in args.items():
                            if isinstance(v, str) and "def build_drafting_prompt" in v:
                                # We only want blocks that don't have backslashes/escaped characters (meaning it's not a python script searching for it)
                                if "log_path =" not in v and "def test_build_drafting_prompt" not in v:
                                    print(f"Line {line_idx} (step_idx={step_idx}): arg {k} (len {len(v)}) contains build_drafting_prompt!")
                                    out_name = f"i:\\claude2\\scratch\\arg_drafting_{step_idx}_{tc_idx}_{k}.py"
                                    with open(out_name, "w", encoding="utf-8") as out:
                                        out.write(v)
                                    print(f"    Saved to {out_name}")
            except Exception:
                pass

