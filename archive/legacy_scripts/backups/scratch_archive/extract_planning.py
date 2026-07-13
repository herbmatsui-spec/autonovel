import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\55a6953c-cce2-431d-a7ed-deab7c633e27\.system_generated\logs\transcript.jsonl"

with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get("step_index") == 9:
                content = data.get("content", "")
                if content:
                    print("Found step 9 content length:", len(content))
                    # Save to scratch/planning_recovered.py
                    with open("scratch/planning_recovered.py", "w", encoding="utf-8") as out:
                        out.write(content)
                    print("Extracted to scratch/planning_recovered.py successfully!")
        except Exception as e:
            print("Error parsing line:", e)

