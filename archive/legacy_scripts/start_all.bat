@echo off
cd /d "%~dp0"

echo ==================================================
echo Starting Hegemony Engine v3.0
echo ==================================================
echo.

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo [1/3] Starting FastAPI Backend...
start "FastAPI Backend" start_server.bat

echo [2/3] Starting Huey Worker...
start "Huey Worker" start_worker.bat

echo [3/3] Starting Streamlit UI...
start "Novel Engine UI" run_app.bat