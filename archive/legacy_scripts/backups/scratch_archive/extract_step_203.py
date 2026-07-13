import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\c7365df4-738d-4991-a317-74d243bcbfce\.system_generated\logs\transcript.jsonl"

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get("step_index") == 203:
                # Print the content/output of the view_file step
                content = data.get("content")
                if content:
                    print("Found step 203 content! Length:", len(content))
                    # Write it to a backup file
                    with open("scratch/writing_recovered.py", "w", encoding="utf-8") as out:
                        out.write(content)
                    print("Recovered to scratch/writing_recovered.py")
                else:
                    print("Step 203 has no content field. Keys:", data.keys())
        except Exception as e:
            print("Error:", e)

