@echo off
cd /d "%~dp0"
echo Starting FastAPI Backend...
echo ==================================================

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python -m uvicorn src.backend.server:app --port 8001 --reload
pause
