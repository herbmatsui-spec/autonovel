@echo off
setlocal enabledelayedexpansion
title Hegemony Novel Generator v3.0 (Starting)
cd /d "%~dp0"

echo ===================================================
echo  Hegemony Novel Generator v3.0
echo ===================================================

if not exist logs mkdir logs

echo [INFO] Killing old processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM streamlit.exe >nul 2>&1

set USE_VENV=1

:: Check if venv exists and is valid
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Python virtual environment not found. Creating...
    if exist .venv rmdir /s /q .venv >nul 2>&1
    
    where py >nul 2>&1
    if !errorlevel! equ 0 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    
    if not exist ".venv\Scripts\python.exe" (
        echo [WARNING] Failed to create venv. Using system Python.
        set USE_VENV=0
    ) else (
        echo [INFO] Virtual environment created.
    )
)

:: Attempt to activate venv only if it exists
if !USE_VENV! equ 1 (
    if exist ".venv\Scripts\activate.bat" (
        call .venv\Scripts\activate.bat
    ) else (
        echo [WARNING] activate.bat not found. Falling back to system Python.
        set USE_VENV=0
    )
)

:: Ensure pip dependencies are installed
if not exist "logs\.packages_installed" (
    echo [INFO] Installing dependencies check...
    python -m pip install -r requirements.txt
    if !errorlevel! equ 0 (
        echo installed > logs\.packages_installed
    ) else (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b
    )
)

echo [INFO] Checking database status...
python -m alembic upgrade head > logs\alembic.log 2>&1

set PYTHONPATH=%cd%

echo [INFO] Starting Backend API...
start /B "" cmd /c "python -m uvicorn src.backend.server:app --host 127.0.0.1 --port 8200 > logs\uvicorn.log 2>&1"

echo [INFO] Starting Task Worker (Huey)...
start /B "" cmd /c "python -m huey.bin.huey_consumer src.backend.tasks.huey > logs\huey.log 2>&1"

echo [INFO] Starting Streamlit UI...
start /B "" cmd /c "python -m streamlit run streamlit_app/app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true > logs\streamlit.log 2>&1"

echo [INFO] Waiting for API to be ready...
:WAIT_LOOP
python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8200/health', timeout=2).getcode() == 200 else 1)" >nul 2>&1
if errorlevel 1 (
    timeout /t 2 >nul
    goto WAIT_LOOP
)

echo [INFO] All services started. Opening browser...
timeout /t 2 >nul
start http://localhost:8501

title Hegemony Novel Generator v3.0 (Running)
echo.
echo ===================================================
echo  All systems started successfully!
echo  Opening browser now.
echo  (If not opening, please visit http://localhost:8501)
echo ===================================================
echo.
echo Logs are saved in logs\ directory.
echo To stop all processes, run this bat file again.
echo.

:IDLE
timeout /t 3600 >nul
goto IDLE