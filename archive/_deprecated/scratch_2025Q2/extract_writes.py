import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\96401c88-aaff-41af-9694-5d7e6bcb52bd\.system_generated\logs\transcript.jsonl"
lines_to_check = [45, 105, 111, 166, 198, 212, 216, 266, 283, 325, 343, 391, 413, 419, 425]

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for idx, line in enumerate(f, 1):
        if idx in lines_to_check:
            try:
                obj = json.loads(line)
                tool_calls = obj.get("tool_calls", [])
                for tc_idx, tc in enumerate(tool_calls):
                    name = tc.get("name")
                    args = tc.get("arguments", {})
                    target_file = args.get("TargetFile", "")
                    print(f"Line {idx} Tool {name}: TargetFile={target_file}")

                    code = args.get("CodeContent", "") or args.get("ReplacementContent", "")
                    if "build_drafting_prompt" in code:
                        print(f"  -> Found 'build_drafting_prompt' in CodeContent (length {len(code)})!")
                        # Let's save it to a separate file so we can inspect it!
                        out_name = f"i:\\claude2\\scratch\\code_line_{idx}_{tc_idx}.py"
                        with open(out_name, "w", encoding="utf-8") as out:
                            out.write(code)
                        print(f"  Saved to {out_name}")
            except Exception as e:
                print(f"Error parsing line {idx}: {e}")

