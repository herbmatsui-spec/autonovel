import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\c7365df4-738d-4991-a317-74d243bcbfce\.system_generated\logs\transcript.jsonl"

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get("step_index") == 233:
                content = data.get("content")
                if content:
                    print("Found step 233 content!")
                    with open("scratch/writing_range_recovered.py", "w", encoding="utf-8") as out:
                        out.write(content)
                    print("Recovered to scratch/writing_range_recovered.py")
        except Exception as e:
            print("Error:", e)

