import subprocess

try:
    content = subprocess.check_output(["git", "show", "HEAD:engine_agents.py"]).decode("utf-8")
    with open("scratch/engine_agents_utf8.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully wrote engine_agents_utf8.py")
except Exception as e:
    print("Error:", e)

