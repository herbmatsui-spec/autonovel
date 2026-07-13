import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\96401c88-aaff-41af-9694-5d7e6bcb52bd\.system_generated\logs\transcript.jsonl"
output_path = r"i:\claude2\scratch\recovered_engine_prompts.py"

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for i, line in enumerate(f, 1):
        if i == 136:
            obj = json.loads(line)
            content = obj.get("content", "")
            # The content contains the view of the file.
            # Let's clean up line numbers or format if it's formatted as "1: line"
            lines = content.splitlines()
            cleaned_lines = []
            for l in lines:
                # Remove line number prefix "1: " or similar
                if ":" in l:
                    parts = l.split(":", 1)
                    if parts[0].strip().isdigit():
                        cleaned_lines.append(parts[1])
                        continue
                cleaned_lines.append(l)

            with open(output_path, "w", encoding="utf-8") as out:
                out.write("\n".join(cleaned_lines))
            print("Successfully recovered line 136 content to scratch/recovered_engine_prompts.py")
            break

