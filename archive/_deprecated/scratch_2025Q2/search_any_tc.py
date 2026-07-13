import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\96401c88-aaff-41af-9694-5d7e6bcb52bd\.system_generated\logs\transcript.jsonl"

found = []

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_idx, line in enumerate(f, 1):
        if "build_drafting_prompt" in line:
            try:
                obj = json.loads(line)
                step_idx = obj.get("step_index")
                if "tool_calls" in obj:
                    for tc_idx, tc in enumerate(obj["tool_calls"]):
                        args = tc.get("args", {})
                        for k, v in args.items():
                            if isinstance(v, str) and "build_drafting_prompt" in v:
                                # Let's ignore search queries or python scripts we wrote ourselves
                                if "log_path =" not in v and "def test_build_drafting_prompt" not in v and "import json" not in v:
                                    found.append((step_idx, tc.get("name"), k, len(v), v))
            except Exception:
                pass

# Sort by length descending
found.sort(key=lambda x: x[3], reverse=True)

for idx, (step_idx, name, key, length, val) in enumerate(found[:5]):
    print(f"Candidate {idx}: step_idx={step_idx}, tool={name}, key={key}, len={length}")
    out_path = f"i:\\claude2\\scratch\\tc_drafting_candidate_{step_idx}_{name}_{key}.py"
    with open(out_path, "w", encoding="utf-8") as out:
        out.write(val)
    print(f"  Saved to {out_path}")

