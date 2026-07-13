import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\96401c88-aaff-41af-9694-5d7e6bcb52bd\.system_generated\logs\transcript.jsonl"
output_path = r"i:\claude2\scratch\found_drafting_prompt.py"

max_len = 0
best_block = ""

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for idx, line in enumerate(f, 1):
        if "def build_drafting_prompt" in line:
            # Let's extract any string values from the JSON line
            # Using regex to find all double-quoted strings or just loading JSON
            try:
                obj = json.loads(line)

                # Recursive search for strings containing "def build_drafting_prompt"
                def search_dict_or_list(data):
                    global max_len, best_block
                    if isinstance(data, str):
                        if "def build_drafting_prompt" in data and len(data) > max_len:
                            # Avoid truncated notices
                            if "truncated" not in data or len(data) > 2000:
                                max_len = len(data)
                                best_block = data
                                print(f"Found block in line {idx} of length {len(data)}")
                    elif isinstance(data, dict):
                        for v in data.values():
                            search_dict_or_list(v)
                    elif isinstance(data, list):
                        for item in data:
                            search_dict_or_list(item)

                search_dict_or_list(obj)
            except Exception:
                pass

if best_block:
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(best_block)
    print(f"Successfully wrote best block (len={max_len}) to {output_path}")
else:
    print("No block found.")

