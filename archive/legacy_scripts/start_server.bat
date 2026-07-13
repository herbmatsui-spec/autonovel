@echo off
cd /d "%~dp0"
echo Starting FastAPI Backend...
echo ==================================================

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

cd backend
python -m uvicorn server:app --port 8000 --reload
pause
