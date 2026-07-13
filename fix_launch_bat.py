
file_path = r"i:\claude2\launch.bat"

with open(file_path, "r", encoding="shift_jis") as f:
    content = f.read()

# Fix 1: Check for python.exe instead of pip.exe for venv validation
content = content.replace('if not exist ".venv\\Scripts\\pip.exe"', 'if not exist ".venv\\Scripts\\python.exe"')

# Fix 2: Ensure packages are installed properly even if falling back to global
# Actually, if we fall back to global, we should probably still try to install.
# But more importantly, let's ensure pip install uses python -m pip.
# The script already has: python -m pip install -r requirements.txt
# Let's also kill old processes at the start so we don't have port conflicts.
kill_logic = """
echo [INFO] 古いプロセスを終了しています...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1
"""

if kill_logic.strip() not in content:
    content = content.replace('set USE_VENV=1', kill_logic + '\nset USE_VENV=1')

with open(file_path, "w", encoding="shift_jis") as f:
    f.write(content)

print("Fixed launch.bat")

