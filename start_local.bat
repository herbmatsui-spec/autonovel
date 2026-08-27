@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ===================================================
echo  Autonovel (HaKen Novel) Local Launcher
echo ===================================================
echo.

set "PYTHONPATH=%cd%"

rem 1. Check Python
where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python was not found. Please install Python and add it to PATH.
        pause
        exit /b 1
    ) else (
        set PY_CMD=py
    )
) else (
    set PY_CMD=python
)

rem 2. Start Backend API
echo [1/4] Starting Backend API Server (Port: 8200)...
start "Autonovel - Backend API" cmd /k "set PYTHONPATH=%cd%&& %PY_CMD% -m uvicorn src.backend.server:app --host 127.0.0.1 --port 8200"

rem 3. Start Background Worker (Huey)
echo [2/4] Starting Background Worker (Huey)...
start "Autonovel - Worker (Huey)" cmd /k "set PYTHONPATH=%cd%&& %PY_CMD% -m huey.bin.huey_consumer src.backend.tasks.huey"

rem 4. Wait for API Server
echo [3/4] Waiting for Backend API to become ready...
set RETRIES=0
:WAIT_LOOP
%PY_CMD% -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8200/health').getcode() == 200 else 1)" >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    if !RETRIES! geq 20 (
        echo [WARNING] API server wait timed out. Continuing anyway...
        goto START_FRONTEND
    )
    ping -n 3 127.0.0.1 >nul
    goto WAIT_LOOP
)
echo Backend API server is ready at http://127.0.0.1:8200

:START_FRONTEND
echo.
echo [4/4] Starting Frontend Server (Port: 5173)...
cd /d "%~dp0frontend"

where bun >nul 2>&1
if errorlevel 1 (
    echo [INFO] bun not found. Using npm run dev...
    start "Autonovel - Frontend (React/Vite)" cmd /k "npm run dev"
) else (
    echo [INFO] bun detected. Using bun run dev...
    start "Autonovel - Frontend (React/Vite)" cmd /k "bun run dev"
)

cd /d "%~dp0"

echo.
echo ===================================================
echo  System started successfully!
echo   - Frontend UI : http://localhost:5173
echo   - Backend API  : http://localhost:8200
echo   - API Docs     : http://localhost:8200/docs
echo ===================================================
echo Opening browser...
ping -n 4 127.0.0.1 >nul
start http://localhost:5173

echo.
echo Please close each console window when you want to stop the servers.
pause
