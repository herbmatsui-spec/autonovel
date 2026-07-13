import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\96401c88-aaff-41af-9694-5d7e6bcb52bd\.system_generated\logs\transcript.jsonl"

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_idx, line in enumerate(f, 1):
        try:
            obj = json.loads(line)
            step_idx = obj.get("step_index")
            tool_calls = obj.get("tool_calls", [])
            for tc_idx, tc in enumerate(tool_calls):
                args = tc.get("arguments", {})
                # Let's check all values in args for "engine_prompts.py" or check target path
                args_str = json.dumps(args, ensure_ascii=False)
                if "engine_prompts.py" in args_str:
                    print(f"Line {line_idx} (step_index={step_idx}) has tool call targeting engine_prompts.py: {tc.get('name')}")
                    # Let's extract any code contents or replacements
                    for key in ["CodeContent", "ReplacementContent"]:
                        if key in args:
                            val = args[key]
                            if "def build_drafting_prompt" in val:
                                print(f"  -> Found 'build_drafting_prompt' in {key} (length {len(val)})!")
                                out_name = f"i:\\claude2\\scratch\\extracted_step_{step_idx}_{tc_idx}.py"
                                with open(out_name, "w", encoding="utf-8") as out:
                                    out.write(val)
                                print(f"  -> Saved to {out_name}")
        except Exception:
            pass

