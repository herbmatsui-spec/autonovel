@echo off
cd /d "%~dp0"
if exist ".env" (
  for /f "usebackq tokens=1*" %%A in (".env") do set "%%A=%%B"
)
python -B main.py --gui
echo.
echo Processed.
pause