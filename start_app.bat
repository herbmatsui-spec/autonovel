@echo off
cd /d "%~dp0"
cls
echo =========================================
echo  Autonovel App Launcher (Docker Compose)
echo =========================================
echo  React UI: http://localhost:5173
echo  Backend : http://localhost:8200
echo =========================================
echo.
echo Launching browser in 30 seconds...
echo.

docker compose down --remove-orphans >nul 2>&1

echo Building backend...
docker compose build backend
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Backend build failed.
    pause
    exit /b %ERRORLEVEL%
)


echo.
echo Building frontend...
docker compose build frontend-dev
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Frontend build failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Starting all services...
docker compose up -d redis backend worker frontend-dev

start "AutoOpenBrowser" cmd /c "timeout /t 10 >nul & start http://localhost:5173"

echo.
echo =========================================
echo  Application started!
echo =========================================
pause