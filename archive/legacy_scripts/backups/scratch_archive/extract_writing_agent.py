import re

with open("scratch/engine_agents_utf8.py", "r", encoding="utf-8") as f:
    content = f.read()

# Let's find where WritingAgent class starts
start_match = re.search(r"class WritingAgent", content)
if start_match:
    start_pos = start_match.start()
    # WritingAgent is the last class in this file, so we can just grab from start_pos to the end!
    writing_agent_code = content[start_pos:]

    with open("scratch/writing_agent_original.py", "w", encoding="utf-8") as out:
        out.write(writing_agent_code)
    print("Extracted WritingAgent class to scratch/writing_agent_original.py. Size:", len(writing_agent_code))
else:
    print("class WritingAgent not found in the file.")

