@echo off
cd /d "%~dp0"
echo Starting Huey Worker...
echo ==================================================

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python -m huey.bin.huey_consumer src.backend.tasks.huey
pause