import json

for file_name in ["scratch\\line_94.json", "scratch\\line_136.json", "scratch\\line_396.json"]:
    try:
        with open(f"i:\\claude2\\{file_name}", "r", encoding="utf-8") as f:
            obj = json.load(f)

            # The content of the viewed file is usually in obj["content"] or obj["tool_calls"][0]["output"] or similar.
            # Let's check obj["content"]
            content = obj.get("content", "")
            if not content and "tool_calls" in obj:
                for tc in obj["tool_calls"]:
                    if "output" in tc:
                        content = tc["output"]
                        break

            if "def build_drafting_prompt" in content:
                print(f"Found def build_drafting_prompt in {file_name}!")
                # Let's extract lines of the content
                lines = content.splitlines()
                # Print 10 lines starting from where "def build_drafting_prompt" is found
                found = False
                for i, line in enumerate(lines):
                    if "def build_drafting_prompt" in line:
                        found = True
                        print("\n".join(lines[i:i+40]))
                        print("=" * 60)
                        break
    except Exception as e:
        print(f"Error reading {file_name}: {e}")

