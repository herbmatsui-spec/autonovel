fpath = r"i:\claude2\run_demo.bat"
code = """@echo off
cd /d "%~dp0"
echo ==================================================
echo 覇権小説エンジン - 動作確認用デモを起動します
echo ==================================================
echo.
python demo.py
echo.
pause
"""
with open(fpath, "w", encoding="cp932") as f:
    f.write(code)
print("run_demo.bat has been written successfully.")

