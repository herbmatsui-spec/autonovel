
file_path = r"i:\claude2\start_app.bat"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    encoding_used = "utf-8"
except UnicodeDecodeError:
    with open(file_path, "r", encoding="cp932") as f:
        content = f.read()
    encoding_used = "cp932"

kill_logic = """
echo [INFO] 古いプロセスを終了しています...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1
"""

if kill_logic.strip() not in content:
    content = content.replace('set PYTHONPATH=%cd%', 'set PYTHONPATH=%cd%\n' + kill_logic)

with open(file_path, "w", encoding=encoding_used) as f:
    f.write(content)

print(f"Fixed start_app.bat using {encoding_used}")

