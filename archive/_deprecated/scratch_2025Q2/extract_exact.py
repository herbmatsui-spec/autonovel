import json

log_path = r"C:\Users\keide\.gemini\antigravity-ide\brain\96401c88-aaff-41af-9694-5d7e6bcb52bd\.system_generated\logs\transcript.jsonl"
output_path = r"i:\claude2\scratch\extracted_methods.py"

extracted = []

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        if "def build_beat_mapping_prompt" in line or "def build_delta_polish_prompt" in line:
            try:
                obj = json.loads(line)
                content = obj.get("content", "")
                if not content and "tool_calls" in obj:
                    content = str(obj["tool_calls"])

                # Check for clean content containing actual python definition
                if "def build_beat_mapping_prompt" in content:
                    extracted.append(content)
            except Exception:
                pass

with open(output_path, "w", encoding="utf-8") as out:
    for item in extracted:
        out.write("# EXTRACTED BLOCK\n")
        out.write(item)
        out.write("\n\n" + "="*80 + "\n\n")

print("Saved to scratch/extracted_methods.py")

