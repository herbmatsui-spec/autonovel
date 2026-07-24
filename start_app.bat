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

start "AutoOpenBrowser" cmd /c "timeout /t 30 >nul & start http://localhost:5173"

docker compose up --build frontend-dev backend
pause